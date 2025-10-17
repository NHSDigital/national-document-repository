import os

from enums.dynamo_filter import AttributeOperator
from enums.lambda_error import LambdaError
from enums.supported_document_types import SupportedDocumentTypes
from enums.trace_status import TraceStatus
from models.document_reference import DocumentReference
from models.zip_trace import DocumentManifestJob, DocumentManifestZipTrace
from pydantic import ValidationError
from services.base.dynamo_service import DynamoDBService
from services.base.s3_service import S3Service
from services.document_service import DocumentService
from utils.audit_logging_setup import LoggingService
from utils.common_query_filters import UploadCompleted
from utils.dynamo_query_filter_builder import DynamoQueryFilterBuilder
from utils.lambda_exceptions import DocumentManifestJobServiceException
from utils.utilities import flatten, get_file_key_from_s3_url

logger = LoggingService(__name__)


class DocumentManifestJobService:
    def __init__(self):
        create_document_aws_role_arn = os.getenv("PRESIGNED_ASSUME_ROLE")
        self.s3_service = S3Service(custom_aws_role=create_document_aws_role_arn)
        self.document_service = DocumentService()
        self.dynamo_service = DynamoDBService()
        self.zip_output_bucket = os.environ["ZIPPED_STORE_BUCKET_NAME"]
        self.zip_trace_table = os.environ["ZIPPED_STORE_DYNAMODB_NAME"]
        self.documents: list[DocumentReference] = []

    def create_document_manifest_job(
        self,
        nhs_number: str,
        doc_types: list[SupportedDocumentTypes],
        selected_document_references: list[str] = None,
    ) -> str:
        logger.info("Retrieving Document References for manifest")

        self.documents = flatten(
            [
                self.document_service.fetch_available_document_references_by_type(
                    nhs_number=nhs_number,
                    doc_type=doc_type,
                    query_filter=UploadCompleted,
                )
                for doc_type in doc_types
            ]
        )

        if not self.documents:
            logger.error(
                f"{LambdaError.ManifestNoDocs.to_str()}",
                {"Result": "Failed to create document manifest job"},
            )
            raise DocumentManifestJobServiceException(404, LambdaError.ManifestNoDocs)

        if selected_document_references:
            self.documents = self.filter_documents_by_reference(
                selected_document_references=selected_document_references,
            )

        self.handle_duplicate_document_filenames()

        documents_to_download = {
            document.file_location: document.file_name for document in self.documents
        }

        job_id = self.write_zip_trace(documents_to_download, nhs_number)

        return job_id

    def filter_documents_by_reference(
        self,
        selected_document_references: list[str],
    ) -> list[DocumentReference]:
        logger.info("Filtering Selected Document References for manifest")

        reference_set = set(selected_document_references)
        matched_references = [
            document_reference
            for document_reference in self.documents
            if document_reference.id in reference_set
        ]

        if not matched_references:
            raise DocumentManifestJobServiceException(
                400, LambdaError.ManifestFilterDocumentReferences
            )

        return matched_references

    def handle_duplicate_document_filenames(self):
        file_names_to_be_zipped = {}

        for document in self.documents:
            file_name = document.file_name
            duplicated_filename = file_name in file_names_to_be_zipped

            if duplicated_filename:
                file_names_to_be_zipped[file_name] += 1
                document.file_name = document.create_unique_filename(
                    file_names_to_be_zipped[file_name]
                )
            else:
                file_names_to_be_zipped[file_name] = 1

    def write_zip_trace(
        self,
        documents_to_download: dict,
        nhs_number: str,
    ) -> str:
        logger.info("Writing Document Manifest zip trace to db")

        zip_trace = DocumentManifestZipTrace(
            files_to_download=documents_to_download, nhs_number=nhs_number
        )
        self.dynamo_service.create_item(
            self.zip_trace_table, zip_trace.model_dump(by_alias=True)
        )

        return str(zip_trace.job_id)

    def query_document_manifest_job(
        self, job_id: str, nhs_number: str
    ) -> DocumentManifestJob:
        zip_trace = self.query_zip_trace(job_id=job_id, nhs_number=nhs_number)

        match zip_trace.job_status:
            case TraceStatus.FAILED:
                raise DocumentManifestJobServiceException(
                    500, LambdaError.ManifestFailure
                )
            case TraceStatus.PENDING:
                return DocumentManifestJob(job_status=TraceStatus.PENDING, url="")
            case TraceStatus.PROCESSING:
                return DocumentManifestJob(job_status=TraceStatus.PROCESSING, url="")
            case TraceStatus.COMPLETED:
                presigned_url = self.create_document_manifest_presigned_url(
                    zip_trace.zip_file_location
                )
                logger.info(
                    "User has downloaded Lloyd George records",
                    {"Result": "Successful download"},
                )

                return DocumentManifestJob(
                    job_status=TraceStatus.COMPLETED, url=presigned_url
                )

    def create_document_manifest_presigned_url(self, zip_file_location: str):
        file_key = get_file_key_from_s3_url(zip_file_location)
        is_manifest_ready = self.s3_service.file_exist_on_s3(
            s3_bucket_name=self.zip_output_bucket, file_key=file_key
        )
        if not is_manifest_ready:
            logger.error("No Document Manifest found")
            raise DocumentManifestJobServiceException(
                404, LambdaError.ManifestMissingJob
            )
        return self.s3_service.create_download_presigned_url(
            s3_bucket_name=self.zip_output_bucket,
            file_key=file_key,
        )

    def query_zip_trace(self, job_id: str, nhs_number: str) -> DocumentManifestZipTrace:
        filter_builder = DynamoQueryFilterBuilder()
        nhs_number_filter_expression = filter_builder.add_condition(
            attribute="NhsNumber",
            attr_operator=AttributeOperator.EQUAL,
            filter_value=nhs_number,
        ).build()
        response = self.dynamo_service.query_table(
            table_name=self.zip_trace_table,
            index_name="JobIdIndex",
            search_key="JobId",
            search_condition=job_id,
            requested_fields=DocumentManifestZipTrace.get_field_names_alias_list(),
            query_filter=nhs_number_filter_expression,
        )

        try:
            zip_trace = DocumentManifestZipTrace.model_validate(response[0])
            return zip_trace
        except (KeyError, IndexError, ValidationError) as e:
            logger.error(
                f"{LambdaError.ManifestMissingJob.to_str()}: {str(e)}",
                {"Result": "Failed to create document manifest job"},
            )
            raise DocumentManifestJobServiceException(
                404, LambdaError.ManifestMissingJob
            )
