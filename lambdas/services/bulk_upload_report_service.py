import csv
import datetime
import os

from boto3.dynamodb.conditions import Attr
from enums.metadata_report import MetadataReport
from models.report.bulk_upload_report import BulkUploadReport
from models.report.bulk_upload_report_output import OdsReport, SummaryReport
from pydantic import ValidationError
from services.base.dynamo_service import DynamoDBService
from services.base.s3_service import S3Service
from utils.audit_logging_setup import LoggingService
from utils.utilities import generate_date_folder_name

logger = LoggingService(__name__)


class BulkUploadReportService:
    def __init__(self):
        self.db_service = DynamoDBService()
        self.s3_service = S3Service()
        self.reports_bucket = os.getenv("STATISTICAL_REPORTS_BUCKET")
        self.generated_on = ""
        self.s3_key_prefix = ""

    def report_handler(self):
        start_time, end_time = self.get_times_for_scan()
        report_data = self.get_dynamodb_report_items(
            int(start_time.timestamp()), int(end_time.timestamp())
        )

        if report_data:
            logger.info(
                f"Bulk upload reports for {str(start_time)} to {str(end_time)}.csv"
            )

            ods_reports: list[OdsReport] = self.generate_ods_reports(report_data)
            logger.info("Successfully processed daily ODS reports")
            self.generate_summary_report(ods_reports)
            logger.info("Successfully processed daily summary report")
            self.generate_daily_report(report_data, start_time, end_time)
            logger.info("Successfully processed daily report")
            self.generate_success_report(ods_reports)
            logger.info("Successfully processed success report")
            self.generate_suspended_report(ods_reports)
            logger.info("Successfully processed suspended report")
            self.generate_deceased_report(ods_reports)
            logger.info("Successfully processed deceased report")
            self.generate_restricted_report(ods_reports)
            logger.info("Successfully processed restricted report")
            self.generate_rejected_report(ods_reports)
            logger.info("Successfully processed rejected report")
        else:
            logger.info("No data found, no new report file to upload")

    def generate_ods_reports(
        self, report_data: list[BulkUploadReport]
    ) -> list[OdsReport]:
        ods_reports: list[OdsReport] = []

        grouped_ods_data = {}
        for item in report_data:
            uploader_ods_code = item.uploader_ods_code

            if uploader_ods_code is not None and item is not None:
                grouped_ods_data.setdefault(uploader_ods_code, []).append(item)

        for uploader_ods_code, ods_report_items in grouped_ods_data.items():
            ods_report = self.generate_individual_ods_report(
                uploader_ods_code, ods_report_items
            )
            ods_reports.append(ods_report)

        return ods_reports

    def generate_individual_ods_report(
        self, uploader_ods_code: str, ods_report_items: list[BulkUploadReport]
    ) -> OdsReport:
        ods_report = OdsReport(
            generated_at=self.generated_on,
            report_items=ods_report_items,
            uploader_ods_code=uploader_ods_code,
        )

        file_name = f"daily_statistical_report_bulk_upload_ods_summary_{self.generated_on}_uploaded_by_{uploader_ods_code}.csv"

        self.write_summary_data_to_csv(
            file_name=file_name,
            total_ingested=ods_report.get_total_ingested_count(),
            total_successful=ods_report.get_total_successful(),
            total_successful_percentage=ods_report.get_total_successful_percentage(),
            total_registered_elsewhere=ods_report.get_total_registered_elsewhere_count(),
            total_suspended=ods_report.get_total_suspended_count(),
            total_deceased=ods_report.get_total_deceased_count(),
            extra_rows=ods_report.get_unsuccessful_reasons_data_rows(),
        )

        logger.info(f"Uploading ODS report file for {uploader_ods_code} to S3")
        self.s3_service.upload_file(
            s3_bucket_name=self.reports_bucket,
            file_key=f"{self.s3_key_prefix}/{file_name}",
            file_name=f"/tmp/{file_name}",
        )

        return ods_report

    def generate_summary_report(self, ods_reports: list[OdsReport]):
        summary_report = SummaryReport(
            generated_at=self.generated_on, ods_reports=ods_reports
        )

        file_name = (
            f"daily_statistical_report_bulk_upload_summary_{self.generated_on}.csv"
        )

        self.write_summary_data_to_csv(
            file_name=file_name,
            total_ingested=summary_report.get_total_ingested_count(),
            total_successful=summary_report.get_total_successful(),
            total_successful_percentage=summary_report.get_total_successful_percentage(),
            total_registered_elsewhere=summary_report.get_total_registered_elsewhere_count(),
            total_suspended=summary_report.get_total_suspended_count(),
            total_deceased=summary_report.get_total_deceased_count(),
            total_restricted=summary_report.get_total_restricted_count(),
            extra_rows=summary_report.success_summary + summary_report.reason_summary,
        )

        logger.info("Uploading daily summary report file to S3")
        self.s3_service.upload_file(
            s3_bucket_name=self.reports_bucket,
            file_key=f"{self.s3_key_prefix}/{file_name}",
            file_name=f"/tmp/{file_name}",
        )

    def generate_daily_report(
        self, report_data: list[BulkUploadReport], start_time: str, end_time: str
    ):
        file_name = f"daily_statistical_report_entire_bulk_upload_{str(start_time)}_to_{str(end_time)}.csv"

        self.write_items_to_csv(report_data, f"/tmp/{file_name}")

        logger.info("Uploading daily report file to S3")
        self.s3_service.upload_file(
            s3_bucket_name=self.reports_bucket,
            file_key=f"{self.s3_key_prefix}/{file_name}",
            file_name=f"/tmp/{file_name}",
        )

    def generate_success_report(self, ods_reports: list[OdsReport]):
        file_name = (
            f"daily_statistical_report_bulk_upload_success_{self.generated_on}.csv"
        )

        headers = [
            MetadataReport.NhsNumber,
            MetadataReport.UploaderOdsCode,
            MetadataReport.Date,
            MetadataReport.RegisteredAtUploaderPractice,
        ]
        data_rows = []
        for report in ods_reports:
            for patient in report.get_sorted(report.total_successful):
                data_rows.append(
                    [
                        str(patient[0]),
                        str(report.uploader_ods_code),
                        str(patient[1]),
                        str(patient[2]),
                    ]
                )

        if data_rows:
            logger.info("Uploading daily success report file to S3")
            self.write_and_upload_additional_reports(file_name, headers, data_rows)
        else:
            logger.info("No data to report for daily success report file")

    def generate_suspended_report(self, ods_reports: list[OdsReport]):
        file_name = (
            f"daily_statistical_report_bulk_upload_suspended_{self.generated_on}.csv"
        )

        headers = [
            MetadataReport.NhsNumber,
            MetadataReport.UploaderOdsCode,
            MetadataReport.Date,
        ]
        data_rows = []
        for report in ods_reports:
            for patient in report.get_sorted(report.total_suspended):
                data_rows.append(
                    [str(patient[0]), str(report.uploader_ods_code), str(patient[1])]
                )

        if data_rows:
            logger.info("Uploading daily suspended report file to S3")
            self.write_and_upload_additional_reports(file_name, headers, data_rows)
        else:
            logger.info("No data to report for daily suspended report file")

    def generate_deceased_report(self, ods_reports: list[OdsReport]):
        file_name = (
            f"daily_statistical_report_bulk_upload_deceased_{self.generated_on}.csv"
        )

        headers = [
            MetadataReport.NhsNumber,
            MetadataReport.UploaderOdsCode,
            MetadataReport.Date,
            MetadataReport.Reason,
        ]
        data_rows = []
        for report in ods_reports:
            for patient in report.get_sorted(report.total_deceased):
                data_rows.append(
                    [
                        str(patient[0]),
                        str(report.uploader_ods_code),
                        str(patient[1]),
                        str(patient[2]),
                    ]
                )

        if data_rows:
            logger.info("Uploading daily deceased report file to S3")
            self.write_and_upload_additional_reports(file_name, headers, data_rows)
        else:
            logger.info("No data to report for daily deceased report file")

    def generate_restricted_report(self, ods_reports: list[OdsReport]):
        file_name = (
            f"daily_statistical_report_bulk_upload_restricted_{self.generated_on}.csv"
        )

        headers = [
            MetadataReport.NhsNumber,
            MetadataReport.UploaderOdsCode,
            MetadataReport.Date,
        ]
        data_rows = []
        for report in ods_reports:
            for patient in report.get_sorted(report.total_restricted):
                data_rows.append(
                    [str(patient[0]), str(report.uploader_ods_code), str(patient[1])]
                )

        if data_rows:
            logger.info("Uploading daily restricted report file to S3")
            self.write_and_upload_additional_reports(file_name, headers, data_rows)
        else:
            logger.info("No data to report for daily restricted report file")

    def generate_rejected_report(self, ods_reports: list[OdsReport]):
        file_name = (
            f"daily_statistical_report_bulk_upload_rejected_{self.generated_on}.csv"
        )

        headers = [
            MetadataReport.NhsNumber,
            MetadataReport.UploaderOdsCode,
            MetadataReport.Date,
            MetadataReport.Reason,
            MetadataReport.RegisteredAtUploaderPractice,
        ]

        data_rows = []
        for report in ods_reports:
            for nhs_number, report_item in report.failures_per_patient.items():
                data_rows.append(
                    [
                        nhs_number,
                        report_item[MetadataReport.UploaderOdsCode],
                        report_item[MetadataReport.Date],
                        report_item[MetadataReport.Reason],
                        report_item[MetadataReport.RegisteredAtUploaderPractice],
                    ]
                )

        if data_rows:
            logger.info("Uploading daily rejected report file to S3")
            self.write_and_upload_additional_reports(file_name, headers, data_rows)
        else:
            logger.info("No data to report for daily rejected report file")

    @staticmethod
    def write_items_to_csv(items: list[BulkUploadReport], csv_file_path: str):
        logger.info("Writing scan results to csv file")
        with open(csv_file_path, "w") as output_file:
            field_names = [
                MetadataReport.NhsNumber,
                MetadataReport.UploadStatus,
                MetadataReport.Reason,
                MetadataReport.PdsOdsCode,
                MetadataReport.UploaderOdsCode,
                MetadataReport.FilePath,
                MetadataReport.Date,
                MetadataReport.Timestamp,
            ]
            dict_writer_object = csv.DictWriter(output_file, fieldnames=field_names)
            dict_writer_object.writeheader()
            for item in items:
                dict_writer_object.writerow(
                    item.model_dump(
                        exclude={str(MetadataReport.ID).lower(), "stored_file_name"},
                        by_alias=True,
                    )
                )

    @staticmethod
    def write_summary_data_to_csv(
        file_name: str,
        total_ingested: int,
        total_successful: int,
        total_successful_percentage: str,
        total_registered_elsewhere: int,
        total_suspended: int,
        total_deceased: int = None,
        total_restricted: int = None,
        extra_rows: list = [],
    ):
        with open(f"/tmp/{file_name}", "w", newline="") as output_file:
            writer = csv.writer(output_file)

            writer.writerow(["Type", "Description", "Count"])
            writer.writerow(["Total", "Total Ingested", total_ingested])
            writer.writerow(["Total", "Total Successful", total_successful])
            writer.writerow(
                ["Total", "Successful Percentage", total_successful_percentage]
            )
            writer.writerow(
                [
                    "Total",
                    "Successful - Registered Elsewhere",
                    total_registered_elsewhere,
                ]
            )
            writer.writerow(["Total", "Successful - Suspended", total_suspended])

            if total_deceased:
                writer.writerow(["Total", "Successful - Deceased", total_deceased])

            if total_restricted:
                writer.writerow(["Total", "Successful - Restricted", total_restricted])

            for row in extra_rows:
                writer.writerow(row)

    @staticmethod
    def write_additional_report_items_to_csv(
        file_name: str,
        headers: list[str] = [],
        rows_to_write: list[list[str]] = [],
    ):
        with open(f"/tmp/{file_name}", "w", newline="") as output_file:
            writer = csv.writer(output_file)
            writer.writerow(headers)
            for row in rows_to_write:
                writer.writerow(row)

    def get_dynamodb_report_items(
        self, start_timestamp: int, end_timestamp: int
    ) -> list[BulkUploadReport]:
        logger.info("Starting Scan on DynamoDB table")
        bulk_upload_table_name = os.getenv("BULK_UPLOAD_DYNAMODB_NAME")
        filter_time = Attr("Timestamp").gt(start_timestamp) & Attr("Timestamp").lt(
            end_timestamp
        )
        db_response = self.db_service.scan_table(
            bulk_upload_table_name, filter_expression=filter_time
        )

        if "Items" not in db_response:
            return []
        items = db_response["Items"]
        while "LastEvaluatedKey" in db_response:
            db_response = self.db_service.scan_table(
                bulk_upload_table_name,
                exclusive_start_key=db_response["LastEvaluatedKey"],
                filter_expression=filter_time,
            )
            if db_response["Items"]:
                items.extend(db_response["Items"])

        validated_items = []
        for item in items:
            try:
                validated_items.append(BulkUploadReport.model_validate(item))
            except ValidationError as e:
                logger.error(f"Failed to parse bulk update report dynamo item: {e}")

        return validated_items

    def get_times_for_scan(self) -> tuple[datetime, datetime]:
        current_time = datetime.datetime.now()
        end_report_time = datetime.time(7, 00, 00, 0)
        today_date = datetime.datetime.today()
        end_timestamp = datetime.datetime.combine(today_date, end_report_time)
        if current_time < end_timestamp:
            end_timestamp -= datetime.timedelta(days=1)
        start_timestamp = end_timestamp - datetime.timedelta(days=1)

        self.generated_on = start_timestamp.strftime("%Y%m%d")
        date_folder_name = generate_date_folder_name(self.generated_on)
        self.s3_key_prefix = f"bulk-upload-reports/{date_folder_name}"

        return start_timestamp, end_timestamp

    def write_and_upload_additional_reports(
        self,
        file_name: str,
        headers: list[str],
        data_rows: list[list[str]],
    ):
        self.write_additional_report_items_to_csv(
            file_name=file_name, headers=headers, rows_to_write=data_rows
        )

        self.s3_service.upload_file(
            s3_bucket_name=self.reports_bucket,
            file_key=f"{self.s3_key_prefix}/{file_name}",
            file_name=f"/tmp/{file_name}",
        )
