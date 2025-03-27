from datetime import datetime, timedelta
from decimal import Decimal
from random import shuffle
from unittest.mock import call

import pytest
from freezegun import freeze_time
from pytest_unordered import unordered
from services.base.cloudwatch_service import CloudwatchService
from services.base.dynamo_service import DynamoDBService
from services.base.s3_service import S3Service
from services.data_collection_service import DataCollectionService
from tests.unit.conftest import (
    MOCK_ARF_BUCKET,
    MOCK_ARF_TABLE_NAME,
    MOCK_LG_BUCKET,
    MOCK_LG_TABLE_NAME,
    MOCK_STATISTICS_TABLE,
)
from tests.unit.helpers.data.statistic.mock_collected_data import (
    ALL_MOCK_DATA_AS_JSON_LIST,
    ALL_MOCK_WEEKLY_DATA,
    END_DATE,
    MOCK_APPLICATION_DATA,
    MOCK_ORGANISATION_DATA,
    MOCK_RECORD_STORE_DATA,
    START_DATE,
    START_DATE_STR,
)
from tests.unit.helpers.data.statistic.mock_dynamodb_and_s3_records import (
    MOCK_ARF_LIST_OBJECTS_RESULT,
    MOCK_ARF_SCAN_RESULT,
    MOCK_LG_LIST_OBJECTS_RESULT,
    MOCK_LG_SCAN_RESULT,
    TOTAL_FILE_SIZE_FOR_H81109,
    TOTAL_FILE_SIZE_FOR_Y12345,
    build_mock_results,
)
from tests.unit.helpers.data.statistic.mock_logs_query_results import (
    HASHED_USER_ID_1_WITH_ADMIN_ROLE,
    HASHED_USER_ID_1_WITH_PCSE_ROLE,
    HASHED_USER_ID_2_WITH_CLINICAL_ROLE,
    MOCK_DECEASED_ACCESS,
    MOCK_LG_DELETED,
    MOCK_LG_DOWNLOADED,
    MOCK_LG_STORED,
    MOCK_LG_VIEWED,
    MOCK_ODS_REPORT_CREATED,
    MOCK_ODS_REPORT_REQUESTED,
    MOCK_PATIENT_SEARCHED,
    MOCK_UNIQUE_ACTIVE_USER_IDS,
)
from utils.cloudwatch_logs_query import (
    CloudwatchLogsQueryParams,
    CountUsersAccessedDeceasedPatient,
    LloydGeorgeRecordsDeleted,
    LloydGeorgeRecordsDownloaded,
    LloydGeorgeRecordsSearched,
    LloydGeorgeRecordsStored,
    LloydGeorgeRecordsViewed,
    OdsReportsCreated,
    OdsReportsRequested,
    UniqueActiveUserIds,
)
from utils.common_query_filters import UploadCompleted


@pytest.fixture
def mock_dynamo_service(mocker):
    def mock_implementation(table_name, **_kwargs):
        if table_name == MOCK_LG_TABLE_NAME:
            return MOCK_LG_SCAN_RESULT
        elif table_name == MOCK_ARF_TABLE_NAME:
            return MOCK_ARF_SCAN_RESULT

    patched_instance = mocker.patch(
        "services.data_collection_service.DynamoDBService", spec=DynamoDBService
    ).return_value
    patched_method = patched_instance.scan_whole_table
    patched_method.side_effect = mock_implementation

    yield patched_instance


@pytest.fixture
def mock_s3_list_all_objects(mocker):
    def mock_implementation(bucket_name, **_kwargs):
        if bucket_name == MOCK_LG_BUCKET:
            return MOCK_LG_LIST_OBJECTS_RESULT
        elif bucket_name == MOCK_ARF_BUCKET:
            return MOCK_ARF_LIST_OBJECTS_RESULT

    patched_instance = mocker.patch(
        "services.data_collection_service.S3Service", spec=S3Service
    ).return_value
    patched_method = patched_instance.list_all_objects
    patched_method.side_effect = mock_implementation

    yield patched_method


@pytest.fixture
def mock_query_logs(mocker):
    def mock_implementation(query_params: CloudwatchLogsQueryParams, **_kwargs):
        if query_params == LloydGeorgeRecordsViewed:
            return MOCK_LG_VIEWED
        elif query_params == LloydGeorgeRecordsDownloaded:
            return MOCK_LG_DOWNLOADED
        elif query_params == LloydGeorgeRecordsDeleted:
            return MOCK_LG_DELETED
        elif query_params == LloydGeorgeRecordsStored:
            return MOCK_LG_STORED
        elif query_params == UniqueActiveUserIds:
            return MOCK_UNIQUE_ACTIVE_USER_IDS
        elif query_params == LloydGeorgeRecordsSearched:
            return MOCK_PATIENT_SEARCHED
        elif query_params == CountUsersAccessedDeceasedPatient:
            return MOCK_DECEASED_ACCESS
        elif query_params == OdsReportsRequested:
            return MOCK_ODS_REPORT_REQUESTED
        elif query_params == OdsReportsCreated:
            return MOCK_ODS_REPORT_CREATED

    patched_instance = mocker.patch(
        "services.data_collection_service.CloudwatchService",
        spec=CloudwatchService,
    ).return_value
    mocked_method = patched_instance.query_logs
    mocked_method.side_effect = mock_implementation

    yield mocked_method


@pytest.fixture
def mock_service(
    set_env, mock_query_logs, mock_dynamo_service, mock_s3_list_all_objects
):
    service = DataCollectionService()
    yield service


@pytest.fixture()
def mock_generate_daily_ranges(mocker, mock_service):
    service = mock_service
    mock_generate_ranges = mocker.patch.object(service, "generate_daily_ranges")
    mock_generate_ranges.return_value = [
        START_DATE,
        START_DATE + timedelta(days=1),
        START_DATE + timedelta(days=2),
        START_DATE + timedelta(days=3),
        START_DATE + timedelta(days=4),
        START_DATE + timedelta(days=5),
        START_DATE + timedelta(days=6),
    ]
    yield mock_generate_daily_ranges


@pytest.fixture
def larger_mock_data():
    dynamodb_1, s3_1 = build_mock_results("H81109", "9000000001", 135, 123)
    dynamodb_2, s3_2 = build_mock_results("H81109", "9000000002", 246, 456)
    dynamodb_3, s3_3 = build_mock_results("H81109", "9000000003", 369, 789)
    dynamodb_4, s3_4 = build_mock_results("Y12345", "9000000004", 4812, 9876)
    dynamodb_5, s3_5 = build_mock_results("Y12345", "9000000005", 5101, 5432)

    mock_dynamo_scan_result = (
        dynamodb_1 + dynamodb_2 + dynamodb_3 + dynamodb_4 + dynamodb_5
    )
    mock_s3_list_objects_result = s3_1 + s3_2 + s3_3 + s3_4 + s3_5
    shuffle(mock_dynamo_scan_result)
    shuffle(mock_s3_list_objects_result)

    return mock_dynamo_scan_result, mock_s3_list_objects_result


@freeze_time("2024-06-04T00:00:00Z")
def test_datetime_correctly_configured_during_initialise(set_env):
    service = DataCollectionService()

    assert service.today_date == "20240604"
    assert (
        service.weekly_collection_start_date
        == datetime.fromisoformat("2024-05-28T00:00:00Z").timestamp()
    )
    assert (
        service.weekly_collection_end_date
        == datetime.fromisoformat("2024-06-04T00:00:00Z").timestamp()
    )


def test_collect_all_data_and_write_to_dynamodb(mock_service, mocker):
    mock_collected_data = ["testing1234"]
    mock_service.collect_all_data = mocker.MagicMock(return_value=mock_collected_data)
    mock_service.write_to_dynamodb_table = mocker.MagicMock()

    mock_service.collect_all_data_and_write_to_dynamodb()

    mock_service.collect_all_data.assert_called_once()
    mock_service.write_to_dynamodb_table.assert_called_with(mock_collected_data)


def test_collect_all_data(mock_uuid, mock_service, mock_generate_daily_ranges):
    mock_service.today_date = START_DATE_STR

    expected = unordered(ALL_MOCK_WEEKLY_DATA)

    actual = mock_service.collect_all_data()

    assert actual == expected


def test_write_to_dynamodb_table(mock_dynamo_service, mock_service):
    mock_data = MOCK_RECORD_STORE_DATA + MOCK_ORGANISATION_DATA + MOCK_APPLICATION_DATA
    mock_service.write_to_dynamodb_table(mock_data)

    mock_dynamo_service.batch_writing.assert_called_with(
        table_name=MOCK_STATISTICS_TABLE, item_list=ALL_MOCK_DATA_AS_JSON_LIST
    )


def test_scan_dynamodb_tables(mock_dynamo_service, mock_service):
    mock_service.scan_dynamodb_tables()

    expected_project_expression = "CurrentGpOds,NhsNumber,FileLocation,ContentType"
    expected_filter_expression = UploadCompleted

    expected_calls = [
        call(
            table_name=MOCK_ARF_TABLE_NAME,
            project_expression=expected_project_expression,
            filter_expression=expected_filter_expression,
        ),
        call(
            table_name=MOCK_LG_TABLE_NAME,
            project_expression=expected_project_expression,
            filter_expression=expected_filter_expression,
        ),
    ]
    mock_dynamo_service.scan_whole_table.assert_has_calls(expected_calls)


def test_get_all_s3_files_info(mock_s3_list_all_objects, mock_service):
    mock_service.get_all_s3_files_info()

    expected_calls = [
        call(MOCK_ARF_BUCKET),
        call(MOCK_LG_BUCKET),
    ]

    mock_s3_list_all_objects.assert_has_calls(expected_calls)


def test_get_record_store_data(mock_uuid, mock_service):
    mock_service.today_date = START_DATE_STR

    mock_dynamo_scan_result = MOCK_ARF_SCAN_RESULT + MOCK_LG_SCAN_RESULT
    s3_list_objects_result = MOCK_ARF_LIST_OBJECTS_RESULT + MOCK_LG_LIST_OBJECTS_RESULT

    actual = mock_service.get_record_store_data(
        mock_dynamo_scan_result, s3_list_objects_result
    )
    expected = unordered(MOCK_RECORD_STORE_DATA)

    assert actual == expected


def test_get_organisation_data(mock_uuid, mock_service):
    mock_dynamo_scan_result = MOCK_ARF_SCAN_RESULT + MOCK_LG_SCAN_RESULT

    actual = mock_service.get_organisation_data(
        mock_dynamo_scan_result, start_date=START_DATE, end_date=END_DATE
    )
    expected = unordered(MOCK_ORGANISATION_DATA)

    assert actual == expected


def test_get_application_data(mock_uuid, mock_service):
    actual = mock_service.get_application_data(start_date=START_DATE, end_date=END_DATE)
    expected = unordered(MOCK_APPLICATION_DATA)

    assert actual == expected


def test_get_active_user_list(set_env, mock_query_logs):
    mock_query_logs.return_value = MOCK_UNIQUE_ACTIVE_USER_IDS
    service = DataCollectionService()
    expected = {
        "H81109": [
            HASHED_USER_ID_1_WITH_ADMIN_ROLE,
            HASHED_USER_ID_2_WITH_CLINICAL_ROLE,
        ],
        "Y12345": [HASHED_USER_ID_1_WITH_PCSE_ROLE],
    }
    actual = service.get_active_user_list(start_date=START_DATE, end_date=END_DATE)

    assert actual == expected


def test_get_cloud_watch_query_result(set_env, mock_query_logs):
    mock_query_param = CloudwatchLogsQueryParams("mock", "test")
    service = DataCollectionService()

    service.get_cloud_watch_query_result(mock_query_param, START_DATE, END_DATE)

    mock_query_logs.assert_called_with(
        query_params=mock_query_param,
        start_time=int(START_DATE.timestamp()),
        end_time=int(END_DATE.timestamp()),
    )


def test_get_total_number_of_records(mock_service):
    actual = mock_service.get_total_number_of_records(
        MOCK_ARF_SCAN_RESULT + MOCK_LG_SCAN_RESULT
    )
    expected = [
        {"ods_code": "Y12345", "total_number_of_records": 2},
        {"ods_code": "H81109", "total_number_of_records": 6},
    ]

    assert actual == expected


def test_get_total_number_of_records_larger_mock_data(mock_service, larger_mock_data):
    mock_dynamo_scan_result, _ = larger_mock_data

    actual = mock_service.get_total_number_of_records(mock_dynamo_scan_result)
    expected = unordered(
        [
            {"ods_code": "H81109", "total_number_of_records": 135 + 246 + 369},
            {"ods_code": "Y12345", "total_number_of_records": 4812 + 5101},
        ]
    )

    assert actual == expected


def test_get_number_of_patients(mock_service):
    actual = mock_service.get_number_of_patients(
        MOCK_ARF_SCAN_RESULT + MOCK_LG_SCAN_RESULT
    )
    expected = unordered(
        [
            {"ods_code": "Y12345", "number_of_patients": 1},
            {"ods_code": "H81109", "number_of_patients": 2},
        ]
    )

    assert actual == expected


def test_get_metrics_for_total_and_average_file_sizes(mock_service):
    mock_dynamo_scan_result = MOCK_ARF_SCAN_RESULT + MOCK_LG_SCAN_RESULT
    mock_s3_list_objects_result = (
        MOCK_ARF_LIST_OBJECTS_RESULT + MOCK_LG_LIST_OBJECTS_RESULT
    )

    actual = mock_service.get_metrics_for_total_and_average_file_sizes(
        mock_dynamo_scan_result, mock_s3_list_objects_result
    )

    expected = unordered(
        [
            {
                "ods_code": "H81109",
                "average_size_of_documents_per_patient_in_megabytes": TOTAL_FILE_SIZE_FOR_H81109
                / 2,
                "total_size_of_records_in_megabytes": TOTAL_FILE_SIZE_FOR_H81109,
            },
            {
                "ods_code": "Y12345",
                "average_size_of_documents_per_patient_in_megabytes": TOTAL_FILE_SIZE_FOR_Y12345,
                "total_size_of_records_in_megabytes": TOTAL_FILE_SIZE_FOR_Y12345,
            },
        ]
    )

    assert actual == expected


def test_get_metrics_for_total_and_average_file_sizes_larger_mock_data(
    mock_service, larger_mock_data
):
    mock_dynamo_scan_result, mock_s3_list_objects_result = larger_mock_data
    actual = mock_service.get_metrics_for_total_and_average_file_sizes(
        mock_dynamo_scan_result, mock_s3_list_objects_result
    )

    expected = unordered(
        [
            {
                "ods_code": "H81109",
                "average_size_of_documents_per_patient_in_megabytes": (123 + 456 + 789)
                / 3,
                "total_size_of_records_in_megabytes": (123 + 456 + 789),
            },
            {
                "ods_code": "Y12345",
                "average_size_of_documents_per_patient_in_megabytes": (9876 + 5432) / 2,
                "total_size_of_records_in_megabytes": (9876 + 5432),
            },
        ]
    )

    assert actual == expected


def test_get_number_of_document_types(mock_service):
    actual = mock_service.get_number_of_document_types(MOCK_ARF_SCAN_RESULT)
    expected = unordered(
        [
            {"ods_code": "Y12345", "number_of_document_types": 2},
            {"ods_code": "H81109", "number_of_document_types": 1},
        ]
    )

    assert actual == expected

    actual = mock_service.get_number_of_document_types(
        MOCK_ARF_SCAN_RESULT + MOCK_LG_SCAN_RESULT
    )
    expected = unordered(
        [
            {"ods_code": "Y12345", "number_of_document_types": 2},
            {"ods_code": "H81109", "number_of_document_types": 2},
        ]
    )

    assert actual == expected


def test_get_average_number_of_file_per_patient(mock_service):
    actual = mock_service.get_average_number_of_files_per_patient(
        MOCK_ARF_SCAN_RESULT + MOCK_LG_SCAN_RESULT
    )
    expected = unordered(
        [
            {"ods_code": "Y12345", "average_records_per_patient": 2},
            {"ods_code": "H81109", "average_records_per_patient": 3},
        ]
    )

    assert actual == expected


def test_get_average_number_of_file_per_patient_larger_mock_data(
    mock_service, larger_mock_data
):
    mock_dynamo_scan_result, _ = larger_mock_data

    actual = mock_service.get_average_number_of_files_per_patient(
        mock_dynamo_scan_result
    )
    expected = unordered(
        [
            {
                "ods_code": "H81109",
                "average_records_per_patient": Decimal(135 + 246 + 369) / 3,
            },
            {
                "ods_code": "Y12345",
                "average_records_per_patient": Decimal(4812 + 5101) / 2,
            },
        ]
    )

    assert actual == expected


def test_generate_daily_ranges(mock_service):
    mock_service.start_date = START_DATE
    expected = [
        START_DATE,
        START_DATE + timedelta(days=1),
        START_DATE + timedelta(days=2),
        START_DATE + timedelta(days=3),
        START_DATE + timedelta(days=4),
        START_DATE + timedelta(days=5),
        START_DATE + timedelta(days=6),
    ]
    actual = mock_service.generate_daily_ranges()

    assert actual == expected
