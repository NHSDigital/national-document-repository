import os

from enums.metadata_field_names import DocumentReferenceMetadataFields
from enums.upload_status import UploadStatus
from models.document_reference import DocumentReference
from models.report.bulk_upload_report import BulkUploadReport
from models.staging_metadata import StagingMetadata
from services.base.dynamo_service import DynamoDBService
from utils.audit_logging_setup import LoggingService

_logger = LoggingService(__name__)


class BulkUploadDynamoRepository:
    def __init__(self):
        self.bulk_upload_report_dynamo_table = os.environ["BULK_UPLOAD_DYNAMODB_NAME"]
        self.lg_dynamo_table = os.environ["LLOYD_GEORGE_DYNAMODB_NAME"]
        self.lg_bucket_name = os.environ["LLOYD_GEORGE_BUCKET_NAME"]

        self.dynamo_records_in_transaction: list[DocumentReference] = []
        self.dynamo_repository = DynamoDBService()

    def create_record_in_lg_dynamo_table(self, document_reference: DocumentReference):
        self.dynamo_repository.create_item(
            table_name=self.lg_dynamo_table,
            item=document_reference.model_dump(by_alias=True, exclude_none=True),
        )
        self.dynamo_records_in_transaction.append(document_reference)

    def write_report_upload_to_dynamo(
        self,
        staging_metadata: StagingMetadata,
        upload_status: UploadStatus,
        reason: str = None,
        pds_ods_code: str = "",
    ):
        nhs_number = staging_metadata.nhs_number

        for file in staging_metadata.files:
            dynamo_record = BulkUploadReport(
                upload_status=upload_status,
                nhs_number=nhs_number,
                reason=reason,
                file_path=file.file_path,
                stored_file_name=file.stored_file_name,
                pds_ods_code=pds_ods_code,
                uploader_ods_code=file.gp_practice_code,
            )
            self.dynamo_repository.create_item(
                table_name=self.bulk_upload_report_dynamo_table,
                item=dynamo_record.model_dump(by_alias=True, exclude_none=True),
            )

    def init_transaction(self):
        self.dynamo_records_in_transaction = []

    def rollback_transaction(self):
        for document_reference in self.dynamo_records_in_transaction:
            primary_key_name = DocumentReferenceMetadataFields.ID.value
            primary_key_value = document_reference.id
            deletion_key = {primary_key_name: primary_key_value}
            self.dynamo_repository.delete_item(
                table_name=self.lg_dynamo_table, key=deletion_key
            )
