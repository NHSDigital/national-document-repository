import os

import pytest
from botocore.exceptions import ClientError
from freezegun import freeze_time
from models.staging_metadata import METADATA_FILENAME
from msgpack.fallback import BytesIO
from services.bulk_upload_metadata_preprocessor_service import (
    MetadataPreprocessorService,
)
from tests.unit.conftest import (
    MOCK_CLIENT_ERROR,
    MOCK_STAGING_STORE_BUCKET,
    TEST_BASE_DIRECTORY,
)
from utils.exceptions import InvalidFileNameException, MetadataPreprocessingException


class MockMetadataPreprocessorService(MetadataPreprocessorService):
    def validate_record_filename(self, original_filename: str, *args, **kwargs) -> str:
        return original_filename


@pytest.fixture(autouse=True)
@freeze_time("2025-01-01T12:00:00")
def test_service(mocker, set_env):
    mocker.patch("services.bulk_upload_metadata_preprocessor_service.S3Service")
    service = MockMetadataPreprocessorService(
        practice_directory="test_practice_directory"
    )
    return service


@pytest.fixture
def mock_get_metadata_rows_from_file(mocker, test_service):
    return mocker.patch.object(test_service, "get_metadata_rows_from_file")


@pytest.fixture
def mock_generate_and_save_csv_file(mocker, test_service):
    return mocker.patch.object(test_service, "generate_and_save_csv_file")


@pytest.fixture
def mock_s3_client(mocker, test_service):
    return mocker.patch.object(test_service.s3_service, "client")


@pytest.fixture
def sample_metadata_row():
    return {
        "FILEPATH": "01 of 02_Lloyd_George_Record_[Dwayne Basil COWIE]_[9730787506]_[18-09-1974].pdf",
        "GP-PRACTICE-CODE": "M85143",
        "NHS-NO": "9730787506",
        "PAGE COUNT": "1",
        "SCAN-DATE": "03/09/2022",
        "SCAN-ID": "NEC",
        "SECTION": "LG",
        "SUB-SECTION": "",
        "UPLOAD": "04/10/2023",
        "USER-ID": "NEC",
    }


@pytest.fixture
def mock_metadata_file_get_object():
    def _mock_metadata_file_get_object(test_file_path: str, *args, **kwargs):
        with open(test_file_path, "rb") as file:
            test_file_data = file.read()

        return {"Body": BytesIO(test_file_data)}

    return _mock_metadata_file_get_object


@pytest.fixture
def mock_update_date_in_row(mocker, test_service):
    return mocker.patch.object(
        test_service,
        "update_date_in_row",
        side_effect=lambda original_date: original_date,
    )


def test_process_metadata_success(test_service, mocker):
    get_metadata_mock = mocker.patch.object(
        test_service,
        "get_metadata_rows_from_file",
        return_value=[{"FILEPATH": "file1.pdf"}],
    )
    generate_map_mock = mocker.patch.object(
        test_service,
        "generate_renaming_map",
        return_value=(
            [({"FILEPATH": "file1.pdf"}, {"FILEPATH": "new_file1.pdf"})],
            [{"FILEPATH": "bad_file.pdf"}],
            [{"REASON": "invalid"}],
        ),
    )
    standardize_mock = mocker.patch.object(
        test_service,
        "standardize_filenames",
        return_value=[{"FILEPATH": "new_file1.pdf"}],
    )
    move_file_mock = mocker.patch.object(
        test_service, "move_original_metadata_file", return_value=True
    )
    delete_mock = mocker.patch.object(test_service.s3_service, "delete_object")
    generate_csv_mock = mocker.patch.object(test_service, "generate_and_save_csv_file")

    test_service.process_metadata()

    assert get_metadata_mock.called
    assert generate_map_mock.called
    assert standardize_mock.called
    assert move_file_mock.called
    assert delete_mock.called
    assert generate_csv_mock.called


def test_process_metadata_move_fails(test_service, mocker):
    mocker.patch.object(
        test_service,
        "get_metadata_rows_from_file",
        return_value=[{"FILEPATH": "file1.pdf"}],
    )
    mocker.patch.object(
        test_service,
        "generate_renaming_map",
        return_value=(
            [({"FILEPATH": "file1.pdf"}, {"FILEPATH": "new_file1.pdf"})],
            [],
            [],
        ),
    )
    mocker.patch.object(
        test_service,
        "standardize_filenames",
        return_value=[{"FILEPATH": "new_file1.pdf"}],
    )
    move_file_mock = mocker.patch.object(
        test_service, "move_original_metadata_file", return_value=False
    )
    delete_mock = mocker.patch.object(test_service.s3_service, "delete_object")
    generate_csv_mock = mocker.patch.object(test_service, "generate_and_save_csv_file")

    test_service.process_metadata()

    move_file_mock.assert_called_once()
    delete_mock.assert_not_called()
    generate_csv_mock.assert_called_once()


def test_get_metadata_csv_from_file_metadata_exists(
    test_service, mock_metadata_file_get_object
):
    test_preprocessed_metadata_file = os.path.join(
        TEST_BASE_DIRECTORY,
        "helpers/data/bulk_upload/preprocessed",
        f"preprocessed_{METADATA_FILENAME}",
    )
    test_file_key = f"{test_service.practice_directory}/{METADATA_FILENAME}"

    test_service.s3_service.file_exist_on_s3.return_value = True
    test_service.s3_service.client.get_object.side_effect = (
        lambda Bucket, Key: mock_metadata_file_get_object(
            test_preprocessed_metadata_file, Bucket, Key
        )
    )

    test_service.get_metadata_rows_from_file(
        file_key=test_file_key,
        bucket_name=MOCK_STAGING_STORE_BUCKET,
    )

    test_service.s3_service.file_exist_on_s3.assert_called_once_with(
        s3_bucket_name=MOCK_STAGING_STORE_BUCKET, file_key=test_file_key
    )
    test_service.s3_service.client.get_object.assert_called_once_with(
        Bucket=MOCK_STAGING_STORE_BUCKET, Key=test_file_key
    )


def test_get_metadata_csv_from_file_metadata_does_not_exist(test_service, caplog):
    test_file_key = f"{test_service.practice_directory}/{METADATA_FILENAME}"

    test_service.s3_service.file_exist_on_s3.return_value = False

    with pytest.raises(MetadataPreprocessingException) as exc_info:
        test_service.get_metadata_rows_from_file(
            file_key=test_file_key,
            bucket_name=MOCK_STAGING_STORE_BUCKET,
        )
    expected_log = f"File {test_file_key} doesn't exist"
    actual_log = caplog.records[-1].msg
    assert expected_log == actual_log
    assert str(exc_info.value) == "Failed to retrieve metadata"

    test_service.s3_service.file_exist_on_s3.assert_called_once_with(
        s3_bucket_name=MOCK_STAGING_STORE_BUCKET, file_key=test_file_key
    )
    test_service.s3_service.client.get_object.assert_not_called()


def test_move_original_metadata_file(test_service):
    file_key = "input/preprocessed/metadata.csv"
    expected_destination_key = (
        f"{test_service.practice_directory}"
        f"/{test_service.processed_folder_name}/{test_service.processed_date}/{METADATA_FILENAME}"
    )

    test_service.move_original_metadata_file(file_key)

    test_service.s3_service.copy_across_bucket.assert_called_once_with(
        MOCK_STAGING_STORE_BUCKET,
        file_key,
        MOCK_STAGING_STORE_BUCKET,
        expected_destination_key,
    )


def test_move_original_metadata_file_handles_exception(test_service):
    file_key = "input/preprocessed/metadata.csv"

    error_response = {"Error": {"Code": "NoSuchKey", "Message": "File not found"}}
    operation_name = "CopyObject"

    test_service.s3_service.copy_across_bucket.side_effect = ClientError(
        error_response, operation_name
    )

    result = test_service.move_original_metadata_file(file_key)

    assert result is False
    test_service.s3_service.copy_across_bucket.assert_called_once()


def test_update_record_filename_no_change_in_filename(test_service, mock_s3_client):
    original_row = {"FILEPATH": "/path/file1.pdf"}
    updated_row = {"FILEPATH": "test_practice_directory/path/file1.pdf"}

    actual_updated_row, actual_rejected_row, actual_rejected_reason = (
        test_service.update_record_filename(original_row, updated_row)
    )

    mock_s3_client.copy_object.assert_not_called()
    mock_s3_client.delete_object.assert_not_called()

    assert actual_updated_row == updated_row
    assert not actual_rejected_row
    assert not actual_rejected_reason


def test_update_record_filename_successful_update(test_service, mock_s3_client):
    original_row = {"FILEPATH": "/old/path/file1.pdf"}
    updated_row = {"FILEPATH": "/test_practice_directory/new/path/file1.pdf"}

    actual_updated_row, actual_rejected_row, actual_rejected_reason = (
        test_service.update_record_filename(original_row, updated_row)
    )

    mock_s3_client.copy_object.assert_called_once_with(
        Bucket=MOCK_STAGING_STORE_BUCKET,
        CopySource={
            "Bucket": MOCK_STAGING_STORE_BUCKET,
            "Key": f"{test_service.practice_directory}/old/path/file1.pdf",
        },
        Key=f"{test_service.practice_directory}/new/path/file1.pdf",
    )

    mock_s3_client.delete_object.assert_called_once_with(
        Bucket=MOCK_STAGING_STORE_BUCKET,
        Key=f"{test_service.practice_directory}/old/path/file1.pdf",
    )

    assert actual_updated_row == updated_row
    assert not actual_rejected_row
    assert not actual_rejected_reason


def test_update_record_filename_file_not_found_on_copy(test_service, mock_s3_client):
    original_row = {"FILEPATH": "/old/path/file1.pdf"}
    updated_row = {"FILEPATH": "/test_practice_directory/new/path/file1.pdf"}

    error_response = {"Error": {"Code": "NoSuchKey", "Message": "File not found"}}
    operation_name = "CopyObject"

    expected_rejection = {
        "FILEPATH": "/old/path/file1.pdf",
        "REASON": "File doesn't exist on S3",
    }

    mock_s3_client.copy_object.side_effect = ClientError(error_response, operation_name)

    actual_updated_row, actual_rejected_row, actual_rejected_reason = (
        test_service.update_record_filename(original_row, updated_row)
    )

    assert actual_updated_row is None
    assert actual_rejected_row == original_row
    assert actual_rejected_reason == expected_rejection

    mock_s3_client.copy_object.assert_called_once()
    mock_s3_client.delete_object.assert_not_called()


def test_update_record_filename_exception_on_copy(test_service, mock_s3_client):
    original_row = {"FILEPATH": "/old/path/file1.pdf"}
    updated_row = {"FILEPATH": "/test_practice_directory/new/path/file1.pdf"}

    expected_rejection = {
        "FILEPATH": "/old/path/file1.pdf",
        "REASON": "Failed to create updated S3 filepath",
    }

    mock_s3_client.copy_object.side_effect = MOCK_CLIENT_ERROR

    actual_updated_row, actual_rejected_row, actual_rejected_reason = (
        test_service.update_record_filename(original_row, updated_row)
    )

    assert actual_updated_row is None
    assert actual_rejected_row == original_row
    assert actual_rejected_reason == expected_rejection

    mock_s3_client.copy_object.assert_called_once()
    mock_s3_client.delete_object.assert_not_called()


def test_update_record_filename_exception_on_delete(test_service, mock_s3_client):
    original_row = {"FILEPATH": "/old/path/file1.pdf"}
    updated_row = {"FILEPATH": "/test_practice_directory/new/path/file1.pdf"}

    expected_rejection = {
        "FILEPATH": "/old/path/file1.pdf",
        "REASON": "Failed to remove old S3 filepath",
    }

    mock_s3_client.delete_object.side_effect = MOCK_CLIENT_ERROR

    actual_updated_row, actual_rejected_row, actual_rejected_reason = (
        test_service.update_record_filename(original_row, updated_row)
    )

    assert actual_updated_row is None
    assert actual_rejected_row == original_row
    assert actual_rejected_reason == expected_rejection

    mock_s3_client.copy_object.assert_called_once()
    mock_s3_client.delete_object.assert_called_once()


def test_update_and_standardize_filenames_success(test_service, mocker):
    original_row1 = {"FILEPATH": "/path/original1.pdf"}
    updated_row1 = {"FILEPATH": "/path/updated1.pdf"}

    original_row2 = {"FILEPATH": "/path/original2.pdf"}
    updated_row2 = {"FILEPATH": "/path/updated2.pdf"}

    renaming_map = [(original_row1, updated_row1), (original_row2, updated_row2)]

    mock_update = mocker.patch.object(
        test_service,
        "update_record_filename",
        side_effect=lambda orig, upd: (upd, None, None),  # Return the updated row
    )

    result = test_service.standardize_filenames(
        renaming_map=renaming_map, rejected_rows=[], rejected_reasons=[]
    )

    assert result == [updated_row1, updated_row2]
    assert mock_update.call_count == 2
    mock_update.assert_any_call(original_row1, updated_row1)
    mock_update.assert_any_call(original_row2, updated_row2)


def test_update_and_standardize_filenames_with_rejections(test_service, mocker):
    original_row1 = {"FILEPATH": "/path/original1.pdf"}
    updated_row1 = {"FILEPATH": "/path/updated1.pdf"}
    original_row2 = {"FILEPATH": "/path/original2.pdf"}
    updated_row2 = {"FILEPATH": "/path/updated2.pdf"}
    rejected_reason = {"REASON": "some reason"}

    renaming_map = [(original_row1, updated_row1), (original_row2, updated_row2)]

    mock_update = mocker.patch.object(
        test_service,
        "update_record_filename",
        side_effect=[
            (updated_row1, None, None),
            (None, original_row2, rejected_reason),
        ],
    )

    initial_rejected_rows = [{"FILEPATH": "initial_rejected.pdf"}]
    initial_rejected_reasons = [{"REASON": "initial_reason"}]

    result = test_service.standardize_filenames(
        renaming_map=renaming_map,
        rejected_rows=initial_rejected_rows,
        rejected_reasons=initial_rejected_reasons,
    )

    assert result == [updated_row1]
    assert mock_update.call_count == 2
    assert initial_rejected_rows == [
        {"FILEPATH": "initial_rejected.pdf"},
        original_row2,
    ]
    assert initial_rejected_reasons == [{"REASON": "initial_reason"}, rejected_reason]


def test_generate_renaming_map(test_service):
    metadata_rows = [
        {"FILEPATH": "file1.pdf", "SCAN-DATE": "01/01/2000", "UPLOAD": "10/10/2010"},
        {"FILEPATH": "file2.pdf", "SCAN-DATE": "01/01/2000", "UPLOAD": "10/10/2010"},
    ]

    renaming_map, rejected_rows, rejected_reasons = test_service.generate_renaming_map(
        metadata_rows
    )

    assert renaming_map == [
        (
            metadata_rows[0],
            {
                "FILEPATH": "test_practice_directory/file1.pdf",
                "SCAN-DATE": "01/01/2000",
                "UPLOAD": "10/10/2010",
            },
        ),
        (
            metadata_rows[1],
            {
                "FILEPATH": "test_practice_directory/file2.pdf",
                "SCAN-DATE": "01/01/2000",
                "UPLOAD": "10/10/2010",
            },
        ),
    ]
    assert rejected_rows == []
    assert rejected_reasons == []


def test_generate_renaming_map_happy_path(test_service, mock_update_date_in_row):
    row = {"FILEPATH": "valid_file.pdf"}

    metadata = [row]
    renaming_map, rejected_rows, rejected_reasons = test_service.generate_renaming_map(
        metadata
    )

    assert len(renaming_map) == 1
    assert renaming_map[0][0] == row
    assert (
        renaming_map[0][1]["FILEPATH"]
        == f"{test_service.practice_directory}/valid_file.pdf"
    )
    assert rejected_rows == []
    assert rejected_reasons == []


def test_generate_renaming_map_duplicate_file(test_service, mock_update_date_in_row):
    row1 = {"FILEPATH": "dup.pdf"}
    row2 = {"FILEPATH": "dup.pdf"}

    metadata = [row1, row2]
    renaming_map, rejected_rows, rejected_reasons = test_service.generate_renaming_map(
        metadata
    )

    assert len(renaming_map) == 1
    assert len(rejected_rows) == 1
    assert rejected_rows[0] == row2
    assert rejected_reasons[0]["REASON"] == "Duplicate filename after renaming"


def test_generate_renaming_map_invalid_filename(
    mocker, test_service, mock_update_date_in_row
):
    row = {"FILEPATH": "invalid_file.pdf"}

    mocker.patch.object(
        test_service,
        "validate_record_filename",
        side_effect=InvalidFileNameException("Bad format"),
    )

    metadata = [row]
    renaming_map, rejected_rows, rejected_reasons = test_service.generate_renaming_map(
        metadata
    )

    assert renaming_map == []
    assert rejected_rows == [row]
    assert rejected_reasons[0]["REASON"], "Bad format"


def test_generate_renaming_map_handles_empty_filename(
    test_service, mock_update_date_in_row
):
    metadata_rows = [{"FILEPATH": ""}]

    renaming_map, rejected_rows, rejected_reasons = test_service.generate_renaming_map(
        metadata_rows
    )

    assert renaming_map == []
    assert rejected_rows == [{"FILEPATH": ""}]
    assert rejected_reasons == [
        {
            "FILEPATH": "N/A",
            "REASON": "Filepath is missing",
        }
    ]


def test_update_date_in_row(test_service):
    metadata_row = {"SCAN-DATE": "2025.01.01", "UPLOAD": "2025.01.01"}

    updated_row = test_service.update_date_in_row(metadata_row)

    assert updated_row["SCAN-DATE"] == "2025/01/01"
    assert updated_row["UPLOAD"] == "2025/01/01"


def test_update_date_in_row_already_formatted(test_service):
    metadata_row = {"SCAN-DATE": "2025/01/01", "UPLOAD": "2025/01/01"}

    updated_row = test_service.update_date_in_row(metadata_row)

    assert updated_row["SCAN-DATE"] == "2025/01/01"
    assert updated_row["UPLOAD"] == "2025/01/01"


def test_generate_and_save_csv_file_updated_metadata(test_service, mocker):
    csv_dict = [
        {
            "FILEPATH": "01 of 02_Lloyd_George_Record_[Dwayne Basil COWIE]_[9730787506]_[18-09-1974].pdf",
            "GP-PRACTICE-CODE": "M85143",
        }
    ]
    file_key = "path/to/file.csv"
    expected_csv_data = b"col1,col2\nvalue1,value2\nvalue3,value4\n"
    mock_convert_csv = mocker.patch(
        "services.bulk_upload_metadata_preprocessor_service.convert_csv_dictionary_to_bytes",
        return_value=expected_csv_data,
    )

    mock_save_or_create_file = mocker.patch.object(
        test_service.s3_service, "save_or_create_file"
    )

    test_service.generate_and_save_csv_file(csv_dict, file_key)

    mock_convert_csv.assert_called_once_with(csv_dict[0].keys(), csv_dict)
    mock_save_or_create_file.assert_called_once()
