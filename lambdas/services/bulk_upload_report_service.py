import csv
import datetime
import os
from typing import Optional

from boto3.dynamodb.conditions import Attr
from models.bulk_upload_status import FieldNamesForBulkUploadReport
from utils.audit_logging_setup import LoggingService

logger = LoggingService(__name__)


class BulkUploadReportService:
    def report_handler(self, db_service_class, s3_service_class):
        db_service = db_service_class()
        s3_service = s3_service_class()
        staging_bucket_name = os.getenv("STAGING_STORE_BUCKET_NAME")
        start_time, end_time = self.get_times_for_scan()
        report_data = self.get_dynamodb_report_items(
            db_service, int(start_time.timestamp()), int(end_time.timestamp())
        )
        if report_data:
            file_name = (
                f"Bulk upload report for {str(start_time)} to {str(end_time)}.csv"
            )
            self.write_items_to_csv(report_data, f"/tmp/{file_name}")
        else:
            file_name = (
                f"Bulk upload report for {str(start_time)} to {str(end_time)}.txt"
            )
            self.write_empty_report(f"/tmp/{file_name}")
        logger.info("Uploading new report file to S3")
        s3_service.upload_file(
            s3_bucket_name=staging_bucket_name,
            file_key=f"reports/{file_name}",
            file_name=f"/tmp/{file_name}",
        )

    @staticmethod
    def get_dynamodb_report_items(
        db_service, start_timestamp: int, end_timestamp: int
    ) -> Optional[list]:
        logger.info("Starting Scan on DynamoDB table")
        bulk_upload_table_name = os.getenv("BULK_UPLOAD_DYNAMODB_NAME")
        filter_time = Attr("Timestamp").gt(start_timestamp) & Attr("Timestamp").lt(
            end_timestamp
        )
        db_response = db_service.scan_table(
            bulk_upload_table_name, filter_expression=filter_time
        )

        if "Items" not in db_response:
            return None
        items = db_response["Items"]
        while "LastEvaluatedKey" in db_response:
            db_response = db_service.scan_table(
                bulk_upload_table_name,
                exclusive_start_key=db_response["LastEvaluatedKey"],
                filter_expression=filter_time,
            )
            if db_response["Items"]:
                items.extend(db_response["Items"])
        return items

    @staticmethod
    def write_items_to_csv(items: list, csv_file_path: str):
        logger.info("Writing scan results to csv file")
        with open(csv_file_path, "w") as output_file:
            field_names = FieldNamesForBulkUploadReport
            dict_writer_object = csv.DictWriter(output_file, fieldnames=field_names)
            dict_writer_object.writeheader()
            for item in items:
                dict_writer_object.writerow(item)

    @staticmethod
    def get_times_for_scan():
        current_time = datetime.datetime.now()
        end_report_time = datetime.time(7, 00, 00, 0)
        today_date = datetime.datetime.today()
        end_timestamp = datetime.datetime.combine(today_date, end_report_time)
        if current_time < end_timestamp:
            end_timestamp -= datetime.timedelta(days=1)
        start_timestamp = end_timestamp - datetime.timedelta(days=1)
        return start_timestamp, end_timestamp

    @staticmethod
    def write_empty_report(file_path: str):
        with open(file_path, "w") as output_file:
            output_file.write("No data was found for this timeframe")
