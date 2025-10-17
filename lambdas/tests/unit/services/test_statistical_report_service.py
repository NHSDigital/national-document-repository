import tempfile
from random import shuffle
from unittest.mock import call

import polars as pl
import pytest
from freezegun import freeze_time
from models.report.statistics import ApplicationData
from polars.testing import assert_frame_equal
from services.base.dynamo_service import DynamoDBService
from services.base.s3_service import S3Service
from services.statistical_report_service import StatisticalReportService
from tests.unit.conftest import (
    MOCK_STATISTICS_REPORT_BUCKET_NAME,
    MOCK_STATISTICS_TABLE,
)
from tests.unit.helpers.data.statistic.mock_data_build_utils import (
    build_random_application_data,
    build_random_organisation_data,
    build_random_record_store_data,
)
from tests.unit.helpers.data.statistic.mock_statistic_data import (
    ALL_MOCKED_STATISTIC_DATA,
    EXPECTED_SUMMARY_APPLICATION_DATA,
    EXPECTED_SUMMARY_ORGANISATION_DATA,
    EXPECTED_SUMMARY_RECORD_STORE_DATA,
    EXPECTED_WEEKLY_SUMMARY,
    MOCK_APPLICATION_DATA_1,
    MOCK_APPLICATION_DATA_2,
    MOCK_APPLICATION_DATA_3,
    MOCK_DYNAMODB_QUERY_RESPONSE,
    MOCK_ORGANISATION_DATA_1,
    MOCK_ORGANISATION_DATA_2,
    MOCK_ORGANISATION_DATA_3,
    MOCK_RECORD_STORE_DATA_1,
    MOCK_RECORD_STORE_DATA_2,
    MOCK_RECORD_STORE_DATA_3,
)
from utils.exceptions import StatisticDataNotFoundException


@pytest.fixture
def mock_service(set_env, mock_s3_service, mock_dynamodb_service):
    return StatisticalReportService()


@pytest.fixture
def mock_s3_service(mocker):
    patched_instance = mocker.patch(
        "services.statistical_report_service.S3Service", spec=S3Service
    ).return_value

    yield patched_instance


@pytest.fixture
def mock_dynamodb_service(mocker):
    patched_instance = mocker.patch(
        "services.statistical_report_service.DynamoDBService", spec=DynamoDBService
    ).return_value

    yield patched_instance


@pytest.fixture
def mock_temp_folder(mocker):
    mocker.patch.object(pl.DataFrame, "write_csv")
    mocker.patch("shutil.rmtree")
    temp_folder = tempfile.mkdtemp()
    mocker.patch.object(tempfile, "mkdtemp", return_value=temp_folder)
    yield temp_folder


@freeze_time("2024-06-06T18:00:00Z")
def test_datetime_correctly_configured_during_initialise(set_env):
    service = StatisticalReportService()

    assert service.dates_to_collect == [
        "20240530",
        "20240531",
        "20240601",
        "20240602",
        "20240603",
        "20240604",
        "20240605",
    ]
    assert service.report_period == "20240530-20240605"


@freeze_time("20240512T07:00:00Z")
def test_make_weekly_summary(set_env, mocker):
    data = ALL_MOCKED_STATISTIC_DATA
    service = StatisticalReportService()
    service.get_statistic_data = mocker.MagicMock(return_value=data)

    actual = service.make_weekly_summary()
    expected = EXPECTED_WEEKLY_SUMMARY

    assert_frame_equal(
        actual, expected, check_row_order=False, check_dtypes=False, check_exact=False
    )


def test_get_statistic_data(mock_dynamodb_service, mock_service):
    mock_service.dates_to_collect = ["20240510", "20240511"]
    mock_dynamodb_service.query_table.side_effect = MOCK_DYNAMODB_QUERY_RESPONSE

    actual = mock_service.get_statistic_data()
    expected = ALL_MOCKED_STATISTIC_DATA

    assert actual == expected

    expected_calls = [
        call(
            table_name=MOCK_STATISTICS_TABLE,
            search_key="Date",
            search_condition="20240510",
        ),
        call(
            table_name=MOCK_STATISTICS_TABLE,
            search_key="Date",
            search_condition="20240511",
        ),
    ]

    mock_dynamodb_service.query_table.assert_has_calls(expected_calls)


def test_get_statistic_data_raise_error_if_all_data_are_empty(
    mock_dynamodb_service, mock_service
):
    mock_dynamodb_service.query_table.return_value = []

    with pytest.raises(StatisticDataNotFoundException):
        mock_service.get_statistic_data()


def test_summarise_record_store_data(mock_service):
    actual = mock_service.summarise_record_store_data(
        [MOCK_RECORD_STORE_DATA_1, MOCK_RECORD_STORE_DATA_2, MOCK_RECORD_STORE_DATA_3]
    )

    expected = EXPECTED_SUMMARY_RECORD_STORE_DATA

    assert_frame_equal(actual, expected, check_row_order=False, check_dtypes=False)


def test_summarise_record_store_data_larger_mock_data(mock_service):
    mock_data_h81109 = build_random_record_store_data(
        "H81109", ["20240601", "20240603", "20240604", "20240605", "20240607"]
    )
    mock_data_y12345 = build_random_record_store_data(
        "Y12345", ["20240601", "20240602", "20240603", "20240606"]
    )
    mock_record_store_data = mock_data_h81109 + mock_data_y12345
    shuffle(mock_record_store_data)

    latest_record_in_h81109 = max(mock_data_h81109, key=lambda record: record.date)
    latest_record_in_y12345 = max(mock_data_y12345, key=lambda record: record.date)
    expected = pl.DataFrame([latest_record_in_h81109, latest_record_in_y12345]).drop(
        "date", "statistic_id"
    )

    actual = mock_service.summarise_record_store_data(mock_record_store_data)

    assert_frame_equal(actual, expected, check_row_order=False, check_dtypes=False)


def test_summarise_record_store_data_can_handle_empty_input(mock_service):
    empty_input = []
    actual = mock_service.summarise_record_store_data(empty_input)

    assert isinstance(actual, pl.DataFrame)
    assert actual.is_empty()


def test_summarise_organisation_data(mock_service):
    actual = mock_service.summarise_organisation_data(
        [MOCK_ORGANISATION_DATA_1, MOCK_ORGANISATION_DATA_2, MOCK_ORGANISATION_DATA_3]
    )

    expected = EXPECTED_SUMMARY_ORGANISATION_DATA

    assert_frame_equal(actual, expected, check_row_order=False, check_dtypes=False)


def test_summarise_organisation_data_larger_mock_data(mock_service):
    mock_data_h81109 = build_random_organisation_data(
        "H81109", ["20240603", "20240604", "20240605", "20240606", "20240607"]
    )
    mock_data_y12345 = build_random_organisation_data(
        "Y12345", ["20240603", "20240604", "20240605", "20240606", "20240607"]
    )
    mock_input_data = {"H81109": mock_data_h81109, "Y12345": mock_data_y12345}

    mock_organisation_data = mock_data_h81109 + mock_data_y12345
    shuffle(mock_organisation_data)

    actual = mock_service.summarise_organisation_data(mock_organisation_data)

    for ods_code in mock_input_data.keys():
        mock_data_of_ods_code = mock_input_data[ods_code]
        row_in_actual_data = actual.filter(pl.col("ods_code") == ods_code)
        assert_weekly_counts_match_sum_of_daily_counts(
            mock_data_of_ods_code, row_in_actual_data
        )
        assert_average_record_per_patient_correct(
            mock_data_of_ods_code, row_in_actual_data
        )
        assert_number_of_patient_correct(mock_data_of_ods_code, row_in_actual_data)


def assert_weekly_counts_match_sum_of_daily_counts(mock_data, row_in_actual_data):
    for count_type in ["viewed", "downloaded", "stored", "deleted"]:
        expected_weekly_count = sum(
            getattr(data, f"daily_count_{count_type}") for data in mock_data
        )
        actual_weekly_count = row_in_actual_data.item(0, f"weekly_count_{count_type}")

        assert actual_weekly_count == expected_weekly_count


def assert_average_record_per_patient_correct(mock_data, row_in_actual_data):
    expected_average_patient_record = sum(
        data.average_records_per_patient for data in mock_data
    ) / len(mock_data)
    actual_average_patient_record = row_in_actual_data.item(
        0, "average_records_per_patient"
    )

    assert actual_average_patient_record == float(expected_average_patient_record)


def assert_number_of_patient_correct(mock_data, row_in_actual_data):
    most_recent_record_in_mock_data = max(mock_data, key=lambda data: data.date)
    expected_number_of_patients = most_recent_record_in_mock_data.number_of_patients
    actual_number_of_patient = row_in_actual_data.item(0, "number_of_patients")

    assert actual_number_of_patient == expected_number_of_patients


def test_summarise_organisation_data_can_handle_empty_input(mock_service):
    empty_input = []
    actual = mock_service.summarise_organisation_data(empty_input)

    assert isinstance(actual, pl.DataFrame)
    assert actual.is_empty()


def test_summarise_application_data(mock_service):
    mock_data = [
        MOCK_APPLICATION_DATA_1,
        MOCK_APPLICATION_DATA_2,
        MOCK_APPLICATION_DATA_3,
    ]

    expected = EXPECTED_SUMMARY_APPLICATION_DATA
    actual = mock_service.summarise_application_data(mock_data)

    assert_frame_equal(
        actual,
        expected,
        check_dtypes=False,
        check_row_order=False,
        check_column_order=False,
    )


def test_summarise_application_data_larger_mock_data(mock_service):
    mock_data_h81109 = build_random_application_data(
        "H81109", ["20240603", "20240604", "20240605", "20240606", "20240607"]
    )
    mock_data_y12345 = build_random_application_data(
        "Y12345", ["20240603", "20240604", "20240605", "20240606", "20240607"]
    )
    mock_organisation_data = mock_data_h81109 + mock_data_y12345
    shuffle(mock_organisation_data)

    active_users_count_h81109 = count_unique_user_ids(mock_data_h81109)
    active_users_count_y12345 = count_unique_user_ids(mock_data_y12345)

    expected = pl.DataFrame(
        [
            {
                "ods_code": "H81109",
                "active_users_count": len(active_users_count_h81109),
                "unique_active_user_ids_hashed": str(active_users_count_h81109),
            },
            {
                "ods_code": "Y12345",
                "active_users_count": len(active_users_count_y12345),
                "unique_active_user_ids_hashed": str(active_users_count_y12345),
            },
        ]
    )
    actual = mock_service.summarise_application_data(mock_organisation_data)

    assert_frame_equal(
        actual,
        expected,
        check_dtypes=False,
        check_row_order=False,
        check_column_order=False,
    )


def count_unique_user_ids(mock_data: list[ApplicationData]) -> list:
    active_users_of_each_day = [set(data.active_user_ids_hashed) for data in mock_data]
    unique_active_users_for_whole_week = set.union(*active_users_of_each_day)

    return sorted(list(unique_active_users_for_whole_week))


def test_summarise_application_data_can_handle_empty_input(mock_service):
    empty_input = []
    actual = mock_service.summarise_application_data(empty_input)

    assert isinstance(actual, pl.DataFrame)
    assert actual.is_empty()


def test_join_dataframes_by_ods_code(mock_service):
    mock_data_1 = pl.DataFrame([{"ods_code": "Y12345", "field1": "apple"}])
    mock_data_2 = pl.DataFrame(
        [
            {"ods_code": "Y12345", "field2": "banana"},
            {"ods_code": "Z56789", "field2": "cherry"},
        ]
    )

    expected = pl.DataFrame(
        [
            {"ods_code": "Y12345", "field1": "apple", "field2": "banana"},
            {"ods_code": "Z56789", "field2": "cherry"},
        ]
    )
    actual = mock_service.join_dataframes_by_ods_code([mock_data_1, mock_data_2])

    assert_frame_equal(actual, expected, check_dtypes=False, check_row_order=False)


def test_join_dataframes_by_ods_code_can_handle_empty_dataframe(mock_service):
    mock_data_1 = pl.DataFrame([{"ods_code": "Y12345", "field1": "cat"}])
    mock_data_2 = pl.DataFrame()
    mock_data_3 = pl.DataFrame(
        [
            {"ods_code": "Y12345", "field2": "dog"},
            {"ods_code": "Z56789", "field3": "lizard"},
        ]
    )

    expected = pl.DataFrame(
        [
            {"ods_code": "Y12345", "field1": "cat", "field2": "dog"},
            {"ods_code": "Z56789", "field3": "lizard"},
        ]
    )
    actual = mock_service.join_dataframes_by_ods_code(
        [mock_data_1, mock_data_2, mock_data_3]
    )

    assert_frame_equal(actual, expected, check_dtypes=False, check_row_order=False)


@freeze_time("20240512T07:00:00Z")
def test_store_report_to_s3(set_env, mock_s3_service, mock_temp_folder):
    mock_weekly_summary = EXPECTED_WEEKLY_SUMMARY
    expected_date_folder = "2024-05-11"
    expected_filename = "statistical_report_20240505-20240511.csv"

    service = StatisticalReportService()

    service.store_report_to_s3(mock_weekly_summary)

    mock_s3_service.upload_file.assert_called_with(
        s3_bucket_name=MOCK_STATISTICS_REPORT_BUCKET_NAME,
        file_key=f"statistic-reports/{expected_date_folder}/{expected_filename}",
        file_name=f"{mock_temp_folder}/{expected_filename}",
    )
