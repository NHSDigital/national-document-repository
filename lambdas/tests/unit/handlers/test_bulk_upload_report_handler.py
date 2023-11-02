import csv
import os
from datetime import datetime
from unittest.mock import call

from boto3.dynamodb.conditions import Attr
from freezegun import freeze_time
from handlers.bulk_upload_report_handler import (get_dynamodb_report_items,
                                                 get_times_for_scan,
                                                 report_handler,
                                                 write_empty_report,
                                                 write_items_to_csv)
from tests.unit.conftest import (MOCK_BULK_REPORT_TABLE_NAME,
                                 MOCK_LG_STAGING_STORE_BUCKET)
from tests.unit.helpers.data.dynamo_scan_response import (
    EXPECTED_RESPONSE, MOCK_EMPTY_RESPONSE, MOCK_RESPONSE,
    MOCK_RESPONSE_WITH_LAST_KEY, UNEXPECTED_RESPONSE)


@freeze_time("2012-01-14 7:20:01")
def test_get_time_for_scan_after_7am():
    expected_end_report_time = datetime(2012, 1, 14, 7, 0, 0, 0)
    expected_start_report_time = datetime(2012, 1, 13, 7, 0, 0, 0)

    actual_start_time, actual_end_time = get_times_for_scan()

    assert expected_start_report_time == actual_start_time
    assert expected_end_report_time == actual_end_time


@freeze_time("2012-01-14 6:59:59")
def test_get_time_for_scan_before_7am():
    expected_end_report_time = datetime(2012, 1, 13, 7, 0, 0, 0)
    expected_start_report_time = datetime(2012, 1, 12, 7, 0, 0, 0)

    actual_start_time, actual_end_time = get_times_for_scan()

    assert expected_start_report_time == actual_start_time
    assert expected_end_report_time == actual_end_time


@freeze_time("2012-01-14 7:00:00")
def test_get_time_for_scan_at_7am():
    expected_end_report_time = datetime(2012, 1, 14, 7, 0, 0, 0)
    expected_start_report_time = datetime(2012, 1, 13, 7, 0, 0, 0)

    actual_start_time, actual_end_time = get_times_for_scan()

    assert expected_start_report_time == actual_start_time
    assert expected_end_report_time == actual_end_time


def test_write_items_to_csv():
    items = [{"id": "1", "key": "value"}, {"id": "2", "key": "value"}]

    write_items_to_csv(items, "test_file")

    with open("test_file") as test_file:
        csv_reader = csv.DictReader(test_file, delimiter=",")
        assert csv_reader.fieldnames == list(items[0].keys())
        for row, item in zip(csv_reader, items):
            assert row == item
    os.remove("test_file")


def test_write_empty_file_to_txt():
    write_empty_report("test_file")

    with open("test_file") as test_file:
        file_content = test_file.read()
    assert file_content == "No data was found for this timeframe"
    os.remove("test_file")


def test_get_dynamo_data_2_calls(mocker, set_env):
    db_service = mocker.MagicMock()
    mock_start_time = 1688395630
    mock_end_time = 1688195630
    mock_filter = Attr("Timestamp").gt(mock_start_time) & Attr("Timestamp").lt(
        mock_end_time
    )
    mock_last_key = {"FileName": "Screenshot 2023-08-15 at 16.17.56.png"}
    db_service.scan_table.side_effect = [MOCK_RESPONSE_WITH_LAST_KEY, MOCK_RESPONSE]
    actual = get_dynamodb_report_items(db_service, mock_start_time, mock_end_time)
    assert actual == EXPECTED_RESPONSE * 2
    assert db_service.scan_table.call_count == 2
    calls = [
        call(MOCK_BULK_REPORT_TABLE_NAME, filter_expression=mock_filter),
        call(
            MOCK_BULK_REPORT_TABLE_NAME,
            exclusive_start_key=mock_last_key,
            filter_expression=mock_filter,
        ),
    ]
    db_service.scan_table.assert_has_calls(calls)


def test_get_dynamo_data_with_no_start_key(mocker, set_env):
    db_service = mocker.MagicMock()
    mock_start_time = 1688395630
    mock_end_time = 1688195630
    mock_filter = Attr("Timestamp").gt(mock_start_time) & Attr("Timestamp").lt(
        mock_end_time
    )
    db_service.scan_table.side_effect = [MOCK_RESPONSE]
    actual = get_dynamodb_report_items(db_service, mock_start_time, mock_end_time)
    assert actual == EXPECTED_RESPONSE
    db_service.scan_table.assert_called_once()
    db_service.scan_table.assert_called_with(
        MOCK_BULK_REPORT_TABLE_NAME, filter_expression=mock_filter
    )


def test_get_dynamo_data_with_no_items(mocker, set_env):
    db_service = mocker.MagicMock()
    mock_start_time = 1688395630
    mock_end_time = 1688195630
    db_service.scan_table.side_effect = [MOCK_EMPTY_RESPONSE]
    actual = get_dynamodb_report_items(db_service, mock_start_time, mock_end_time)
    assert actual == []
    db_service.scan_table.assert_called_once()


def test_get_dynamo_data_with_bad_response(mocker, set_env):
    db_service = mocker.MagicMock()
    mock_start_time = 1688395630
    mock_end_time = 1688195630
    db_service.scan_table.side_effect = [UNEXPECTED_RESPONSE]
    actual = get_dynamodb_report_items(db_service, mock_start_time, mock_end_time)
    assert actual is None
    db_service.scan_table.assert_called_once()


def test_report_handler_no_items_return(mocker, set_env):
    mock_db_service = mocker.MagicMock()
    mock_s3_service = mocker.MagicMock()
    mock_end_report_time = datetime(2012, 1, 14, 7, 0, 0, 0)
    mock_start_report_time = datetime(2012, 1, 13, 7, 0, 0, 0)
    mock_file_name = f"Bulk upload report for {str(mock_start_report_time)} to {str(mock_end_report_time)}.txt"
    mock_get_time = mocker.patch(
        "handlers.bulk_upload_report_handler.get_times_for_scan",
        return_value=(mock_start_report_time, mock_end_report_time),
    )
    mock_write_empty_csv = mocker.patch(
        "handlers.bulk_upload_report_handler.write_empty_report"
    )
    mock_get_db = mocker.patch(
        "handlers.bulk_upload_report_handler.get_dynamodb_report_items", return_value=[]
    )

    report_handler(mock_db_service, mock_s3_service)

    mock_get_time.assert_called_once()
    mock_get_db.assert_called_once()
    mock_get_db.assert_called_with(
        mock_db_service,
        int(mock_start_report_time.timestamp()),
        int(mock_end_report_time.timestamp()),
    )
    mock_write_empty_csv.assert_called_once()
    mock_s3_service.upload_file.assert_called_with(
        s3_bucket_name=MOCK_LG_STAGING_STORE_BUCKET,
        file_key=f"reports/{mock_file_name}",
        file_name=f"/tmp/{mock_file_name}",
    )


def test_report_handler_with_items(mocker, set_env):
    mock_db_service = mocker.MagicMock()
    mock_s3_service = mocker.MagicMock()
    mock_end_report_time = datetime(2012, 1, 14, 7, 0, 0, 0)
    mock_start_report_time = datetime(2012, 1, 13, 7, 0, 0, 0)
    mock_file_name = f"Bulk upload report for {str(mock_start_report_time)} to {str(mock_end_report_time)}.csv"
    mock_get_time = mocker.patch(
        "handlers.bulk_upload_report_handler.get_times_for_scan",
        return_value=(mock_start_report_time, mock_end_report_time),
    )
    mock_write_empty_csv = mocker.patch(
        "handlers.bulk_upload_report_handler.write_empty_report"
    )
    mock_get_db = mocker.patch(
        "handlers.bulk_upload_report_handler.get_dynamodb_report_items",
        return_value=[{"test": "dsfsf"}],
    )
    mock_write_csv = mocker.patch(
        "handlers.bulk_upload_report_handler.write_items_to_csv"
    )

    report_handler(mock_db_service, mock_s3_service)

    mock_get_time.assert_called_once()
    mock_get_db.assert_called_once()
    mock_get_db.assert_called_with(
        mock_db_service,
        int(mock_start_report_time.timestamp()),
        int(mock_end_report_time.timestamp()),
    )
    mock_write_empty_csv.ssert_not_called()
    mock_write_csv.assert_called_once()
    mock_write_csv.assert_called_with([{"test": "dsfsf"}], f"/tmp/{mock_file_name}")
    mock_s3_service.upload_file.assert_called_with(
        s3_bucket_name=MOCK_LG_STAGING_STORE_BUCKET,
        file_key=f"reports/{mock_file_name}",
        file_name=f"/tmp/{mock_file_name}",
    )
