import base64
import binascii
import io
import os

from typing import Optional
from botocore.exceptions import ClientError
from enums.lambda_error import LambdaError
from enums.patient_ods_inactive_status import PatientOdsInactiveStatus
from enums.snomed_codes import SnomedCode, SnomedCodes
from models.document_reference import DocumentReference
from models.fhir.R4.fhir_document_reference import SNOMED_URL, Attachment
from models.fhir.R4.fhir_document_reference import (
    DocumentReference as FhirDocumentReference,
)
from models.fhir.R4.fhir_document_reference import DocumentReferenceInfo
from models.pds_models import PatientDetails
from pydantic import ValidationError
from services.base.dynamo_service import DynamoDBService
from services.base.s3_service import S3Service
from utils.audit_logging_setup import LoggingService
from utils.exceptions import (
    InvalidNhsNumberException,
    InvalidResourceIdException,
    PatientNotFoundException,
    PdsErrorException,
)
from utils.lambda_exceptions import CreateDocumentRefException
from utils.ods_utils import PCSE_ODS_CODE
from utils.utilities import create_reference_id, get_pds_service, validate_nhs_number

logger = LoggingService(__name__)


class PostFhirDocumentReferenceService:
    def __init__(self):
        presigned_aws_role_arn = os.getenv("PRESIGNED_ASSUME_ROLE")
        self.s3_service = S3Service(custom_aws_role=presigned_aws_role_arn)
        self.dynamo_service = DynamoDBService()

        self.lg_dynamo_table = os.getenv("LLOYD_GEORGE_DYNAMODB_NAME")
        self.pdm_dynamo_table = os.getenv("PDM_DYNAMODB_NAME")
        self.staging_bucket_name = os.getenv("STAGING_STORE_BUCKET_NAME")

    def process_fhir_document_reference(
        self, fhir_document: str, request_headers: dict = {}
    ) -> str:
        """
        Process a FHIR Document Reference request

        Args:
            fhir_document: FHIR Document Reference object

        Returns:
            FHIR Document Reference response JSON object
        """
        try:
            headers = {k.lower(): v for k, v in request_headers.items()}
            common_name = self._validate_headers(headers)

            validated_fhir_doc = FhirDocumentReference.model_validate_json(
                fhir_document
            )

            # Extract NHS number from the FHIR document
            nhs_number = self._extract_nhs_number_from_fhir(validated_fhir_doc)
            patient_details = self._check_nhs_number_with_pds(nhs_number)

            # Extract document type
            doc_type = self._determine_document_type(validated_fhir_doc, common_name)

            # Determine which DynamoDB table to use based on the document type
            dynamo_table = self._get_dynamo_table_for_doc_type(doc_type)

            # Check if binary content is included
            binary_content = validated_fhir_doc.content[0].attachment.data

            # Create a document reference model
            document_reference = self._create_document_reference(
                nhs_number,
                doc_type,
                validated_fhir_doc,
                patient_details.general_practice_ods,
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
            raise CreateDocumentRefException(400, LambdaError.CreateDocNoParse)
        except ClientError as e:
            logger.error(f"AWS client error: {str(e)}")
            raise CreateDocumentRefException(500, LambdaError.InternalServerError)

    def _validate_headers(self, headers: dict) -> Optional[str]:
        subject = headers.get("x-amzn-mtls-clientcert-subject", "")
        common_name = None
        if "CN=" in subject:
            for part in subject.split(","):
                if part.strip().startswith("CN="):
                    common_name = part.strip().split("=", 1)[1]
                    break
        return common_name

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

        raise CreateDocumentRefException(400, LambdaError.CreateDocNoParse)

    def _determine_document_type(
        self, fhir_doc: FhirDocumentReference, common_name
    ) -> SnomedCode:
        if not common_name:
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
                        raise CreateDocumentRefException(
                            400, LambdaError.CreateDocInvalidType
                        )
            logger.error("SNOMED code not found in FHIR document")
            raise CreateDocumentRefException(400, LambdaError.CreateDocInvalidType)

        if common_name != "pdm":
            logger.error(f"mTLS common name {common_name} - is not supported")
            raise CreateDocumentRefException(400, LambdaError.CreateDocInvalidType)

        return SnomedCodes.UNSTRUCTURED.value

    def _get_dynamo_table_for_doc_type(self, doc_type: SnomedCode) -> str:
        """Get the appropriate DynamoDB table name based on a document type"""
        if doc_type == SnomedCodes.LLOYD_GEORGE.value:
            return self.lg_dynamo_table
        else:
            return self.pdm_dynamo_table

    def _create_document_reference(
        self,
        nhs_number: str,
        doc_type: SnomedCode,
        fhir_doc: FhirDocumentReference,
        current_gp_ods: str,
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
            raise CreateDocumentRefException(
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
            raise CreateDocumentRefException(500, LambdaError.CreateDocNoParse)
        except MemoryError as e:
            logger.error(f"File too large to process: {str(e)}")
            raise CreateDocumentRefException(500, LambdaError.CreateDocNoParse)
        except ClientError as e:
            logger.error(f"Failed to store binary in S3: {str(e)}")
            raise CreateDocumentRefException(500, LambdaError.CreateDocNoParse)
        except (OSError, IOError) as e:
            logger.error(f"I/O error when processing binary content: {str(e)}")
            raise CreateDocumentRefException(500, LambdaError.CreateDocNoParse)

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
            raise CreateDocumentRefException(500, LambdaError.InternalServerError)

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
                + document_reference_ndr.document_snomed_code_type
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
            raise CreateDocumentRefException(
                400, LambdaError.CreatePatientSearchInvalid
            )
