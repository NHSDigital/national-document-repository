import csv
import os
import shutil
import tempfile
import uuid
from datetime import datetime
from typing import Iterable

import pydantic
from botocore.exceptions import ClientError
from enums.upload_status import UploadStatus
from models.staging_metadata import METADATA_FILENAME, MetadataFile, StagingMetadata
from repositories.bulk_upload.bulk_upload_dynamo_repository import (
    BulkUploadDynamoRepository,
)
from services.base.s3_service import S3Service
from services.base.sqs_service import SQSService
from services.bulk_upload_metadata_preprocessor_service import (
    MetadataPreprocessorService,
)
from utils.audit_logging_setup import LoggingService
from utils.exceptions import (
    BulkUploadMetadataException,
    InvalidFileNameException,
    LGInvalidFilesException,
)
from utils.lloyd_george_validator import validate_file_name

logger = LoggingService(__name__)
UNSUCCESSFUL = "Unsuccessful bulk upload"


class BulkUploadMetadataProcessorService:
    def __init__(self, metadata_formatter_service: MetadataPreprocessorService):
        self.s3_service = S3Service()
        self.sqs_service = SQSService()
        self.dynamo_repository = BulkUploadDynamoRepository()

        self.staging_bucket_name = os.getenv("STAGING_STORE_BUCKET_NAME")
        self.metadata_queue_url = os.getenv("METADATA_SQS_QUEUE_URL")

        self.temp_download_dir = tempfile.mkdtemp()

        self.corrections = {}
        self.practice_directory = metadata_formatter_service.practice_directory
        self.file_key = (
            f"{metadata_formatter_service.practice_directory}/{METADATA_FILENAME}"
            if metadata_formatter_service.practice_directory
            else METADATA_FILENAME
        )
        self.metadata_formatter_service = metadata_formatter_service

    def process_metadata(self):
        try:
            metadata_file = self.download_metadata_from_s3()
            staging_metadata_list = self.csv_to_staging_metadata(metadata_file)
            logger.info("Finished parsing metadata")

            self.send_metadata_to_fifo_sqs(staging_metadata_list)
            logger.info("Sent bulk upload metadata to sqs queue")

            self.copy_metadata_to_dated_folder()

            self.clear_temp_storage()

        except pydantic.ValidationError as e:
            failure_msg = f"Failed to parse {METADATA_FILENAME} due to error: {str(e)}"
            logger.error(failure_msg, {"Result": UNSUCCESSFUL})
            raise BulkUploadMetadataException(failure_msg)
        except KeyError as e:
            failure_msg = f"Failed due to missing key: {str(e)}"
            logger.error(failure_msg, {"Result": UNSUCCESSFUL})
            raise BulkUploadMetadataException(failure_msg)
        except ClientError as e:
            if "HeadObject" in str(e):
                failure_msg = f'No metadata file could be found with the name "{METADATA_FILENAME}"'
            else:
                failure_msg = str(e)
            logger.error(failure_msg, {"Result": UNSUCCESSFUL})
            raise BulkUploadMetadataException(failure_msg)

    def download_metadata_from_s3(self) -> str:
        logger.info(f"Fetching {METADATA_FILENAME} from bucket")

        local_file_path = os.path.join(self.temp_download_dir, METADATA_FILENAME)
        self.s3_service.download_file(
            s3_bucket_name=self.staging_bucket_name,
            file_key=self.file_key,
            download_path=local_file_path,
        )
        return local_file_path

    def csv_to_staging_metadata(self, csv_file_path: str) -> list[StagingMetadata]:
        logger.info("Parsing bulk upload metadata")
        patients = {}
        with open(
            csv_file_path, mode="r", encoding="utf-8-sig", errors="replace"
        ) as csv_file_handler:
            csv_reader: Iterable[dict] = csv.DictReader(csv_file_handler)
            for row in csv_reader:
                self.process_metadata_row(row, patients)
        return [
            StagingMetadata(
                nhs_number=key[0],
                files=value,
            )
            for (key, value) in patients.items()
            # If there are multiple files for a patient AND it's USB mode: do not return those.
        ]

    def process_metadata_row(self, row: dict, patients: dict) -> None:
        file_metadata = MetadataFile.model_validate(row)
        nhs_number, ods_code = self.extract_patient_info(file_metadata)
        patient_record_key = (nhs_number, ods_code)

        if patient_record_key not in patients:
            patients[patient_record_key] = [file_metadata]
        else:
            patients[patient_record_key].append(file_metadata)

        try:
            self.validate_correct_filename(file_metadata)
        except InvalidFileNameException as error:
            self.handle_invalid_filename(
                file_metadata, error, patient_record_key, patients
            )
            patients.pop(patient_record_key)

    def extract_patient_info(self, file_metadata: MetadataFile) -> tuple[str, str]:
        nhs_number = file_metadata.nhs_number
        ods_code = file_metadata.gp_practice_code
        return nhs_number, ods_code

    def validate_correct_filename(
        self,
        file_metadata: MetadataFile,
    ) -> None:
        try:
            validate_file_name(file_metadata.file_path.split("/")[-1])
            valid_filepath = file_metadata.file_path
        except LGInvalidFilesException:
            valid_filepath = self.metadata_formatter_service.validate_record_filename(
                file_metadata.file_path
            )

        if valid_filepath:
            self.corrections[file_metadata.file_path] = valid_filepath

    def handle_invalid_filename(
        self,
        file_metadata: MetadataFile,
        error: InvalidFileNameException,
        key: tuple[str, str],
        patients: dict[tuple[str, str], list[MetadataFile]],
    ) -> None:
        logger.error(
            f"Failed to process {file_metadata.file_path} due to error: {error}"
        )
        failed_entry = StagingMetadata(
            nhs_number=key[0],
            files=patients[key],
        )
        self.dynamo_repository.write_report_upload_to_dynamo(
            failed_entry, UploadStatus.FAILED, str(error)
        )

    def send_metadata_to_fifo_sqs(
        self, staging_metadata_list: list[StagingMetadata]
    ) -> None:
        sqs_group_id = f"bulk_upload_{uuid.uuid4()}"

        for staging_metadata in staging_metadata_list:
            nhs_number = staging_metadata.nhs_number
            logger.info(f"Sending metadata for patientId: {nhs_number}")

            self.sqs_service.send_message_with_nhs_number_attr_fifo(
                queue_url=self.metadata_queue_url,
                message_body=staging_metadata.model_dump_json(by_alias=True),
                nhs_number=nhs_number,
                group_id=sqs_group_id,
            )

    def copy_metadata_to_dated_folder(self):
        logger.info("Copying metadata CSV to dated folder")

        current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M")

        self.s3_service.copy_across_bucket(
            self.staging_bucket_name,
            self.file_key,
            self.staging_bucket_name,
            f"metadata/{current_datetime}.csv",
        )

        self.s3_service.delete_object(self.staging_bucket_name, METADATA_FILENAME)

    def clear_temp_storage(self):
        logger.info("Clearing temp storage directory")
        shutil.rmtree(self.temp_download_dir)
