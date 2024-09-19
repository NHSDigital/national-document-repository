import csv
import datetime
import os
from typing import Optional

from boto3.dynamodb.conditions import Attr
from enums.metadata_report import MetadataReport
from services.base.dynamo_service import DynamoDBService
from services.base.s3_service import S3Service
from utils.audit_logging_setup import LoggingService

logger = LoggingService(__name__)


class OdsReport:
    def __init__(
        self,
        ods_code: str,
        total_successful=0,
        total_registered_elsewhere=0,
        total_suspended=0,
        failure_reasons=None,
    ):
        self.ods_code = ods_code
        self.total_successful = total_successful
        self.total_registered_elsewhere = total_registered_elsewhere
        self.total_suspended = total_suspended

        if failure_reasons is None:
            failure_reasons = {}
        self.failure_reasons = failure_reasons


class BulkUploadReportService:
    def __init__(self):
        self.db_service = DynamoDBService()
        self.s3_service = S3Service()
        self.reports_bucket = os.getenv("STATISTICAL_REPORTS_BUCKET_NAME")

    def report_handler(self):
        start_time, end_time = self.get_times_for_scan()
        report_data = self.get_dynamodb_report_items(
            int(start_time.timestamp()), int(end_time.timestamp())
        )

        if report_data:
            generated_at = end_time.strftime("%Y%m%d")
            ods_reports: list[OdsReport] = self.generate_ods_reports(
                report_data, generated_at
            )
            self.generate_summary_report(ods_reports, generated_at)
        else:
            logger.info("No data found, no new report file to upload")

    def generate_ods_reports(
        self, report_data: list[dict], generated_at: str
    ) -> list[OdsReport]:
        ods_reports: list[OdsReport] = []

        grouped_ods_data = {}
        for item in report_data:
            uploader_ods_code = item.get(MetadataReport.UploaderOdsCode)

            if uploader_ods_code not in grouped_ods_data:
                grouped_ods_data[uploader_ods_code] = []
            grouped_ods_data[uploader_ods_code].append(item)

        for ods_code, ods_data in grouped_ods_data.items():
            logger.info(f"Generating ODS report file for {ods_code}")
            ods_report = self.generate_individual_ods_report(ods_code, grouped_ods_data)

            logger.info(f"Uploading ODS report file for {ods_code} to S3")
            file_key = f"daily_statistical_report_bulk_upload_summary_{generated_at}_uploaded_by_{ods_code}.csv"
            self.upload_ods_report(file_key, ods_report)

            ods_reports.append(ods_report)

        return ods_reports

    def generate_individual_ods_report(
        self, ods_code: str, ods_report_data: dict
    ) -> OdsReport:
        total_successful = set()
        total_registered_elsewhere = set()
        total_suspended = set()
        failure_reasons = {}

        for item in ods_report_data:
            nhs_number = item.get(MetadataReport.NhsNumber)
            upload_status = item.get(MetadataReport.UploadStatus)
            pds_ods_code = item.get(MetadataReport.PdsOdsCode)
            uploader_ods_code = item.get(MetadataReport.UploaderOdsCode)

            if upload_status == "complete":
                total_successful.add(nhs_number)

                if uploader_ods_code != pds_ods_code:
                    total_registered_elsewhere.add(nhs_number)

            if upload_status == "suspended":
                total_suspended.add(nhs_number)

            if upload_status == "failed":
                failure_reason = item.get("FailureReason", "Unknown")
                if failure_reason not in failure_reasons:
                    failure_reasons[failure_reason] = 0
                failure_reasons[failure_reason] += 1

        ods_report = OdsReport(
            ods_code=ods_code,
            total_successful=len(total_successful),
            total_registered_elsewhere=len(total_registered_elsewhere),
            total_suspended=len(total_suspended),
            failure_reasons=failure_reasons,
        )

        return ods_report

    def generate_summary_report(self, ods_reports: list[OdsReport], generated_at: str):
        file_name = f"daily_statistical_report_bulk_upload_summary_{generated_at}.csv"
        file_key = f"daily-reports/{file_name}"

        total_successful = 0
        total_registered_elsewhere = 0
        total_suspended = 0
        ods_code_totals = {}
        extra_row_values = []

        for report in ods_reports:
            total_successful += report.total_successful
            total_registered_elsewhere += report.total_registered_elsewhere
            total_suspended += report.total_suspended
            ods_code_totals[report.ods_code] = report.total_successful

            for failure_reason, count in report.failure_reasons.items():
                extra_row_values.append(["FailureReason", failure_reason, count])

        if ods_code_totals:
            for ods_code, count in ods_code_totals.items():
                extra_row_values.append(["Success by ODS", ods_code, count])
        else:
            extra_row_values.append(["Success by ODS", "No ODS codes found", 0])

        self.write_items_to_csv(
            file_name=file_key,
            total_successful=total_successful,
            total_registered_elsewhere=total_registered_elsewhere,
            total_suspended=total_suspended,
            extra_rows=extra_row_values,
        )

        logger.info("Uploading daily report file to S3")
        self.s3_service.upload_file(
            s3_bucket_name=self.reports_bucket,
            file_key=file_key,
            file_name=f"/tmp/{file_name}",
        )

    def upload_ods_report(self, file_key: str, ods_report: OdsReport):
        extra_row_values = []
        for failure_reason, count in ods_report.failure_reasons.items():
            extra_row_values.append(["FailureReason", failure_reason, count])

        self.write_items_to_csv(
            file_name=file_key,
            total_successful=ods_report.total_successful,
            total_registered_elsewhere=ods_report.total_registered_elsewhere,
            total_suspended=ods_report.total_suspended,
            extra_rows=ods_report.failure_reasons,
        )

        self.s3_service.upload_file(
            s3_bucket_name=self.reports_bucket,
            file_key=file_key,
            file_name=f"/tmp/{file_key}",
        )

    def write_items_to_csv(
        self,
        file_name: str,
        total_successful: int,
        total_registered_elsewhere: int,
        total_suspended: int,
        extra_rows: [],
    ):
        with open(f"/tmp/{file_name}", "w") as output_file:
            writer = csv.writer(output_file)

            writer.writerow(["Type", "Description", "Count"])
            writer.writerow(["Total", "Total Successful", total_successful])
            writer.writerow(
                [
                    "Total",
                    "Successful - Registered Elsewhere",
                    total_registered_elsewhere,
                ]
            )
            writer.writerow(["Total", "Suspended", total_suspended])

            for row in extra_rows:
                writer.writerow(row)

    def group_by_uploader_ods_code(self, report_data):
        ods_reports = {}
        for item in report_data:
            ods_code = item.get(MetadataReport.UploaderOdsCode, "Unknown")
            if ods_code not in ods_reports:
                ods_reports[ods_code] = []
            ods_reports[ods_code].append(item)
        return ods_reports

    def get_dynamodb_report_items(
        self, start_timestamp: int, end_timestamp: int
    ) -> Optional[list]:
        logger.info("Starting Scan on DynamoDB table")
        bulk_upload_table_name = os.getenv("BULK_UPLOAD_DYNAMODB_NAME")
        filter_time = Attr("Timestamp").gt(start_timestamp) & Attr("Timestamp").lt(
            end_timestamp
        )
        db_response = self.db_service.scan_table(
            bulk_upload_table_name, filter_expression=filter_time
        )

        if "Items" not in db_response:
            return None
        items = db_response["Items"]
        while "LastEvaluatedKey" in db_response:
            db_response = self.db_service.scan_table(
                bulk_upload_table_name,
                exclusive_start_key=db_response["LastEvaluatedKey"],
                filter_expression=filter_time,
            )
            if db_response["Items"]:
                items.extend(db_response["Items"])
        return items

    @staticmethod
    def get_times_for_scan() -> tuple[datetime, datetime]:
        current_time = datetime.datetime.now()
        today_date = datetime.datetime.today()
        start_timestamp = today_date - datetime.timedelta(days=30)
        start_timestamp = datetime.datetime.combine(start_timestamp, datetime.time.min)
        end_timestamp = current_time
        return start_timestamp, end_timestamp

        # current_time = datetime.datetime.now()
        # end_report_time = datetime.time(7, 00, 00, 0)
        # today_date = datetime.datetime.today()
        # end_timestamp = datetime.datetime.combine(today_date, end_report_time)
        # if current_time < end_timestamp:
        #     end_timestamp -= datetime.timedelta(days=1)
        # start_timestamp = end_timestamp - datetime.timedelta(days=1)
        # return start_timestamp, end_timestamp
