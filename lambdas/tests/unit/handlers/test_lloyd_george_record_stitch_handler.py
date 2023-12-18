import json
import tempfile

import pypdf.errors
import pytest
from botocore.exceptions import ClientError
from handlers.lloyd_george_record_stitch_handler import lambda_handler
from services.document_service import DocumentService
from services.lloyd_george_stitch_service import LloydGeorgeStitchService
from services.s3_service import S3Service
from tests.unit.conftest import MOCK_LG_BUCKET, TEST_NHS_NUMBER
from tests.unit.helpers.data.test_documents import (
    create_test_lloyd_george_doc_store_refs,
)
from utils.lambda_response import ApiGatewayResponse


def test_respond_200_with_presign_url(
    valid_id_event_without_auth_header,
    context,
    set_env,
    fetch_available_document_references_by_type,
    mock_s3,
    mock_stitch_pdf,
    mock_get_total_file_size,
):
    actual = lambda_handler(valid_id_event_without_auth_header, context)

    expected_response_object = {
        "number_of_files": 3,
        "last_updated": "2023-08-24T14:38:04.095Z",
        "presign_url": MOCK_PRESIGNED_URL,
        "total_file_size_in_byte": MOCK_TOTAL_FILE_SIZE,
    }
    expected = ApiGatewayResponse(
        200, json.dumps(expected_response_object), "GET"
    ).create_api_gateway_response()

    assert actual == expected


def test_aws_services_are_correctly_called(
    joe_bloggs_event,
    context,
    set_env,
    fetch_available_document_references_by_type,
    mock_s3,
    mock_stitch_pdf,
    mock_tempfile,
    mock_get_total_file_size,
):
    lambda_handler(joe_bloggs_event, context)

    fetch_available_document_references_by_type.assert_called_once()

    assert mock_s3.download_file.call_count == len(MOCK_LLOYD_GEORGE_DOCUMENT_REFS)
    mock_s3.upload_file_with_extra_args.assert_called_with(
        file_key="9000000009/Combined_Lloyd_George_Record_[Joe Bloggs]_[9000000009]_[30-12-2019].pdf",
        file_name=MOCK_STITCHED_FILE,
        s3_bucket_name=MOCK_LG_BUCKET,
        extra_args={
            "Tagging": "autodelete=true",
            "ContentDisposition": "inline",
            "ContentType": "application/pdf",
        },
    )


def test_respond_400_throws_error_when_no_nhs_number_supplied(
    missing_id_event, context
):
    actual = lambda_handler(missing_id_event, context)
    expected = ApiGatewayResponse(
        400, "An error occurred due to missing key: 'patientId'", "GET"
    ).create_api_gateway_response()
    assert actual == expected


def test_respond_500_throws_error_when_environment_variables_not_set(
    joe_bloggs_event, context
):
    actual = lambda_handler(joe_bloggs_event, context)
    expected = ApiGatewayResponse(
        500,
        "An error occurred due to missing environment variable: 'LLOYD_GEORGE_DYNAMODB_NAME'",
        "GET",
    ).create_api_gateway_response()
    assert actual == expected


def test_respond_400_throws_error_when_nhs_number_not_valid(invalid_id_event, context):
    actual = lambda_handler(invalid_id_event, context)
    expected = ApiGatewayResponse(
        400, "Invalid NHS number", "GET"
    ).create_api_gateway_response()
    assert actual == expected


def test_respond_500_throws_error_when_failed_to_retrieve_lg_record(
    joe_bloggs_event, context, set_env, fetch_available_document_references_by_type
):
    fetch_available_document_references_by_type.side_effect = MOCK_CLIENT_ERROR
    actual = lambda_handler(joe_bloggs_event, context)
    expected = ApiGatewayResponse(
        500, "Unable to retrieve documents for patient 9000000009", "GET"
    ).create_api_gateway_response()
    assert actual == expected


def test_respond_500_throws_error_when_fail_to_download_lloyd_george_file(
    joe_bloggs_event,
    context,
    set_env,
    fetch_available_document_references_by_type,
    mock_s3,
):
    mock_s3.download_file.side_effect = MOCK_CLIENT_ERROR
    actual = lambda_handler(joe_bloggs_event, context)
    expected = ApiGatewayResponse(
        500, "Unable to retrieve documents for patient 9000000009", "GET"
    ).create_api_gateway_response()
    assert actual == expected


def test_respond_404_throws_error_when_no_lloyd_george_for_patient_in_record(
    valid_id_event_without_auth_header,
    context,
    set_env,
    fetch_available_document_references_by_type,
):
    fetch_available_document_references_by_type.return_value = []
    actual = lambda_handler(valid_id_event_without_auth_header, context)
    expected = ApiGatewayResponse(
        404, "Lloyd george record not found for patient 9000000009", "GET"
    ).create_api_gateway_response()
    assert actual == expected


def test_respond_500_throws_error_when_fail_to_stitch_lloyd_george_file(
    valid_id_event_without_auth_header,
    context,
    set_env,
    fetch_available_document_references_by_type,
    mock_s3,
    mock_stitch_pdf,
):
    mock_stitch_pdf.side_effect = pypdf.errors.ParseError

    actual = lambda_handler(valid_id_event_without_auth_header, context)
    expected = ApiGatewayResponse(
        500, "Unable to return stitched pdf file due to internal error", "GET"
    ).create_api_gateway_response()
    assert actual == expected


def test_respond_500_throws_error_when_fail_to_upload_lloyd_george_file(
    joe_bloggs_event,
    context,
    set_env,
    fetch_available_document_references_by_type,
    mock_s3,
    mock_stitch_pdf,
):
    mock_s3.upload_file_with_extra_args.side_effect = MOCK_CLIENT_ERROR
    actual = lambda_handler(joe_bloggs_event, context)
    expected = ApiGatewayResponse(
        500, "Unable to return stitched pdf file due to internal error", "GET"
    ).create_api_gateway_response()
    assert actual == expected


MOCK_CLIENT_ERROR = ClientError(
    {"Error": {"Code": "500", "Message": "test error"}}, "testing"
)
MOCK_LG_DYNAMODB_RESPONSE_NO_RECORD = {"Items": [], "Count": 0}
MOCK_LLOYD_GEORGE_DOCUMENT_REFS = create_test_lloyd_george_doc_store_refs()
MOCK_STITCHED_FILE = "filename_of_stitched_lg_in_local_storage.pdf"
MOCK_TOTAL_FILE_SIZE = 1024 * 256
MOCK_PRESIGNED_URL = (
    f"https://{MOCK_LG_BUCKET}.s3.amazonaws.com/{TEST_NHS_NUMBER}/abcd-1234-5678"
)


@pytest.fixture
def fetch_available_document_references_by_type(mocker):
    mocked_method = mocker.patch.object(
        DocumentService, "fetch_available_document_references_by_type"
    )
    mocked_method.return_value = MOCK_LLOYD_GEORGE_DOCUMENT_REFS
    yield mocked_method


@pytest.fixture
def mock_s3(mocker):
    mocked_instance = mocker.patch(
        "services.lloyd_george_stitch_service.S3Service", spec=S3Service
    ).return_value
    # mocked_instance.download_file.return_value =
    mocked_instance.create_download_presigned_url.return_value = MOCK_PRESIGNED_URL
    yield mocked_instance


@pytest.fixture
def mock_stitch_pdf(mocker):
    yield mocker.patch(
        "services.lloyd_george_stitch_service.stitch_pdf",
        return_value=MOCK_STITCHED_FILE,
    )


@pytest.fixture
def mock_tempfile(mocker):
    yield mocker.patch.object(tempfile, "mkdtemp", return_value="/tmp/")


@pytest.fixture
def joe_bloggs_event():
    api_gateway_proxy_event = {
        "httpMethod": "GET",
        "queryStringParameters": {"patientId": "9000000009"},
    }
    return api_gateway_proxy_event


@pytest.fixture
def mock_get_total_file_size(mocker):
    yield mocker.patch.object(
        LloydGeorgeStitchService,
        "get_total_file_size",
        return_value=MOCK_TOTAL_FILE_SIZE,
    )
