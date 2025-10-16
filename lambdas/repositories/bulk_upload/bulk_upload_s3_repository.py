import os

from botocore.exceptions import ClientError
from enums.virus_scan_result import SCAN_RESULT_TAG_KEY, VirusScanResult
from models.document_reference import DocumentReference
from models.staging_metadata import StagingSqsMetadata
from services.base.s3_service import S3Service
from utils.audit_logging_setup import LoggingService
from utils.exceptions import (
    DocumentInfectedException,
    S3FileNotFoundException,
    TagNotFoundException,
    VirusScanFailedException,
    VirusScanNoResultException,
)

_logger = LoggingService(__name__)


class BulkUploadS3Repository:
    def __init__(self):
        self.s3_repository = S3Service()
        self.staging_bucket_name = os.environ["STAGING_STORE_BUCKET_NAME"]
        self.lg_bucket_name: str = os.environ["LLOYD_GEORGE_BUCKET_NAME"]

        self.dynamo_records_in_transaction: list[DocumentReference] = []
        self.source_bucket_files_in_transaction = []
        self.dest_bucket_files_in_transaction = []

    def check_virus_result(
        self, staging_metadata: StagingSqsMetadata, file_path_cache: dict
    ):
        for file_metadata in staging_metadata.files:
            file_path = file_metadata.file_path
            source_file_key = file_path_cache[file_path]
            try:
                scan_result = self.s3_repository.get_tag_value(
                    self.staging_bucket_name, source_file_key, SCAN_RESULT_TAG_KEY
                )
                if scan_result == VirusScanResult.CLEAN:
                    continue
                elif scan_result == VirusScanResult.INFECTED:
                    raise DocumentInfectedException(
                        f"Found infected document: {file_path}"
                    )
                else:
                    # handle cases other than Clean or Infected e.g. Unscannable, Error
                    raise VirusScanFailedException(
                        f"Failed to scan document: {file_path}, scan result was {scan_result}"
                    )
            except TagNotFoundException:
                raise VirusScanNoResultException(
                    f"Virus scan result not found for document: {file_path}"
                )
            except ClientError as e:
                if "AccessDenied" in str(e) or "NoSuchKey" in str(e):
                    _logger.info(
                        f"Failed to check object tag for given file_path: {file_path}"
                    )
                    _logger.info(
                        "file_path may be incorrect or contain invalid character"
                    )
                    raise S3FileNotFoundException(f"Failed to access file {file_path}")
                else:
                    raise e

        _logger.info(
            f"Verified that all documents for patient {staging_metadata.nhs_number} are clean."
        )

    def copy_to_lg_bucket(self, source_file_key: str, dest_file_key: str):
        self.s3_repository.copy_across_bucket(
            source_bucket=self.staging_bucket_name,
            source_file_key=source_file_key,
            dest_bucket=self.lg_bucket_name,
            dest_file_key=dest_file_key,
        )
        self.source_bucket_files_in_transaction.append(source_file_key)
        self.dest_bucket_files_in_transaction.append(dest_file_key)

    def remove_ingested_file_from_source_bucket(self):
        for source_file_key in self.source_bucket_files_in_transaction:
            self.s3_repository.delete_object(
                s3_bucket_name=self.staging_bucket_name, file_key=source_file_key
            )

    def init_transaction(self):
        self.source_bucket_files_in_transaction = []
        self.dest_bucket_files_in_transaction = []

    def rollback_transaction(self):
        for dest_bucket_file_key in self.dest_bucket_files_in_transaction:
            self.s3_repository.delete_object(
                s3_bucket_name=self.lg_bucket_name, file_key=dest_bucket_file_key
            )

    def file_exists_on_staging_bucket(self, file_key: str) -> bool:
        return self.s3_repository.file_exist_on_s3(self.staging_bucket_name, file_key)
