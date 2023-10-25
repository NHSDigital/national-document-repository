import pytest
from botocore.exceptions import ClientError
from services.bulk_upload_service import BulkUploadService
from tests.unit.conftest import (
    MOCK_LG_BUCKET,
    MOCK_LG_STAGING_STORE_BUCKET,
    MOCK_LG_TABLE_NAME,
    TEST_OBJECT_KEY,
)
from tests.unit.helpers.data.bulk_upload.test_data import (
    TEST_DOCUMENT_REFERENCE,
    TEST_DOCUMENT_REFERENCE_LIST,
    TEST_FILE_METADATA,
    TEST_NHS_NUMBER_FOR_BULK_UPLOAD,
    TEST_SQS_MESSAGE,
    TEST_STAGING_METADATA,
    TEST_STAGING_METADATA_WITH_INVALID_FILENAME,
    TEST_SQS_MESSAGE_WITH_INVALID_FILENAME,
)
from utils.exceptions import InvalidMessageException
from utils.lloyd_george_validator import LGInvalidFilesException


@pytest.fixture
def mock_uuid(mocker):
    test_uuid = TEST_OBJECT_KEY
    mocker.patch("uuid.uuid4", return_value=test_uuid)
    yield test_uuid


def test_handle_sqs_message_calls_create_lg_records_and_copy_files_when_validation_passed(
    set_env, mocker, mock_uuid
):
    mock_create_lg_records_and_copy_files = mocker.patch.object(
        BulkUploadService, "create_lg_records_and_copy_files"
    )
    mock_report_upload_complete = mocker.patch.object(
        BulkUploadService, "report_upload_complete"
    )
    mocker.patch.object(BulkUploadService, "validate_files", return_value=None)

    service = BulkUploadService()
    service.handle_sqs_message(message=TEST_SQS_MESSAGE)

    mock_create_lg_records_and_copy_files.assert_called_with(TEST_STAGING_METADATA)
    mock_report_upload_complete.assert_called()


def test_handle_sqs_message_calls_report_upload_failure_when_lg_file_are_invalid(
    set_env, mocker, mock_uuid
):
    mock_create_lg_records_and_copy_files = mocker.patch.object(
        BulkUploadService, "create_lg_records_and_copy_files"
    )
    mocked_report_upload_failure = mocker.patch.object(
        BulkUploadService, "report_upload_failure"
    )
    mocked_error = LGInvalidFilesException(
        "One or more of the files do not match naming convention"
    )
    mocker.patch.object(BulkUploadService, "validate_files", side_effect=mocked_error)

    service = BulkUploadService()
    service.handle_sqs_message(message=TEST_SQS_MESSAGE_WITH_INVALID_FILENAME)

    mock_create_lg_records_and_copy_files.assert_not_called()
    mocked_report_upload_failure.assert_called_with(
        TEST_STAGING_METADATA_WITH_INVALID_FILENAME, str(mocked_error)
    )


def test_handle_sqs_message_rollback_transaction_when_validation_pass_but_file_transfer_failed_halfway(
    set_env, mocker, mock_uuid
):
    mocked_rollback_transaction = mocker.patch.object(
        BulkUploadService, "rollback_transaction"
    )
    mocked_report_upload_failure = mocker.patch.object(
        BulkUploadService, "report_upload_failure"
    )
    service = BulkUploadService()
    service.s3_service = mocker.MagicMock()
    service.dynamo_service = mocker.MagicMock()
    service.validate_files = mocker.MagicMock()

    mock_client_error = ClientError(
        {"Error": {"Code": "404", "Message": "Object not found in bucket"}},
        "GetObject",
    )

    # simulate a client error occur when copying the 3rd file
    service.s3_service.copy_across_bucket.side_effect = [None, None, mock_client_error]

    service.handle_sqs_message(message=TEST_SQS_MESSAGE)

    mocked_rollback_transaction.assert_called()
    mocked_report_upload_failure.assert_called()


def test_handle_sqs_message_raise_InvalidMessageException_when_failed_to_extract_data_from_message(
    set_env, mocker
):
    invalid_message = {"body": "invalid content"}
    mock_create_lg_records_and_copy_files = mocker.patch.object(
        BulkUploadService, "create_lg_records_and_copy_files"
    )

    service = BulkUploadService()
    with pytest.raises(InvalidMessageException):
        service.handle_sqs_message(invalid_message)

    mock_create_lg_records_and_copy_files.assert_not_called()


def test_validate_files_raise_LGInvalidFilesException_when_file_names_invalid(set_env):
    service = BulkUploadService()

    with pytest.raises(LGInvalidFilesException):
        service.validate_files(TEST_STAGING_METADATA_WITH_INVALID_FILENAME)


def test_create_lg_records_and_copy_files(set_env, mocker, mock_uuid):
    service = BulkUploadService()
    service.s3_service = mocker.MagicMock()
    service.dynamo_service = mocker.MagicMock()
    service.convert_to_document_reference = mocker.MagicMock(
        return_value=TEST_DOCUMENT_REFERENCE
    )

    service.create_lg_records_and_copy_files(TEST_STAGING_METADATA)

    nhs_number = TEST_STAGING_METADATA.nhs_number

    for file in TEST_STAGING_METADATA.files:
        expected_source_file_key = BulkUploadService.strip_leading_slash(file.file_path)
        expected_dest_file_key = f"{nhs_number}/{mock_uuid}"
        service.s3_service.copy_across_bucket.assert_any_call(
            source_bucket=MOCK_LG_STAGING_STORE_BUCKET,
            source_file_key=expected_source_file_key,
            dest_bucket=MOCK_LG_BUCKET,
            dest_file_key=expected_dest_file_key,
        )
    assert service.s3_service.copy_across_bucket.call_count == 3

    service.dynamo_service.create_item.assert_any_call(
        table_name=MOCK_LG_TABLE_NAME, item=TEST_DOCUMENT_REFERENCE.to_dict()
    )
    assert service.dynamo_service.create_item.call_count == 3


def test_convert_to_document_reference(set_env, mock_uuid):
    service = BulkUploadService()

    expected = TEST_DOCUMENT_REFERENCE
    actual = service.convert_to_document_reference(
        file_metadata=TEST_FILE_METADATA, nhs_number=TEST_STAGING_METADATA.nhs_number
    )

    # exclude the `created` timestamp from comparison
    actual.created = "mock_timestamp"
    expected.created = "mock_timestamp"

    assert actual == expected


def test_rollback_transaction(set_env, mocker, mock_uuid):
    service = BulkUploadService()
    service.s3_service = mocker.MagicMock()
    service.dynamo_service = mocker.MagicMock()

    service.dynamo_records_in_transaction = TEST_DOCUMENT_REFERENCE_LIST
    service.dest_bucket_files_in_transaction = [
        f"{TEST_NHS_NUMBER_FOR_BULK_UPLOAD}/mock_uuid_1",
        f"{TEST_NHS_NUMBER_FOR_BULK_UPLOAD}/mock_uuid_2",
    ]

    service.rollback_transaction()

    service.dynamo_service.delete_item.assert_called_with(
        table_name=MOCK_LG_TABLE_NAME, key={"ID": mock_uuid}
    )
    assert service.dynamo_service.delete_item.call_count == len(
        TEST_DOCUMENT_REFERENCE_LIST
    )

    service.s3_service.delete_object.assert_any_call(
        s3_bucket_name=MOCK_LG_BUCKET,
        file_key=f"{TEST_NHS_NUMBER_FOR_BULK_UPLOAD}/mock_uuid_1",
    )
    service.s3_service.delete_object.assert_any_call(
        s3_bucket_name=MOCK_LG_BUCKET,
        file_key=f"{TEST_NHS_NUMBER_FOR_BULK_UPLOAD}/mock_uuid_2",
    )
    assert service.s3_service.delete_object.call_count == 2
