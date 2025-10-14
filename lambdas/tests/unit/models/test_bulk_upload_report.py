from enums.patient_ods_inactive_status import PatientOdsInactiveStatus
from enums.upload_status import UploadStatus
from freezegun import freeze_time
from models.report.bulk_upload_report import BulkUploadReport
from tests.unit.conftest import TEST_UUID

MOCK_DATA_COMPLETE_UPLOAD = {
    "ID": TEST_UUID,
    "NhsNumber": "9000000009",
    "Timestamp": 1698661500,
    "Date": "2023-10-30",
    "UploadStatus": "complete",
    "FilePath": "/9000000009/1of1_Lloyd_George_Record_[Joe Bloggs]_[9000000009]_[25-12-2019].pdf",
    "StoredFileName": "/9000000009/1of1_Lloyd_George_Record_[Joe Bloggs]_[9000000009]_[25-12-2019].pdf",
    "PdsOdsCode": "Y12345",
    "UploaderOdsCode": "Y12345",
}

MOCK_REASON = "File name not matching Lloyd George naming convention"
MOCK_DATA_FAILED_UPLOAD = {
    "ID": TEST_UUID,
    "NhsNumber": "9000000025",
    "Timestamp": 1698661500,
    "Date": "2023-10-30",
    "UploadStatus": "failed",
    "Reason": MOCK_REASON,
    "FilePath": "/9000000025/invalid_filename.pdf",
    "StoredFileName": "/9000000025/invalid_filename.pdf",
    "PdsOdsCode": "",
    "UploaderOdsCode": "Y12345",
}

mock_report = BulkUploadReport(
    ID=TEST_UUID,
    nhs_number="9000000009",
    timestamp=1698661500,
    date="2023-10-30",
    upload_status=UploadStatus.COMPLETE,
    file_path="/9000000009/1of1_Lloyd_George_Record_[Joe Bloggs]_[9000000009]_[25-12-2019].pdf",
    pds_ods_code="Y12345",
    uploader_ods_code="Y12345",
)


def test_create_successful_upload():
    expected = MOCK_DATA_COMPLETE_UPLOAD
    expected.update({"Reason": ""})

    actual = BulkUploadReport(
        ID=TEST_UUID,
        nhs_number="9000000009",
        timestamp=1698661500,
        date="2023-10-30",
        upload_status=UploadStatus.COMPLETE,
        file_path="/9000000009/1of1_Lloyd_George_Record_[Joe Bloggs]_[9000000009]_[25-12-2019].pdf",
        stored_file_name="/9000000009/1of1_Lloyd_George_Record_[Joe Bloggs]_[9000000009]_[25-12-2019].pdf",
        pds_ods_code="Y12345",
        uploader_ods_code="Y12345",
    ).model_dump(by_alias=True, exclude_none=True)

    assert actual == expected


def test_create_failed_upload():
    expected = MOCK_DATA_FAILED_UPLOAD
    actual = BulkUploadReport(
        ID=TEST_UUID,
        nhs_number="9000000025",
        timestamp=1698661500,
        date="2023-10-30",
        upload_status=UploadStatus.FAILED,
        reason=MOCK_REASON,
        file_path="/9000000025/invalid_filename.pdf",
        stored_file_name="/9000000025/invalid_filename.pdf",
        pds_ods_code="",
        uploader_ods_code="Y12345",
    ).model_dump(by_alias=True, exclude_none=True)

    assert actual == expected


@freeze_time("2023-10-30 10:25:00")
def test_successful_upload_ids_and_timestamp_are_auto_populated_if_not_given(mock_uuid):
    expected = MOCK_DATA_COMPLETE_UPLOAD
    expected.update({"Reason": ""})

    actual = BulkUploadReport(
        nhs_number="9000000009",
        file_path="/9000000009/1of1_Lloyd_George_Record_[Joe Bloggs]_[9000000009]_[25-12-2019].pdf",
        stored_file_name="/9000000009/1of1_Lloyd_George_Record_[Joe Bloggs]_[9000000009]_[25-12-2019].pdf",
        pds_ods_code="Y12345",
        uploader_ods_code="Y12345",
        upload_status=UploadStatus.COMPLETE,
    ).model_dump(by_alias=True, exclude_none=True)

    assert actual == expected


@freeze_time("2023-10-30 10:25:00")
def test_failed_upload_ids_and_timestamp_are_auto_populated_if_not_given(mock_uuid):
    expected = MOCK_DATA_FAILED_UPLOAD
    actual = BulkUploadReport(
        nhs_number="9000000025",
        file_path="/9000000025/invalid_filename.pdf",
        stored_file_name="/9000000025/invalid_filename.pdf",
        reason=MOCK_REASON,
        pds_ods_code="",
        uploader_ods_code="Y12345",
        upload_status=UploadStatus.FAILED,
    ).model_dump(by_alias=True, exclude_none=True)

    assert actual == expected


def test_get_registered_at_uploader_status_returns_true_uploader_ods_and_pds_ods_are_the_same():
    assert mock_report.get_registered_at_uploader_practice_status() == "True"


def test_get_registered_at_uploader_status_returns_false_uploader_ods_and_pds_ods_are_different():
    mock_report.uploader_ods_code = "Z12345"

    assert mock_report.get_registered_at_uploader_practice_status() == "False"


def test_get_registered_at_uploader_status_returns_correct_status():
    for status in PatientOdsInactiveStatus.list():
        mock_report.pds_ods_code = status
        assert mock_report.get_registered_at_uploader_practice_status() == status
