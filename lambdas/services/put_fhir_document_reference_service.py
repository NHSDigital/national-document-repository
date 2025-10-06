import os
import binascii
import io
import base64

from utils.audit_logging_setup import LoggingService
from services.base.dynamo_service import DynamoDBService
from services.base.s3_service import S3Service
from models.fhir.R4.fhir_document_reference import (
    DocumentReference as FhirDocumentReference,
)
from models.document_reference import DocumentReference
from utils.common_query_filters import CurrentStatusFile
from services.document_service import DocumentService
from enums.snomed_codes import SnomedCode, SnomedCodes
from enums.lambda_error import LambdaError
from utils.lambda_exceptions import UpdateFhirDocumentReferenceException
from botocore.exceptions import ClientError
from enums.patient_ods_inactive_status import PatientOdsInactiveStatus
from models.fhir.R4.fhir_document_reference import SNOMED_URL, Attachment
from models.fhir.R4.fhir_document_reference import DocumentReferenceInfo
from models.pds_models import PatientDetails
from pydantic import ValidationError
from utils.exceptions import (
    InvalidNhsNumberException,
    InvalidResourceIdException,
    PatientNotFoundException,
    PdsErrorException,
)
from utils.ods_utils import PCSE_ODS_CODE
from utils.utilities import create_reference_id, get_pds_service, validate_nhs_number

#Questions for Danielle
#Does the NHS Number check need to be in scope for this base service?
#   the two apis handle checking that differently

#How do we handle swapping the current document version?
#   do we prevent access to it until it has been processed?
#   do we allow access to the previous version until the new one has been processed

logger = LoggingService(__name__)

class PutFhirDocumentReferenceService:
    def __init__(self):
        presigned_aws_role_arn = os.getenv("PRESIGNED_ASSUME_ROLE")
        self.s3_service = S3Service(custom_aws_role=presigned_aws_role_arn)
        self.dynamo_service = DynamoDBService()

        self.lg_dynamo_table = os.getenv("LLOYD_GEORGE_DYNAMODB_NAME")
        self.arf_dynamo_table = os.getenv("DOCUMENT_STORE_DYNAMODB_NAME")
        self.staging_bucket_name = os.getenv("STAGING_STORE_BUCKET_NAME")
        self.document_service = DocumentService()

    def process_fhir_document_reference(self, fhir_document: str) -> str:
        #get document reference from database
        #create new document reference entry in dynamodb set to preliminary
        #store document in bucket or return pre-signed url

        validated_fhir_doc = self._validate_update_document_reference_request(fhir_document)
        return self._update_document_references(validated_fhir_doc)

    def _update_document_references(self, validated_fhir_doc: FhirDocumentReference):
        try:
            # Extract NHS number from the FHIR document
            nhs_number = self._extract_nhs_number_from_fhir(validated_fhir_doc)
            patient_details = self._check_nhs_number_with_pds(nhs_number)

            # Extract document type
            doc_type = self._determine_document_type(validated_fhir_doc)

            # Determine which DynamoDB table to use based on the document type
            dynamo_table = self._get_dynamo_table_for_doc_type(doc_type)

            # Check if binary content is included
            binary_content = validated_fhir_doc.content[0].attachment.data

            current_doc = self._get_document_references(validated_fhir_doc.id, dynamo_table)

            new_doc_version = int(current_doc.version) + 1

            # Create a document reference model
            document_reference = self._create_document_reference(
                nhs_number,
                doc_type,
                validated_fhir_doc,
                patient_details.general_practice_ods,
                str(new_doc_version)
            )

            presigned_url = None
            # Handle binary content if present, otherwise create a pre-signed URL
            if binary_content:
                self._store_binary_in_s3(document_reference, binary_content)
            else:
                # Create a pre-signed URL for uploading
                presigned_url = self._create_presigned_url(document_reference)

            # Save document reference to DynamoDB
            self._save_document_reference_to_dynamo(dynamo_table, document_reference)
            return self._create_fhir_response(document_reference, presigned_url)

        except (ValidationError, InvalidNhsNumberException) as e:
            logger.error(f"FHIR document validation error: {str(e)}")
            raise UpdateFhirDocumentReferenceException(400, LambdaError.CreateDocNoParse)
        except ClientError as e:
            logger.error(f"AWS client error: {str(e)}")
            raise UpdateFhirDocumentReferenceException(500, LambdaError.InternalServerError)

    def _validate_update_document_reference_request(self, updated_doc: str) -> FhirDocumentReference:
        #check document with passed ID exists
        #check it is the latest version (DocStatus = final)
        #check referenced NHS number matches NHS number on stored reference
        
        try:
            validated_fhir_doc = FhirDocumentReference.model_validate_json(updated_doc)
        except ValidationError as e:
            logger.error(f"FHIR document validation error: {str(e)}")
            raise UpdateFhirDocumentReferenceException(400, LambdaError.CreateDocNoParse)

        # Extract document type
        doc_type = self._determine_document_type(validated_fhir_doc)

        # Determine which DynamoDB table to use based on the document type
        dynamo_table = self._get_dynamo_table_for_doc_type(doc_type)

        current_doc = self._get_document_references(validated_fhir_doc.id, dynamo_table)

        if not current_doc:
            logger.error("No document found for the given document ID.")
            raise UpdateFhirDocumentReferenceException(
                404, LambdaError.DocumentReferenceNotFound
            )

        if not current_doc.doc_status == "final":
            logger.error("Document is not the latest version.") #would it be better to have the same error message as above?
            raise UpdateFhirDocumentReferenceException(
                404, LambdaError.DocumentReferenceForbidden
            )
        
        put_nhs_number = self._extract_nhs_number_from_fhir(validated_fhir_doc)

        if current_doc.nhs_number != put_nhs_number:
            logger.error("NHS numbers do not match.")
            raise UpdateFhirDocumentReferenceException(
                400, LambdaError
            )
        
        return validated_fhir_doc

    def _extract_nhs_number_from_fhir(self, fhir_doc: FhirDocumentReference) -> str:
        """Extract NHS number from FHIR document"""
        # Extract NHS number from subject.identifier where the system identifier is NHS number
        if (
            fhir_doc.subject
            and fhir_doc.subject.identifier
            and fhir_doc.subject.identifier.system
            == "https://fhir.nhs.uk/Id/nhs-number"
        ):
            return fhir_doc.subject.identifier.value

        raise UpdateFhirDocumentReferenceException(400, LambdaError.UpdateDocNoParse)
    
    def _get_document_references(self, document_id: str, table) -> DocumentReference:
        documents = self.document_service.fetch_documents_from_table(
            table=table,
            search_condition=document_id,
            search_key="ID",
            query_filter=CurrentStatusFile,
        )
        if len(documents) > 0:
            logger.info("Document found for given id")
            return documents[0]
        else:
            raise UpdateFhirDocumentReferenceException(
                404, LambdaError.DocumentReferenceNotFound
            )

    def _extract_nhs_number_from_fhir(self, fhir_doc: FhirDocumentReference) -> str:
        """Extract NHS number from FHIR document"""
        # Extract NHS number from subject.identifier where the system identifier is NHS number
        if (
            fhir_doc.subject
            and fhir_doc.subject.identifier
            and fhir_doc.subject.identifier.system
            == "https://fhir.nhs.uk/Id/nhs-number"
        ):
            return fhir_doc.subject.identifier.value

        raise UpdateFhirDocumentReferenceException(400, LambdaError.CreateDocNoParse)

    def _determine_document_type(self, fhir_doc: FhirDocumentReference) -> SnomedCode:
        """Determine the document type based on SNOMED code in the FHIR document"""
        if fhir_doc.type and fhir_doc.type.coding:
            for coding in fhir_doc.type.coding:
                if coding.system == SNOMED_URL:
                    if coding.code == SnomedCodes.LLOYD_GEORGE.value.code:
                        return SnomedCodes.LLOYD_GEORGE.value
                else:
                    logger.error(
                        f"SNOMED code {coding.code} - {coding.display} is not supported"
                    )
                    raise UpdateFhirDocumentReferenceException(
                        400, LambdaError.CreateDocInvalidType
                    )
        logger.error("SNOMED code not found in FHIR document")
        raise UpdateFhirDocumentReferenceException(400, LambdaError.CreateDocInvalidType)

    def _get_dynamo_table_for_doc_type(self, doc_type: SnomedCode) -> str:
        """Get the appropriate DynamoDB table name based on a document type"""
        if doc_type == SnomedCodes.LLOYD_GEORGE.value:
            return self.lg_dynamo_table
        else:
            return self.arf_dynamo_table

    def _create_document_reference(
        self,
        nhs_number: str,
        doc_type: SnomedCode,
        fhir_doc: FhirDocumentReference,
        current_gp_ods: str,
        version: str
    ) -> DocumentReference:
        """Create a document reference model"""
        document_id = create_reference_id()

        custodian = fhir_doc.custodian.identifier.value if fhir_doc.custodian else None
        if not custodian:
            custodian = (
                current_gp_ods
                if current_gp_ods not in PatientOdsInactiveStatus.list()
                else PCSE_ODS_CODE
            )
        document_reference = DocumentReference(
            id=document_id,
            nhs_number=nhs_number,
            current_gp_ods=current_gp_ods,
            custodian=custodian,
            s3_bucket_name=self.staging_bucket_name,
            author=fhir_doc.author[0].identifier.value,
            content_type=fhir_doc.content[0].attachment.contentType,
            file_name=fhir_doc.content[0].attachment.title,
            document_snomed_code_type=doc_type.code,
            doc_status="preliminary",
            status="current",
            sub_folder="user_upload",
            document_scan_creation=fhir_doc.content[0].attachment.creation,
            version=version,
        )

        return document_reference

    def _save_document_reference_to_dynamo(
        self, table_name: str, document_reference: DocumentReference
    ) -> None:
        """Save document reference to DynamoDB"""
        try:
            self.dynamo_service.create_item(
                table_name,
                document_reference.model_dump(exclude_none=True, by_alias=True),
            )
            logger.info(f"Successfully created document reference in {table_name}")
        except ClientError as e:
            logger.error(f"Failed to create document reference: {str(e)}")
            raise UpdateFhirDocumentReferenceException(
                500, LambdaError.CreateDocUploadInternalError
            )

    def _store_binary_in_s3(
        self, document_reference: DocumentReference, binary_content: bytes
    ) -> None:
        """Store binary content in S3"""
        try:
            binary_file = io.BytesIO(base64.b64decode(binary_content, validate=True))
            self.s3_service.upload_file_obj(
                file_obj=binary_file,
                s3_bucket_name=document_reference.s3_bucket_name,
                file_key=document_reference.s3_file_key,
            )
            logger.info(
                f"Successfully stored binary content in S3: {document_reference.s3_file_key}"
            )
        except (binascii.Error, ValueError) as e:
            logger.error(f"Failed to decode base64: {str(e)}")
            raise UpdateFhirDocumentReferenceException(500, LambdaError.CreateDocNoParse)
        except MemoryError as e:
            logger.error(f"File too large to process: {str(e)}")
            raise UpdateFhirDocumentReferenceException(500, LambdaError.CreateDocNoParse)
        except ClientError as e:
            logger.error(f"Failed to store binary in S3: {str(e)}")
            raise UpdateFhirDocumentReferenceException(500, LambdaError.CreateDocNoParse)
        except (OSError, IOError) as e:
            logger.error(f"I/O error when processing binary content: {str(e)}")
            raise UpdateFhirDocumentReferenceException(500, LambdaError.CreateDocNoParse)

    def _create_presigned_url(self, document_reference: DocumentReference) -> str:
        """Create a pre-signed URL for uploading a file"""
        try:
            response = self.s3_service.create_put_presigned_url(
                document_reference.s3_bucket_name, document_reference.s3_file_key
            )
            logger.info(
                f"Successfully created pre-signed URL for {document_reference.s3_file_key}"
            )
            return response
        except ClientError as e:
            logger.error(f"Failed to create pre-signed URL: {str(e)}")
            raise UpdateFhirDocumentReferenceException(500, LambdaError.InternalServerError)

    def _create_fhir_response(
        self,
        document_reference_ndr: DocumentReference,
        presigned_url: str,
    ) -> str:
        """Create a FHIR response document"""

        if presigned_url:
            attachment_url = presigned_url
        else:
            document_retrieve_endpoint = os.getenv(
                "DOCUMENT_RETRIEVE_ENDPOINT_APIM", ""
            )
            attachment_url = (
                document_retrieve_endpoint
                + "/"
                + SnomedCodes.LLOYD_GEORGE.value.code
                + "~"
                + document_reference_ndr.id
            )
        document_details = Attachment(
            title=document_reference_ndr.file_name,
            creation=document_reference_ndr.document_scan_creation
            or document_reference_ndr.created,
            url=attachment_url,
        )
        fhir_document_reference = (
            DocumentReferenceInfo(
                nhs_number=document_reference_ndr.nhs_number,
                attachment=document_details,
                custodian=document_reference_ndr.custodian,
                snomed_code_doc_type=SnomedCodes.find_by_code(
                    document_reference_ndr.document_snomed_code_type
                ),
            )
            .create_fhir_document_reference_object(document_reference_ndr)
            .model_dump_json(exclude_none=True)
        )

        return fhir_document_reference

    def _check_nhs_number_with_pds(self, nhs_number: str) -> PatientDetails:
        try:
            validate_nhs_number(nhs_number)
            pds_service = get_pds_service()
            return pds_service.fetch_patient_details(nhs_number)
        except (
            PatientNotFoundException,
            InvalidResourceIdException,
            PdsErrorException,
        ) as e:
            logger.error(f"Error occurred when fetching patient details: {str(e)}")
            raise UpdateFhirDocumentReferenceException(
                400, LambdaError.CreatePatientSearchInvalid
            )