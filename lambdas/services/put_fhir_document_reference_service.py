import os

from utils.audit_logging_setup import LoggingService
from services.base.dynamo_service import DynamoDBService
from services.base.s3_service import S3Service
from models.fhir.R4.fhir_document_reference import (
    DocumentReference as FhirDocumentReference,
)
from models.document_reference import DocumentReference
from services.document_service import DocumentService
from enums.snomed_codes import SnomedCodes
from enums.lambda_error import LambdaError
from utils.lambda_exceptions import UpdateFhirDocumentReferenceException
from models.fhir.R4.fhir_document_reference import Attachment
from models.fhir.R4.fhir_document_reference import DocumentReferenceInfo

from pydantic import ValidationError
from utils.exceptions import (
    InvalidNhsNumberException,
    DocumentServiceException,
)

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
        try:
            validated_fhir_doc = FhirDocumentReference.model_validate_json(fhir_document)
        except ValidationError as e:
            logger.error(f"FHIR document validation error: {str(e)}")
            raise UpdateFhirDocumentReferenceException(400, LambdaError.UpdateDocNoParse)

        try:
            # Extract document type
            doc_type = self.document_service.determine_document_type(validated_fhir_doc)
        except DocumentServiceException:
            logger.error("Could not determine document type")
            raise UpdateFhirDocumentReferenceException(400, LambdaError.UpdateDocInvalidType)

        # Determine which DynamoDB table to use based on the document type
        dynamo_table = self.document_service.get_dynamo_table_for_doc_type(doc_type)

        try:
            current_doc = self.document_service.get_document_reference(validated_fhir_doc.id, dynamo_table)
        except DocumentServiceException:
            logger.error("No document found for the given document ID.")
            raise UpdateFhirDocumentReferenceException(
                404, LambdaError.DocumentReferenceNotFound
            )

        if not current_doc.doc_status == "final":
            logger.error("Document is not the latest version.")
            raise UpdateFhirDocumentReferenceException(
                400, LambdaError.UpdateDocNotLatestVersion
            )
        
        try:
            put_nhs_number = self.document_service.extract_nhs_number_from_fhir(validated_fhir_doc)
        except DocumentServiceException:
            logger.error("Could not find NHS number in request fhir document reference")
            raise UpdateFhirDocumentReferenceException(400, LambdaError.UpdateDocNoParse)

        if current_doc.nhs_number != put_nhs_number:
            logger.error("NHS numbers do not match.")
            raise UpdateFhirDocumentReferenceException(
                400, LambdaError.UpdateDocNHSNumberMismatch
            )
        
        if validated_fhir_doc.meta is None:
            logger.error("Missing version number")
            raise UpdateFhirDocumentReferenceException(400, LambdaError.DocumentReferenceMissingParameters)
        
        if current_doc.version != validated_fhir_doc.meta.versionId:
            logger.error("Version does not match current version.")
            raise UpdateFhirDocumentReferenceException(400, LambdaError.UpdateDocVersionMismatch)
        
        try:
            patient_details = self.document_service.check_nhs_number_with_pds(put_nhs_number)
        except DocumentServiceException:
            raise UpdateFhirDocumentReferenceException(400, LambdaError.UpdatePatientSearchInvalid)
        
        # Check if binary content is included
        binary_content = validated_fhir_doc.content[0].attachment.data
        
        new_doc_version = int(current_doc.version) + 1

        # Create a document reference model
        document_reference = self.document_service.create_document_reference(
            put_nhs_number,
            doc_type,
            validated_fhir_doc,
            patient_details.general_practice_ods,
            str(new_doc_version)
        )

        presigned_url = None
        # Handle binary content if present, otherwise create a pre-signed URL
        if binary_content:
            try:
                self.document_service.store_binary_in_s3(document_reference, binary_content)
            except DocumentServiceException:
                raise UpdateFhirDocumentReferenceException(500, LambdaError.UpdateDocNoParse)
        else:
            # Create a pre-signed URL for uploading
            try:
                presigned_url = self.document_service.create_s3_presigned_url(document_reference)
            except DocumentServiceException:
                raise UpdateFhirDocumentReferenceException(500, LambdaError.InternalServerError)
        try:
            # Save document reference to DynamoDB
            self.document_service.save_document_reference_to_dynamo(dynamo_table, document_reference)
        except DocumentServiceException:
            raise UpdateFhirDocumentReferenceException(500, LambdaError.UpdateDocUploadInternalError)
        
        try:
            return self._create_fhir_response(document_reference, presigned_url)
        except (ValidationError, InvalidNhsNumberException) as e:
            logger.error(f"FHIR document validation error: {str(e)}")
            raise UpdateFhirDocumentReferenceException(400, LambdaError.UpdateDocNoParse)

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