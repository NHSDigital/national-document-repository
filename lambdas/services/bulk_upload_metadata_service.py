import csv
import os
import shutil
import tempfile
import uuid
from datetime import datetime
from typing import Iterable

import pydantic
from botocore.exceptions import ClientError
from models.staging_metadata import (
    NHS_NUMBER_FIELD_NAME,
    ODS_CODE,
    MetadataFile,
    StagingMetadata,
)
from services.base.cloudwatch_service import CloudwatchService
from services.base.s3_service import S3Service
from services.base.sqs_service import SQSService
from utils.audit_logging_setup import LoggingService
from utils.exceptions import BulkUploadMetadataException

logger = LoggingService(__name__)
unsuccessful = "Unsuccessful bulk upload"


class BulkUploadMetadataService:
    def __init__(self, metrics=None):
        self.s3_service = S3Service()
        self.sqs_service = SQSService()
        self.cloudwatch_service = CloudwatchService()
        self.metrics = metrics

        self.staging_bucket_name = os.environ["STAGING_STORE_BUCKET_NAME"]
        self.metadata_queue_url = os.environ["METADATA_SQS_QUEUE_URL"]

        self.temp_download_dir = tempfile.mkdtemp()

    def process_metadata(self, metadata_filename: str):
        try:
            metadata_file = self.download_metadata_from_s3(metadata_filename)

            staging_metadata_list = self.csv_to_staging_metadata(metadata_file)
            logger.info("Finished parsing metadata")

            self.send_metadata_to_fifo_sqs(staging_metadata_list)
            logger.info("Sent bulk upload metadata to sqs queue")

            self.copy_metadata_to_dated_folder(metadata_filename)

            self.clear_temp_storage()

        except pydantic.ValidationError as e:
            failure_msg = f"Failed to parse {metadata_filename}: {str(e)}"
            logger.error(failure_msg, {"Result": unsuccessful})
            raise BulkUploadMetadataException(failure_msg)
        except KeyError as e:
            failure_msg = f"Failed due to missing key: {str(e)}"
            logger.error(failure_msg, {"Result": unsuccessful})
            raise BulkUploadMetadataException(failure_msg)
        except ClientError as e:
            if "HeadObject" in str(e):
                failure_msg = f'No metadata file could be found with the name "{metadata_filename}"'
            else:
                failure_msg = str(e)
            logger.error(failure_msg, {"Result": unsuccessful})
            raise BulkUploadMetadataException(failure_msg)

    def download_metadata_from_s3(self, metadata_filename: str) -> str:
        logger.info(f"Fetching {metadata_filename} from bucket")

        local_file_path = os.path.join(self.temp_download_dir, metadata_filename)
        self.s3_service.download_file(
            s3_bucket_name=self.staging_bucket_name,
            file_key=metadata_filename,
            download_path=local_file_path,
        )
        return local_file_path

    @staticmethod
    def csv_to_staging_metadata(csv_file_path: str) -> list[StagingMetadata]:
        logger.info("Parsing bulk upload metadata")

        patients = {}
        with open(
            csv_file_path, mode="r", encoding="utf-8-sig", errors="replace"
        ) as csv_file_handler:
            csv_reader: Iterable[dict] = csv.DictReader(csv_file_handler)
            for row in csv_reader:
                file_metadata = MetadataFile.model_validate(row)
                nhs_number = row[NHS_NUMBER_FIELD_NAME]
                ods_code = row[ODS_CODE]
                key = (nhs_number, ods_code)
                if key not in patients:
                    patients[key] = [file_metadata]
                else:
                    patients[key].append(file_metadata)

        return [
            StagingMetadata(
                nhs_number=nhs_number,
                files=patients[nhs_number, ods_code],
            )
            for (nhs_number, ods_code) in patients
        ]

    def publish_ods_code_queued_metrics(
        self, staging_metadata: StagingMetadata
    ) -> None:
        ods_code = (
            staging_metadata.files[0].gp_practice_code
            if staging_metadata.files
            else "UNKNOWN"
        )
        self.metrics.set_namespace("Custom_metrics/BulkUpload")
        self.metrics.put_dimension("ODSCode", ods_code)
        self.metrics.put_metric("MessagesSent", 1, "Count")

    def send_metadata_to_fifo_sqs(
        self, staging_metadata_list: list[StagingMetadata]
    ) -> None:
        sqs_group_id = f"bulk_upload_{uuid.uuid4()}"

        for staging_metadata in staging_metadata_list:
            nhs_number = staging_metadata.nhs_number
            self.publish_ods_code_queued_metrics(staging_metadata)

            logger.info(f"Sending metadata for patientId: {nhs_number}")

            self.sqs_service.send_message_with_nhs_number_attr_fifo(
                queue_url=self.metadata_queue_url,
                message_body=staging_metadata.model_dump_json(by_alias=True),
                nhs_number=nhs_number,
                group_id=sqs_group_id,
            )

    def copy_metadata_to_dated_folder(self, metadata_filename: str):
        logger.info("Copying metadata CSV to dated folder")

        current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M")

        self.s3_service.copy_across_bucket(
            self.staging_bucket_name,
            metadata_filename,
            self.staging_bucket_name,
            f"metadata/{current_datetime}.csv",
        )

        self.s3_service.delete_object(self.staging_bucket_name, metadata_filename)

    def clear_temp_storage(self):
        logger.info("Clearing temp storage directory")
        shutil.rmtree(self.temp_download_dir)
