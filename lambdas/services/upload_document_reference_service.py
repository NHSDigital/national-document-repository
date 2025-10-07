import os
from typing import Optional

from botocore.exceptions import ClientError
from enums.lambda_error import LambdaError
from enums.snomed_codes import SnomedCodes
from enums.virus_scan_result import VirusScanResult
from models.document_reference import DocumentReference
from services.base.dynamo_service import DynamoDBService
from services.base.s3_service import S3Service
from services.document_service import DocumentService
from utils.audit_logging_setup import LoggingService
from utils.common_query_filters import PreliminaryStatus
from utils.dynamo_utils import DocTypeTableRouter
from utils.exceptions import DocumentServiceException, FileProcessingException
from utils.lambda_exceptions import InvalidDocTypeException
from utils.s3_utils import DocTypeS3BucketRouter
from utils.utilities import get_virus_scan_service

logger = LoggingService(__name__)


class UploadDocumentReferenceService:
    def __init__(self):
        self.staging_s3_bucket_name = os.getenv("STAGING_STORE_BUCKET_NAME")
        self.table_name = os.getenv("LLOYD_GEORGE_DYNAMODB_NAME")
        self.destination_bucket_name = os.getenv("LLOYD_GEORGE_BUCKET_NAME")
        self.document_service = DocumentService()
        self.dynamo_service = DynamoDBService()
        self.virus_scan_service = get_virus_scan_service()
        self.s3_service = S3Service()
        self.table_router = DocTypeTableRouter()
        self.bucket_router = DocTypeS3BucketRouter()

    def handle_upload_document_reference_request(
        self, object_key: str, object_size: int = 0
    ):
        """Handle the upload document reference request with comprehensive error handling"""
        if not object_key:
            logger.error("Invalid or empty object_key provided")
            return

        try:
            object_parts = object_key.split("/")
            document_key = object_parts[-1]

            self.table_name = self._get_dynamo_table_for_document_key(object_parts)
            self.destination_bucket_name = self._get_s3_bucket_for_document_key(
                object_parts
            )
            document_reference = self._fetch_document_reference(document_key)
            if not document_reference:
                return

            self._process_document_reference(
                document_reference, object_key, object_size
            )

        except Exception as e:
            logger.error(f"Unexpected error processing document reference: {str(e)}")
            logger.error(f"Failed to process document reference: {object_key}")
            return

    def _get_dynamo_table_for_document_key(self, object_parts: list[str]) -> str:
        if object_parts[0] != "fhir_upload":
            doc_type = SnomedCodes.LLOYD_GEORGE.value
            return self.table_router.resolve(doc_type)

        doc_type = SnomedCodes.find_by_code(object_parts[1])
        if doc_type:
            try:
                return self.table_router.resolve(doc_type)
            except KeyError:
                logger.error(
                    f"SNOMED code {doc_type.code} - {doc_type.display_name} is not supported"
                )
                raise InvalidDocTypeException(400, LambdaError.DocTypeDB)
        doc_type = SnomedCodes.LLOYD_GEORGE.value
        return self.table_router.resolve(doc_type)

    def _get_s3_bucket_for_document_key(self, object_parts: list[str]) -> str:
        if object_parts[0] != "fhir_upload":
            doc_type = SnomedCodes.LLOYD_GEORGE.value
            return self.bucket_router.resolve(doc_type)

        doc_type = SnomedCodes.find_by_code(object_parts[1])
        if doc_type:
            try:
                return self.bucket_router.resolve(doc_type)
            except KeyError:
                logger.error(
                    f"SNOMED code {doc_type.code} - {doc_type.display_name} is not supported"
                )
                raise InvalidDocTypeException(400, LambdaError.DocTypeInvalid)
        doc_type = SnomedCodes.LLOYD_GEORGE.value
        return self.bucket_router.resolve(doc_type)

    def _fetch_document_reference(
        self, document_key: str
    ) -> Optional[DocumentReference]:
        """Fetch document reference from the database"""
        try:

            documents = self.document_service.fetch_documents_from_table(
                table=self.table_name,
                search_condition=document_key,
                search_key="ID",
                query_filter=PreliminaryStatus,
            )
            if not documents:
                logger.error(
                    f"No document with the following key found in {self.table_name} table: {document_key}"
                )
                logger.info("Skipping this object")
                return None

            if len(documents) > 1:
                logger.warning(
                    f"Multiple documents found for key {document_key}, using first one"
                )

            return documents[0]

        except ClientError as e:
            logger.error(
                f"Error fetching document reference for key {document_key}: {str(e)}"
            )
            raise DocumentServiceException(
                f"Failed to fetch document reference: {str(e)}"
            )

    def _process_document_reference(
        self, document_reference: DocumentReference, object_key: str, object_size: int
    ):
        """Process the document reference with virus scanning and file operations"""
        try:
            virus_scan_result = self._perform_virus_scan(document_reference)
            document_reference.virus_scanner_result = virus_scan_result

            if virus_scan_result == VirusScanResult.CLEAN:
                self._process_clean_document(
                    document_reference,
                    object_key,
                )
            else:
                logger.warning(f"Document {document_reference.id} failed virus scan")
            document_reference.file_size = object_size
            document_reference.uploaded = True
            document_reference.uploading = False
            self.update_dynamo_table(document_reference, virus_scan_result)

        except Exception as e:
            logger.error(
                f"Error processing document reference {document_reference.id}: {str(e)}"
            )
            raise

    def _perform_virus_scan(
        self, document_reference: DocumentReference
    ) -> VirusScanResult:
        """Perform a virus scan on the document"""
        try:
            return self.virus_scan_service.scan_file(
                document_reference.s3_file_key, nhs_number=document_reference.nhs_number
            )

        except Exception as e:
            logger.error(
                f"Virus scan failed for document {document_reference.id}: {str(e)}"
            )
            return VirusScanResult.ERROR

    def _process_clean_document(
        self, document_reference: DocumentReference, object_key: str
    ):
        """Process a document that passed virus scanning"""
        try:
            self.copy_files_from_staging_bucket(document_reference, object_key)
            self.delete_file_from_staging_bucket(object_key)
            logger.info(
                f"Successfully processed clean document: {document_reference.id}"
            )

        except Exception as e:
            logger.error(
                f"Error processing clean document {document_reference.id}: {str(e)}"
            )
            document_reference.doc_status = "cancelled"
            raise FileProcessingException(f"Failed to process clean document: {str(e)}")

    def copy_files_from_staging_bucket(
        self, document_reference: DocumentReference, source_file_key: str
    ):
        """Copy files from staging bucket to destination bucket"""
        try:
            logger.info("Copying files from staging bucket")

            dest_file_key = f"{document_reference.nhs_number}/{document_reference.id}"

            self.s3_service.copy_across_bucket(
                source_bucket=self.staging_s3_bucket_name,
                source_file_key=source_file_key,
                dest_bucket=self.destination_bucket_name,
                dest_file_key=dest_file_key,
            )

            document_reference.s3_file_key = dest_file_key
            document_reference.s3_bucket_name = self.destination_bucket_name
            document_reference.file_location = document_reference._build_s3_location(
                self.destination_bucket_name, dest_file_key
            )

        except ClientError as e:
            logger.error(f"Error copying files from staging bucket: {str(e)}")
            raise FileProcessingException(
                f"Failed to copy file from staging bucket: {str(e)}"
            )

    def delete_file_from_staging_bucket(self, source_file_key: str):
        """Delete file from staging bucket"""
        try:
            logger.info(f"Deleting file from staging bucket: {source_file_key}")
            self.s3_service.delete_object(self.staging_s3_bucket_name, source_file_key)

        except ClientError as e:
            logger.error(f"Error deleting file from staging bucket: {str(e)}")

    def update_dynamo_table(
        self,
        document: DocumentReference,
        scan_result: VirusScanResult,
    ):
        """Update the DynamoDB table with document status and virus scan results"""
        try:
            logger.info("Updating dynamo db table")

            document.doc_status = (
                "cancelled" if scan_result != VirusScanResult.CLEAN else "final"
            )
            update_fields = {
                "virus_scanner_result",
                "doc_status",
                "file_location",
                "file_size",
                "uploaded",
                "uploading",
            }

            self.document_service.update_document(
                table_name=self.table_name,
                document_reference=document,
                update_fields_name=update_fields,
            )

        except ClientError as e:
            logger.error(f"Error updating DynamoDB table: {str(e)}")
            raise DocumentServiceException(
                f"Failed to update document in database: {str(e)}"
            )
