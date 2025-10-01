from datetime import datetime
from unittest import mock

import pytest
from botocore.exceptions import ClientError
from enums.trace_status import TraceStatus
from freezegun import freeze_time
from models.stitch_trace import StitchTrace
from services.lloyd_george_stitch_job_service import LloydGeorgeStitchJobService
from tests.unit.conftest import STITCH_METADATA_DYNAMODB_NAME_VALUE, TEST_NHS_NUMBER
from utils.exceptions import FileUploadInProgress, NoAvailableDocument
from utils.lambda_exceptions import LGStitchServiceException
from utils.lloyd_george_validator import LGInvalidFilesException

MOCK_STITCH_TRACE_OBJECT = StitchTrace(
    nhs_number=TEST_NHS_NUMBER, expire_at=9999999, job_status=TraceStatus.FAILED
)


@pytest.fixture
def stitch_service(set_env, mocker):
    mocker.patch("services.lloyd_george_stitch_job_service.S3Service")
    mocker.patch("services.lloyd_george_stitch_job_service.DocumentService")
    mocker.patch("services.lloyd_george_stitch_job_service.DynamoDBService")

    yield LloydGeorgeStitchJobService()


@pytest.fixture
def patch_service(mocker, stitch_service):
    stitch_service.check_lloyd_george_record_for_patient = mocker.MagicMock()
    stitch_service.query_stitch_trace_with_nhs_number = mocker.MagicMock()
    stitch_service.get_latest_stitch_trace = mocker.MagicMock()
    stitch_service.update_dynamo_with_new_stitch_trace = mocker.MagicMock()
    return stitch_service


def test_create_document_stitch_presigned_url(stitch_service, mocker):
    expected_url = "https://d12345.cloudfront.net/path/to/resource"

    stitch_service.s3_service.create_download_presigned_url.return_value = (
        "https://example.com/path/to/resource"
    )
    mocker.patch(
        "services.lloyd_george_stitch_job_service.format_cloudfront_url"
    ).return_value = "https://d12345.cloudfront.net/path/to/resource"

    stitched_file_location = "path/to/stitched/file"

    result = stitch_service.create_document_stitch_presigned_url(stitched_file_location)
    assert result == expected_url

    stitch_service.s3_service.create_download_presigned_url.assert_called_once_with(
        s3_bucket_name=stitch_service.lloyd_george_bucket_name,
        file_key=stitched_file_location,
    )


def test_check_lloyd_george_record_for_patient(stitch_service):
    stitch_service.check_lloyd_george_record_for_patient(TEST_NHS_NUMBER)
    stitch_service.document_service.get_available_lloyd_george_record_for_patient.assert_called_once_with(
        TEST_NHS_NUMBER
    )


def test_check_lloyd_george_record_for_patient_raise_client_error(stitch_service):
    stitch_service.document_service.get_available_lloyd_george_record_for_patient.side_effect = ClientError(
        {"Error": {"Code": "InternalError", "Message": "Internal error"}}, "GetRecord"
    )
    with pytest.raises(LGStitchServiceException) as exc_info:
        stitch_service.check_lloyd_george_record_for_patient(TEST_NHS_NUMBER)
    assert exc_info.value.status_code == 500


def test_check_lloyd_george_record_for_patient_when_files_upload_in_progress(
    stitch_service,
):
    stitch_service.document_service.get_available_lloyd_george_record_for_patient.side_effect = FileUploadInProgress(
        "Upload in progress"
    )
    with pytest.raises(LGStitchServiceException) as exc_info:
        stitch_service.check_lloyd_george_record_for_patient(TEST_NHS_NUMBER)
    assert exc_info.value.status_code == 423


def test_check_lloyd_george_record_for_patient_when_no_documents_found(stitch_service):
    stitch_service.document_service.get_available_lloyd_george_record_for_patient.side_effect = NoAvailableDocument(
        "No document available"
    )
    with pytest.raises(LGStitchServiceException) as exc_info:
        stitch_service.check_lloyd_george_record_for_patient(TEST_NHS_NUMBER)
    assert exc_info.value.status_code == 404


def test_check_lloyd_george_record_for_patient_when_invalid_files(stitch_service):
    stitch_service.document_service.get_available_lloyd_george_record_for_patient.side_effect = LGInvalidFilesException(
        "Invalid files"
    )
    with pytest.raises(LGStitchServiceException) as exc_info:
        stitch_service.check_lloyd_george_record_for_patient(TEST_NHS_NUMBER)
    assert exc_info.value.status_code == 400


def test_query_stitch_trace_with_nhs_number(stitch_service, mocker):
    mock_response = [
        {"NhsNumber": TEST_NHS_NUMBER, "Deleted": False, "Data": "Some data"},
        {"NhsNumber": TEST_NHS_NUMBER, "Deleted": False, "Data": "More data"},
    ]

    stitch_service.dynamo_service.query_table.return_value = mock_response

    stitch_service.validate_stitch_trace = mocker.MagicMock(return_value=mock_response)

    result = stitch_service.query_stitch_trace_with_nhs_number(TEST_NHS_NUMBER)
    assert result == mock_response

    stitch_service.dynamo_service.query_table.assert_called_once_with(
        table_name=STITCH_METADATA_DYNAMODB_NAME_VALUE,
        index_name="NhsNumberIndex",
        search_key="NhsNumber",
        search_condition=TEST_NHS_NUMBER,
        query_filter=mock.ANY,
    )


def test_create_stitch_job_no_trace_results(patch_service):
    patch_service.check_lloyd_george_record_for_patient.return_value = None
    patch_service.query_stitch_trace_with_nhs_number.return_value = None
    patch_service.update_dynamo_with_new_stitch_trace.return_value = TraceStatus.PENDING

    result = patch_service.get_or_create_stitch_job(TEST_NHS_NUMBER)

    patch_service.check_lloyd_george_record_for_patient.assert_called_once_with(
        TEST_NHS_NUMBER
    )
    patch_service.query_stitch_trace_with_nhs_number.assert_called_once_with(
        TEST_NHS_NUMBER
    )
    patch_service.update_dynamo_with_new_stitch_trace.assert_called_once_with(
        TEST_NHS_NUMBER
    )
    assert result == TraceStatus.PENDING


def test_create_stitch_job_failed_status(patch_service):
    patch_service.check_lloyd_george_record_for_patient.return_value = None
    patch_service.query_stitch_trace_with_nhs_number.return_value = [
        MOCK_STITCH_TRACE_OBJECT
    ]
    patch_service.get_latest_stitch_trace.return_value = MOCK_STITCH_TRACE_OBJECT
    patch_service.update_dynamo_with_new_stitch_trace.return_value = TraceStatus.PENDING

    result = patch_service.get_or_create_stitch_job(TEST_NHS_NUMBER)

    patch_service.check_lloyd_george_record_for_patient.assert_called_once_with(
        TEST_NHS_NUMBER
    )
    patch_service.query_stitch_trace_with_nhs_number.assert_called_once_with(
        TEST_NHS_NUMBER
    )
    patch_service.get_latest_stitch_trace.assert_called_once_with(
        [MOCK_STITCH_TRACE_OBJECT]
    )
    patch_service.update_dynamo_with_new_stitch_trace.assert_called_once_with(
        TEST_NHS_NUMBER
    )
    assert result == TraceStatus.PENDING


def test_create_stitch_job_success_status(patch_service):
    patch_service.check_lloyd_george_record_for_patient.return_value = None
    MOCK_STITCH_TRACE_OBJECT.job_status = TraceStatus.COMPLETED
    patch_service.query_stitch_trace_with_nhs_number.return_value = [
        MOCK_STITCH_TRACE_OBJECT
    ]
    patch_service.get_latest_stitch_trace.return_value = MOCK_STITCH_TRACE_OBJECT

    result = patch_service.get_or_create_stitch_job(TEST_NHS_NUMBER)

    patch_service.check_lloyd_george_record_for_patient.assert_called_once_with(
        TEST_NHS_NUMBER
    )
    patch_service.query_stitch_trace_with_nhs_number.assert_called_once_with(
        TEST_NHS_NUMBER
    )
    patch_service.get_latest_stitch_trace.assert_called_once_with(
        [MOCK_STITCH_TRACE_OBJECT]
    )
    assert result == TraceStatus.COMPLETED


def test_create_stitch_job_client_error(patch_service):
    patch_service.check_lloyd_george_record_for_patient.side_effect = ClientError(
        {"Error": {"Code": "InternalError", "Message": "Internal error"}}, "GetRecord"
    )

    with pytest.raises(LGStitchServiceException):
        patch_service.get_or_create_stitch_job(TEST_NHS_NUMBER)

    patch_service.check_lloyd_george_record_for_patient.assert_called_once_with(
        TEST_NHS_NUMBER
    )


def test_write_stitch_trace(stitch_service, mocker):
    stitch_service.get_expiration_time = mocker.MagicMock(return_value=1234567890)

    job_status = stitch_service.update_dynamo_with_new_stitch_trace(TEST_NHS_NUMBER)

    assert job_status == TraceStatus.PENDING
    stitch_service.dynamo_service.create_item.assert_called_once()


@freeze_time("2023-10-01 12:00:00")
def test_get_expiration_time(stitch_service):
    expiration_time = stitch_service.get_expiration_time()

    expected_expiration_time = int((datetime(2023, 10, 2, 1, 0, 0)).timestamp())

    assert expiration_time == expected_expiration_time


def test_query_document_stitch_job(stitch_service, mocker):

    mock_response = [
        {"NhsNumber": TEST_NHS_NUMBER, "Deleted": False, "Data": "Some data"}
    ]
    mock_latest_stitch_trace = mocker.MagicMock()

    stitch_service.query_stitch_trace_with_nhs_number = mocker.MagicMock(
        return_value=mock_response
    )
    stitch_service.get_latest_stitch_trace = mocker.MagicMock(
        return_value=mock_latest_stitch_trace
    )
    stitch_service.process_stitch_trace_response = mocker.MagicMock()

    stitch_service.query_document_stitch_job(TEST_NHS_NUMBER)

    stitch_service.query_stitch_trace_with_nhs_number.assert_called_once_with(
        nhs_number=TEST_NHS_NUMBER
    )
    stitch_service.get_latest_stitch_trace.assert_called_once_with(mock_response)
    stitch_service.process_stitch_trace_response.assert_called_once_with(
        mock_latest_stitch_trace
    )


def test_process_stitch_trace_response_failed(stitch_service, mocker):
    stitch_trace = mocker.MagicMock()
    stitch_trace.job_status = TraceStatus.FAILED

    with pytest.raises(LGStitchServiceException) as exc_info:
        stitch_service.process_stitch_trace_response(stitch_trace)

    assert exc_info.value.status_code == 500


def test_process_stitch_trace_response_pending(stitch_service, mocker):
    stitch_trace = mocker.MagicMock()

    stitch_trace.job_status = TraceStatus.PENDING

    result = stitch_service.process_stitch_trace_response(stitch_trace)
    assert result.job_status == TraceStatus.PENDING
    assert result.presigned_url == ""


def test_process_stitch_trace_response_processing(stitch_service, mocker):
    stitch_trace = mocker.MagicMock()

    stitch_trace.job_status = TraceStatus.PROCESSING

    result = stitch_service.process_stitch_trace_response(stitch_trace)
    assert result.job_status == TraceStatus.PROCESSING
    assert result.presigned_url == ""


def test_process_stitch_trace_response_completed(stitch_service, mocker):
    stitch_trace = mocker.MagicMock()

    stitch_trace.job_status = TraceStatus.COMPLETED
    stitch_trace.stitched_file_location = "path/to/stitched/file"
    stitch_trace.number_of_files = 2
    stitch_trace.file_last_updated = "2023-10-01T12:00:00Z"
    stitch_trace.total_file_size_in_bytes = 2048

    stitch_service.create_document_stitch_presigned_url = mocker.MagicMock(
        return_value="https://example.com/presigned-url"
    )

    result = stitch_service.process_stitch_trace_response(stitch_trace)

    assert result.job_status == TraceStatus.COMPLETED
    assert result.presigned_url == "https://example.com/presigned-url"
    assert result.number_of_files == 2
    assert result.last_updated == "2023-10-01T12:00:00Z"
    assert result.total_file_size_in_bytes == 2048


def test_validate_latest_stitch_trace_success(stitch_service):
    mock_stitch_trace_1 = StitchTrace(
        nhs_number=TEST_NHS_NUMBER,
        expire_at=111111111,
        job_status=TraceStatus.COMPLETED,
    )
    mock_stitch_trace_2 = StitchTrace(
        nhs_number=TEST_NHS_NUMBER, expire_at=222222222, job_status=TraceStatus.FAILED
    )

    mock_response = [
        mock_stitch_trace_1.model_dump(by_alias=True),
        mock_stitch_trace_2.model_dump(by_alias=True),
    ]

    result = stitch_service.validate_stitch_trace(mock_response)

    assert len(result) == 2
    assert result[0] == mock_stitch_trace_1
    assert result[1] == mock_stitch_trace_2


def test_validate_latest_stitch_trace_no_items(stitch_service):
    mock_response = []

    result = stitch_service.validate_stitch_trace(mock_response)
    assert result is None


def test_validate_latest_stitch_trace_validation_error(stitch_service):
    mock_response = {
        "Items": [
            {"NhsNumber": "1234567890", "job_status": "COMPLETED"},
        ]
    }

    with pytest.raises(LGStitchServiceException) as exc_info:
        stitch_service.validate_stitch_trace(mock_response)

    assert exc_info.value.status_code == 400


def test_get_latest_stitch_trace(stitch_service, mocker):
    stitch_trace_1 = StitchTrace(nhs_number="11111111", expire_at=123456)
    stitch_trace_1.created = (
        datetime(2023, 10, 1, 12, 0, 0).isoformat().replace("+00:00", "Z")
    )

    stitch_trace_2 = StitchTrace(nhs_number="222222222", expire_at=123456)
    stitch_trace_2.created = (
        datetime(2023, 10, 2, 12, 0, 0).isoformat().replace("+00:00", "Z")
    )

    stitch_trace_3 = StitchTrace(nhs_number="333333333", expire_at=123456)
    stitch_trace_3.created = (
        datetime(2023, 10, 1, 15, 0, 0).isoformat().replace("+00:00", "Z")
    )

    stitch_trace_items = [stitch_trace_1, stitch_trace_3, stitch_trace_2]

    latest_stitch_trace = stitch_service.get_latest_stitch_trace(stitch_trace_items)

    assert latest_stitch_trace == stitch_trace_2


def test_get_latest_stitch_trace_single_item(stitch_service, mocker):
    stitch_trace_1 = StitchTrace(nhs_number="11111111", expire_at=123456)
    stitch_trace_1.created = (
        datetime(2023, 10, 1, 12, 0, 0).isoformat().replace("+00:00", "Z")
    )

    latest_stitch_trace = stitch_service.get_latest_stitch_trace([stitch_trace_1])

    assert latest_stitch_trace == stitch_trace_1


def test_get_latest_stitch_trace_empty_list(stitch_service):
    with pytest.raises(IndexError):
        stitch_service.get_latest_stitch_trace([])
