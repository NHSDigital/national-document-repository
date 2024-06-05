import hashlib
import os
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal

import polars as pl
from enums.supported_document_types import SupportedDocumentTypes
from models.cloudwatch_logs_query import (
    CloudwatchLogsQueryParams,
    LloydGeorgeRecordsDeleted,
    LloydGeorgeRecordsDownloaded,
    LloydGeorgeRecordsStored,
    LloydGeorgeRecordsViewed,
    UniqueActiveUserIds,
)
from models.statistics import (
    ApplicationData,
    OrganisationData,
    RecordStoreData,
    StatisticData,
)
from services.base.dynamo_service import DynamoDBService
from services.base.s3_service import S3Service
from services.cloudwatch_logs_query_service import CloudwatchLogsQueryService
from utils.audit_logging_setup import LoggingService
from utils.common_query_filters import UploadCompleted
from utils.utilities import flatten, get_file_key_from_s3_url

logger = LoggingService(__name__)


class DataCollectionService:
    def __init__(self):
        self.workspace = os.environ["WORKSPACE"]
        self.output_table_name = os.environ["STATISTICS_TABLE"]

        self.logs_query_service = CloudwatchLogsQueryService()
        self.dynamodb_service = DynamoDBService()
        self.s3_service = S3Service()

        one_day = 60 * 60 * 24
        time_now = int(datetime.now().timestamp())

        self.collection_start_time = time_now - one_day
        self.collection_end_time = time_now
        self.today_date = datetime.today().strftime("%Y%m%d")

    def collect_all_data_and_write_to_dynamodb(self):
        all_statistic_data = self.collect_all_data()
        logger.info("Statistic data collected:")
        logger.info(all_statistic_data)

        self.write_to_local_dynamodb_table(all_statistic_data)

    def collect_all_data(self) -> list[StatisticData]:
        dynamodb_scan_result = self.scan_dynamodb_tables()
        s3_list_objects_result = self.get_all_s3_files_info()

        record_store_data = self.get_record_store_data(
            dynamodb_scan_result, s3_list_objects_result
        )
        organisation_data = self.get_organisation_data(dynamodb_scan_result)
        application_data = self.get_application_data()

        return record_store_data + organisation_data + application_data

    def write_to_local_dynamodb_table(self, all_statistic_data: list[StatisticData]):
        logger.info("Writing statistic data to dynamodb table")
        item_list = []
        for entry in all_statistic_data:
            item_list.append(entry.model_dump(by_alias=True))

        self.dynamodb_service.batch_writing(
            table_name=self.output_table_name, item_list=item_list
        )

        logger.info("Finish writing all data to dynamodb table")

    def scan_dynamodb_tables(self) -> list[dict]:
        all_results = []

        project_expression = "CurrentGpOds,NhsNumber,FileLocation,ContentType"
        filter_expression = UploadCompleted

        for doc_type in SupportedDocumentTypes.list():
            table_name = doc_type.get_dynamodb_table_name()
            result = self.dynamodb_service.scan_whole_table(
                table_name=table_name,
                project_expression=project_expression,
                filter_expression=filter_expression,
            )
            all_results.extend(result)

        return all_results

    def get_all_s3_files_info(self) -> list[dict]:
        all_results = []
        for doc_type in SupportedDocumentTypes.list():
            bucket_name = doc_type.get_s3_bucket_name()
            result = self.s3_service.list_all_objects(bucket_name)
            all_results += result

        return all_results

    def get_record_store_data(
        self,
        dynamodb_scan_result: list[dict],
        s3_list_objects_result: list[dict],
    ) -> list[RecordStoreData]:
        total_number_of_records = self.get_total_number_of_records(dynamodb_scan_result)

        total_and_average_file_sizes = (
            self.get_metrics_for_total_and_average_file_sizes(
                dynamodb_scan_result, s3_list_objects_result
            )
        )

        number_of_document_types = self.get_number_of_document_types(
            dynamodb_scan_result
        )

        joined_query_result = self.join_results_by_ods_code(
            [
                total_number_of_records,
                total_and_average_file_sizes,
                number_of_document_types,
            ]
        )

        record_store_data_for_all_ods_code = [
            RecordStoreData(
                date=self.today_date,
                **record_store_data_properties,
            )
            for record_store_data_properties in joined_query_result
        ]

        return record_store_data_for_all_ods_code

    def get_organisation_data(
        self, dynamodb_scan_result: list[dict]
    ) -> list[OrganisationData]:
        number_of_patients = self.get_number_of_patients(dynamodb_scan_result)
        average_records_per_patient = self.get_average_number_of_file_per_patient(
            dynamodb_scan_result
        )
        daily_count_viewed = self.get_cloud_watch_query_result(LloydGeorgeRecordsViewed)
        daily_count_downloaded = self.get_cloud_watch_query_result(
            LloydGeorgeRecordsDownloaded
        )
        daily_count_deleted = self.get_cloud_watch_query_result(
            LloydGeorgeRecordsDeleted
        )
        daily_count_stored = self.get_cloud_watch_query_result(LloydGeorgeRecordsStored)

        joined_query_result = self.join_results_by_ods_code(
            [
                number_of_patients,
                average_records_per_patient,
                daily_count_viewed,
                daily_count_downloaded,
                daily_count_deleted,
                daily_count_stored,
            ]
        )

        organisation_data_for_all_ods_code = [
            OrganisationData(date=self.today_date, **organisation_data_properties)
            for organisation_data_properties in joined_query_result
        ]

        return organisation_data_for_all_ods_code

    def get_application_data(self) -> list[ApplicationData]:
        user_id_per_ods_code = self.get_active_user_list()
        application_data_for_all_ods_code = [
            ApplicationData(
                date=self.today_date,
                active_user_ids_hashed=active_user_ids_hashed,
                ods_code=ods_code,
            )
            for ods_code, active_user_ids_hashed in user_id_per_ods_code.items()
        ]
        return application_data_for_all_ods_code

    def get_active_user_list(self) -> dict[str, list]:
        query_result = self.get_cloud_watch_query_result(
            query_params=UniqueActiveUserIds
        )
        user_ids_per_ods_code = defaultdict(list)
        for entry in query_result:
            ods_code = entry.get("ods_code")
            user_id = entry.get("user_id")
            hashed_user_id = hashlib.md5(bytes(user_id, "utf8")).hexdigest()
            user_ids_per_ods_code[ods_code].append(hashed_user_id)

        return user_ids_per_ods_code

    def get_cloud_watch_query_result(
        self, query_params: CloudwatchLogsQueryParams
    ) -> list[dict]:
        return self.logs_query_service.query_logs(
            query_params=query_params,
            start_time=self.collection_start_time,
            end_time=self.collection_end_time,
        )

    def get_total_number_of_records(
        self, dynamodb_scan_result: list[dict]
    ) -> list[dict]:
        ods_code_for_every_document = [
            item["CurrentGpOds"] for item in dynamodb_scan_result
        ]
        counted_by_ods_code = Counter(ods_code_for_every_document)
        count_result_in_list_of_dict = [
            {"ods_code": key, "total_number_of_records": value}
            for key, value in counted_by_ods_code.items()
        ]
        return count_result_in_list_of_dict

    def get_number_of_patients(self, dynamodb_scan_result: list[dict]) -> list[dict]:
        patients_grouped_by_ods_code = defaultdict(set)
        for item in dynamodb_scan_result:
            ods_code = item["CurrentGpOds"]
            patients_grouped_by_ods_code[ods_code].add(item["NhsNumber"])

        return [
            {"ods_code": ods_code, "number_of_patients": len(patients)}
            for ods_code, patients in patients_grouped_by_ods_code.items()
        ]

    def get_metrics_for_total_and_average_file_sizes(
        self,
        dynamodb_scan_result: list[dict],
        s3_list_objects_result: list[dict],
    ) -> list[dict]:
        dynamodb_df = pl.DataFrame(dynamodb_scan_result)
        s3_df = pl.DataFrame(s3_list_objects_result)

        dynamodb_df_with_file_key = dynamodb_df.with_columns(
            pl.col("FileLocation")
            .map_elements(get_file_key_from_s3_url, return_dtype=pl.String)
            .alias("FileKey")
        )

        joined_df = dynamodb_df_with_file_key.join(
            s3_df, how="left", left_on="FileKey", right_on="Key", coalesce=True
        )
        get_total_size = (pl.col("Size").sum() / 1024 / 1024).alias(
            "TotalFileSizeForPatientInMegabytes"
        )
        df_with_total_file_size_per_patient = joined_df.group_by(
            "CurrentGpOds", "NhsNumber"
        ).agg(get_total_size)

        get_average_file_size_per_patient = (
            pl.col("TotalFileSizeForPatientInMegabytes")
            .mean()
            .alias("average_size_of_documents_per_patient_in_megabytes")
        )

        get_total_file_size_for_ods_code = (
            pl.col("TotalFileSizeForPatientInMegabytes")
            .sum()
            .alias("total_size_of_records_in_megabytes")
        )

        result = (
            df_with_total_file_size_per_patient.group_by("CurrentGpOds")
            .agg(get_average_file_size_per_patient, get_total_file_size_for_ods_code)
            .rename({"CurrentGpOds": "ods_code"})
            .sort("ods_code")
        )

        return result.to_dicts()

    def get_number_of_document_types(
        self, dynamodb_scan_result: list[dict]
    ) -> list[dict]:
        file_types_grouped_by_ods_code = defaultdict(set)
        for item in dynamodb_scan_result:
            ods_code = item["CurrentGpOds"]
            file_type = item["ContentType"]
            file_types_grouped_by_ods_code[ods_code].add(file_type)

        return [
            {"ods_code": ods_code, "number_of_document_types": len(file_types)}
            for ods_code, file_types in file_types_grouped_by_ods_code.items()
        ]

    def get_average_number_of_file_per_patient(
        self,
        dynamodb_scan_result: list[dict],
    ) -> list[dict]:
        # we should consider to use pandas / polars for this kind of aggregation
        ods_code_and_patient_number_tuple_for_every_document = [
            (item["CurrentGpOds"], item["NhsNumber"]) for item in dynamodb_scan_result
        ]
        counter_dict = Counter(ods_code_and_patient_number_tuple_for_every_document)
        counter_dict_by_ods_code = defaultdict(list)

        for (
            ods_code,
            _nhs_number,
        ), number_of_file_of_single_patient in counter_dict.items():
            counter_dict_by_ods_code[ods_code].append(number_of_file_of_single_patient)

        average_by_ods_code = [
            {
                "ods_code": ods_code,
                "average_records_per_patient": self.take_average(
                    list_of_number_of_files_of_each_patient
                ),
            }
            for ods_code, list_of_number_of_files_of_each_patient in counter_dict_by_ods_code.items()
        ]
        return average_by_ods_code

    @staticmethod
    def join_results_by_ods_code(results: list[list[dict]]) -> list[dict]:
        joined_by_ods_code = defaultdict(dict)
        for entry in flatten(results):
            ods_code = entry["ods_code"]
            joined_by_ods_code[ods_code].update(entry)

        joined_result = list(joined_by_ods_code.values())

        return joined_result

    @staticmethod
    def take_average(list_of_number: list[int]) -> Decimal:
        if list_of_number:
            return sum(list_of_number) / Decimal(len(list_of_number))
        return Decimal(0)
