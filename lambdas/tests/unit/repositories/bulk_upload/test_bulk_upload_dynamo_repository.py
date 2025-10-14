import pytest
from enums.upload_status import UploadStatus
from freezegun import freeze_time
from repositories.bulk_upload.bulk_upload_dynamo_repository import (
    BulkUploadDynamoRepository,
)
from tests.unit.conftest import MOCK_BULK_REPORT_TABLE_NAME, MOCK_LG_TABLE_NAME
from tests.unit.helpers.data.bulk_upload.test_data import (
    TEST_DOCUMENT_REFERENCE,
    TEST_DOCUMENT_REFERENCE_LIST,
    TEST_NHS_NUMBER_FOR_BULK_UPLOAD,
    TEST_STAGING_METADATA,
)


@pytest.fixture
def repo_under_test(set_env, mocker):
    repo = BulkUploadDynamoRepository()
    mocker.patch.object(repo, "dynamo_repository")
    yield repo


def test_create_record_in_dynamodb_table(set_env, repo_under_test):
    repo_under_test.create_record_in_lg_dynamo_table(TEST_DOCUMENT_REFERENCE)

    assert TEST_DOCUMENT_REFERENCE in repo_under_test.dynamo_records_in_transaction

    repo_under_test.dynamo_repository.create_item.assert_called_with(
        table_name=MOCK_LG_TABLE_NAME,
        item=TEST_DOCUMENT_REFERENCE.model_dump(by_alias=True, exclude_none=True),
    )


@freeze_time("2023-10-1 13:00:00")
def test_report_upload_complete_add_record_to_dynamodb(
    repo_under_test, set_env, mock_uuid
):
    repo_under_test.write_report_upload_to_dynamo(
        TEST_STAGING_METADATA, upload_status=UploadStatus.COMPLETE
    )

    assert repo_under_test.dynamo_repository.create_item.call_count == len(
        TEST_STAGING_METADATA.files
    )

    for file in TEST_STAGING_METADATA.files:
        expected_dynamo_db_record = {
            "Date": "2023-10-01",
            "FilePath": file.file_path,
            "StoredFileName": file.stored_file_name,
            "ID": mock_uuid,
            "NhsNumber": TEST_STAGING_METADATA.nhs_number,
            "Timestamp": 1696165200,
            "UploadStatus": UploadStatus.COMPLETE,
            "UploaderOdsCode": "Y12345",
            "PdsOdsCode": "",
        }
        repo_under_test.dynamo_repository.create_item.assert_any_call(
            item=expected_dynamo_db_record, table_name=MOCK_BULK_REPORT_TABLE_NAME
        )


@freeze_time("2023-10-2 13:00:00")
def test_report_upload_failure_add_record_to_dynamodb(
    repo_under_test, set_env, mock_uuid
):
    mock_reason = "File name invalid"
    repo_under_test.write_report_upload_to_dynamo(
        TEST_STAGING_METADATA,
        upload_status=UploadStatus.FAILED,
        reason=mock_reason,
    )

    for file in TEST_STAGING_METADATA.files:
        expected_dynamo_db_record = {
            "Date": "2023-10-02",
            "FilePath": file.file_path,
            "StoredFileName": file.stored_file_name,
            "ID": mock_uuid,
            "NhsNumber": TEST_STAGING_METADATA.nhs_number,
            "Timestamp": 1696251600,
            "UploadStatus": "failed",
            "Reason": mock_reason,
            "UploaderOdsCode": "Y12345",
            "PdsOdsCode": "",
        }
        repo_under_test.dynamo_repository.create_item.assert_any_call(
            item=expected_dynamo_db_record, table_name=MOCK_BULK_REPORT_TABLE_NAME
        )


def test_rollback_transaction(repo_under_test, set_env, mock_uuid):
    repo_under_test.dynamo_records_in_transaction = TEST_DOCUMENT_REFERENCE_LIST
    repo_under_test.dest_bucket_files_in_transaction = [
        f"{TEST_NHS_NUMBER_FOR_BULK_UPLOAD}/mock_uuid_1",
        f"{TEST_NHS_NUMBER_FOR_BULK_UPLOAD}/mock_uuid_2",
    ]

    repo_under_test.rollback_transaction()

    repo_under_test.dynamo_repository.delete_item.assert_called_with(
        table_name=MOCK_LG_TABLE_NAME, key={"ID": mock_uuid}
    )
    assert repo_under_test.dynamo_repository.delete_item.call_count == len(
        TEST_DOCUMENT_REFERENCE_LIST
    )
