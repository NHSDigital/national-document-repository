import tempfile
from unittest.mock import call

import pytest
from botocore.exceptions import ClientError
from freezegun import freeze_time
from models.staging_metadata import METADATA_FILENAME
from pydantic import ValidationError
from services.bulk_upload_metadata_service import BulkUploadMetadataService
from tests.unit.conftest import MOCK_LG_METADATA_SQS_QUEUE, MOCK_STAGING_STORE_BUCKET
from tests.unit.helpers.data.bulk_upload.test_data import (
    EXPECTED_PARSED_METADATA,
    EXPECTED_PARSED_METADATA_2,
    EXPECTED_SQS_MSG_FOR_PATIENT_0000000000,
    EXPECTED_SQS_MSG_FOR_PATIENT_123456789,
    EXPECTED_SQS_MSG_FOR_PATIENT_1234567890,
    MOCK_METADATA,
)
from utils.exceptions import BulkUploadMetadataException

# METADATA_FILE_DIR = "lambdas/tests/unit/helpers/data/bulk_upload"
METADATA_FILE_DIR = "tests/unit/helpers/data/bulk_upload"
MOCK_METADATA_CSV = f"{METADATA_FILE_DIR}/metadata.csv"
MOCK_DUPLICATE_ODS_METADATA_CSV = (
    f"{METADATA_FILE_DIR}/metadata_with_duplicates_different_ods.csv"
)
MOCK_INVALID_METADATA_CSV_FILES = [
    f"{METADATA_FILE_DIR}/metadata_invalid.csv",
    f"{METADATA_FILE_DIR}/metadata_invalid_empty_nhs_number.csv",
    f"{METADATA_FILE_DIR}/metadata_invalid_unexpected_comma.csv",
]
MOCK_TEMP_FOLDER = "tests/unit/helpers/data/bulk_upload"


def test_process_metadata_send_metadata_to_sqs_queue(
    set_env,
    mocker,
    metadata_filename,
    mock_sqs_service,
    mock_s3_service,
    mock_download_metadata_from_s3,
    metadata_service,
):
    mock_download_metadata_from_s3.return_value = MOCK_METADATA_CSV
    mocker.patch("uuid.uuid4", return_value="123412342")

    mock_s3_service.copy_across_bucket.return_value = None

    expected_calls = [
        call(
            queue_url=MOCK_LG_METADATA_SQS_QUEUE,
            message_body=EXPECTED_SQS_MSG_FOR_PATIENT_1234567890,
            nhs_number="1234567890",
            group_id="bulk_upload_123412342",
        ),
        call(
            queue_url=MOCK_LG_METADATA_SQS_QUEUE,
            message_body=EXPECTED_SQS_MSG_FOR_PATIENT_123456789,
            nhs_number="123456789",
            group_id="bulk_upload_123412342",
        ),
        call(
            queue_url=MOCK_LG_METADATA_SQS_QUEUE,
            message_body=EXPECTED_SQS_MSG_FOR_PATIENT_0000000000,
            nhs_number="0000000000",
            group_id="bulk_upload_123412342",
        ),
    ]

    metadata_service.process_metadata(metadata_filename)

    assert mock_sqs_service.send_message_with_nhs_number_attr_fifo.call_count == 3
    mock_sqs_service.send_message_with_nhs_number_attr_fifo.assert_has_calls(
        expected_calls
    )


def test_process_metadata_catch_and_log_error_when_fail_to_get_metadata_csv_from_s3(
    set_env,
    caplog,
    metadata_filename,
    mock_s3_service,
    mock_sqs_service,
    metadata_service,
):
    mock_s3_service.download_file.side_effect = ClientError(
        {"Error": {"Code": "403", "Message": "Forbidden"}},
        "S3:HeadObject",
    )
    expected_err_msg = 'No metadata file could be found with the name "metadata.csv"'

    with pytest.raises(BulkUploadMetadataException) as e:
        metadata_service.process_metadata(metadata_filename)

    assert expected_err_msg in str(e.value)
    assert caplog.records[-1].msg == expected_err_msg
    assert caplog.records[-1].levelname == "ERROR"

    mock_sqs_service.send_message_with_nhs_number_attr_fifo.assert_not_called()


def test_process_metadata_raise_validation_error_when_metadata_csv_is_invalid(
    set_env,
    caplog,
    metadata_filename,
    mock_sqs_service,
    mock_download_metadata_from_s3,
    metadata_service,
):
    for invalid_csv_file in MOCK_INVALID_METADATA_CSV_FILES:
        mock_download_metadata_from_s3.return_value = invalid_csv_file

        with pytest.raises(BulkUploadMetadataException) as e:
            metadata_service.process_metadata(metadata_filename)

        assert "validation error" in str(e.value)
        assert "validation error" in caplog.records[-1].msg
        assert caplog.records[-1].levelname == "ERROR"

        mock_sqs_service.send_message_with_nhs_number_attr_fifo.assert_not_called()


def test_process_metadata_raise_validation_error_when_gp_practice_code_is_missing(
    set_env,
    caplog,
    metadata_filename,
    mock_sqs_service,
    mock_download_metadata_from_s3,
    metadata_service,
):
    mock_download_metadata_from_s3.return_value = (
        f"{METADATA_FILE_DIR}/metadata_invalid_empty_gp_practice_code.csv"
    )
    expected_error_log = (
        "Failed to parse metadata.csv: 1 validation error for MetadataFile\n"
        + "GP-PRACTICE-CODE\n  missing GP-PRACTICE-CODE for patient 1234567890"
    )

    with pytest.raises(BulkUploadMetadataException) as e:
        metadata_service.process_metadata(metadata_filename)

    assert expected_error_log in str(e.value)
    assert expected_error_log in caplog.records[-1].msg
    assert caplog.records[-1].levelname == "ERROR"

    mock_sqs_service.send_message_with_nhs_number_attr_fifo.assert_not_called()


def test_process_metadata_raise_client_error_when_failed_to_send_message_to_sqs(
    set_env,
    caplog,
    metadata_filename,
    mock_s3_service,
    mock_sqs_service,
    mock_tempfile,
    metadata_service,
):
    mock_client_error = ClientError(
        {
            "Error": {
                "Code": "AWS.SimpleQueueService.NonExistentQueue",
                "Message": "The specified queue does not exist",
            }
        },
        "SendMessage",
    )
    mock_sqs_service.send_message_with_nhs_number_attr_fifo.side_effect = (
        mock_client_error
    )
    expected_err_msg = (
        "An error occurred (AWS.SimpleQueueService.NonExistentQueue) when calling the SendMessage operation:"
        " The specified queue does not exist"
    )

    with pytest.raises(BulkUploadMetadataException) as e:
        metadata_service.process_metadata(metadata_filename)

    assert expected_err_msg in str(e.value)
    assert caplog.records[-1].msg == expected_err_msg
    assert caplog.records[-1].levelname == "ERROR"


def test_download_metadata_from_s3(
    set_env, metadata_filename, mock_s3_service, mock_tempfile, metadata_service
):
    actual = metadata_service.download_metadata_from_s3(metadata_filename)
    expected = MOCK_METADATA_CSV

    mock_s3_service.download_file.assert_called_with(
        s3_bucket_name=MOCK_STAGING_STORE_BUCKET,
        file_key=metadata_filename,
        download_path=f"{MOCK_TEMP_FOLDER}/{metadata_filename}",
    )
    assert actual == expected


def test_download_metadata_from_s3_raise_error_when_failed_to_download(
    set_env, metadata_filename, mock_s3_service, mock_tempfile, metadata_service
):
    mock_s3_service.download_file.side_effect = ClientError(
        {"Error": {"Code": "500", "Message": "file not exist in bucket"}},
        "s3_get_object",
    )

    with pytest.raises(ClientError):
        metadata_service.download_metadata_from_s3(metadata_filename)


def test_csv_to_staging_metadata(set_env, metadata_service):
    actual = metadata_service.csv_to_staging_metadata(MOCK_METADATA_CSV)
    expected = EXPECTED_PARSED_METADATA
    assert actual == expected


def test_duplicates_csv_to_staging_metadata(set_env, metadata_service):
    actual = metadata_service.csv_to_staging_metadata(MOCK_DUPLICATE_ODS_METADATA_CSV)
    expected = EXPECTED_PARSED_METADATA_2
    assert actual == expected


def test_csv_to_staging_metadata_raise_error_when_metadata_invalid(
    set_env, metadata_service
):
    for invalid_csv_file in MOCK_INVALID_METADATA_CSV_FILES:
        with pytest.raises(ValidationError):
            metadata_service.csv_to_staging_metadata(invalid_csv_file)


def test_send_metadata_to_sqs(set_env, mocker, mock_sqs_service, metadata_service):
    mocker.patch("uuid.uuid4", return_value="123412342")
    expected_calls = [
        call(
            queue_url=MOCK_LG_METADATA_SQS_QUEUE,
            message_body=EXPECTED_SQS_MSG_FOR_PATIENT_1234567890,
            nhs_number="1234567890",
            group_id="bulk_upload_123412342",
        ),
        call(
            queue_url=MOCK_LG_METADATA_SQS_QUEUE,
            message_body=EXPECTED_SQS_MSG_FOR_PATIENT_123456789,
            nhs_number="123456789",
            group_id="bulk_upload_123412342",
        ),
    ]

    metadata_service.send_metadata_to_fifo_sqs(MOCK_METADATA)

    mock_sqs_service.send_message_with_nhs_number_attr_fifo.assert_has_calls(
        expected_calls
    )
    assert mock_sqs_service.send_message_with_nhs_number_attr_fifo.call_count == 2


def test_send_metadata_to_sqs_raise_error_when_fail_to_send_message(
    set_env, mock_sqs_service, metadata_service
):
    mock_sqs_service.send_message_with_nhs_number_attr_fifo.side_effect = ClientError(
        {
            "Error": {
                "Code": "AWS.SimpleQueueService.NonExistentQueue",
                "Message": "The specified queue does not exist",
            }
        },
        "SendMessage",
    )

    with pytest.raises(ClientError):
        metadata_service.send_metadata_to_fifo_sqs(EXPECTED_PARSED_METADATA)


@freeze_time("2024-01-01 12:34:56")
def test_copy_metadata_to_dated_folder(
    set_env, metadata_filename, mock_s3_service, metadata_service
):
    metadata_service.copy_metadata_to_dated_folder(metadata_filename)

    mock_s3_service.copy_across_bucket.assert_called_once_with(
        metadata_service.staging_bucket_name,
        metadata_filename,
        metadata_service.staging_bucket_name,
        "metadata/2024-01-01_12-34.csv",
    )

    mock_s3_service.delete_object.assert_called_once_with(
        metadata_service.staging_bucket_name,
        metadata_filename,
    )


def test_clear_temp_storage(set_env, mocker, mock_tempfile, metadata_service):
    mocked_rm = mocker.patch("shutil.rmtree")

    metadata_service.clear_temp_storage()

    mocked_rm.assert_called_once_with(metadata_service.temp_download_dir)


@pytest.fixture
def metadata_service():
    yield BulkUploadMetadataService()


@pytest.fixture
def metadata_filename():
    return METADATA_FILENAME


@pytest.fixture
def mock_download_metadata_from_s3(mocker):
    yield mocker.patch.object(BulkUploadMetadataService, "download_metadata_from_s3")


@pytest.fixture
def mock_s3_service(mocker):
    patched_instance = mocker.patch(
        "services.bulk_upload_metadata_service.S3Service"
    ).return_value
    yield patched_instance


@pytest.fixture
def mock_tempfile(mocker):
    mocker.patch.object(tempfile, "mkdtemp", return_value=MOCK_TEMP_FOLDER)
    mocker.patch("shutil.rmtree")
    yield


@pytest.fixture
def mock_sqs_service(mocker):
    patched_instance = mocker.patch(
        "services.bulk_upload_metadata_service.SQSService"
    ).return_value
    yield patched_instance
