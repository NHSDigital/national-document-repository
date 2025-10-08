import json
import pytest
from enums.lambda_error import LambdaError
from handlers.update_document_reference_handler import lambda_handler
from tests.unit.conftest import MOCK_STAGING_STORE_BUCKET, TEST_NHS_NUMBER, TEST_UUID
from tests.unit.helpers.data.create_document_reference import LG_FILE_LIST, LG_MOCK_EVENT_BODY, LG_MOCK_RESPONSE
from utils.exceptions import InvalidNhsNumberException
from utils.lambda_exceptions import SearchPatientException, UpdateDocumentRefException
from utils.lambda_response import ApiGatewayResponse


TEST_DOCUMENT_LOCATION_ARF = f"s3://{MOCK_STAGING_STORE_BUCKET}/{TEST_UUID}"
TEST_DOCUMENT_LOCATION_LG = f"s3://{MOCK_STAGING_STORE_BUCKET}/{TEST_UUID}"

INVALID_NHS_NUMBER = "12345"

arf_environment_variables = ["STAGING_STORE_BUCKET_NAME"]
lg_environment_variables = ["LLOYD_GEORGE_BUCKET_NAME", "LLOYD_GEORGE_DYNAMODB_NAME"]

@pytest.fixture
def lg_type_event():
    return {
        "httpMethod": "PUT",
        "body": json.dumps(LG_MOCK_EVENT_BODY),
        "queryStringParameters": {"patientId": TEST_NHS_NUMBER},
    }

@pytest.fixture
def mock_processing_event_details(mocker):
    yield mocker.patch(
        "handlers.update_document_reference_handler.processing_event_details",
        return_value=(TEST_NHS_NUMBER, LG_FILE_LIST),
    )

@pytest.fixture
def mock_udr_service(mocker):
    mock_udrService = mocker.MagicMock()
    mocker.patch(
        "handlers.update_document_reference_handler.UpdateDocumentReferenceService",
        return_value=mock_udrService,
    )
    yield mock_udrService

@pytest.fixture
def mock_invalid_nhs_number_exception(mocker):
    mocker.patch(
        "utils.decorators.validate_patient_id.validate_nhs_number",
        side_effect=InvalidNhsNumberException(),
    )


def test_update_document_reference_valid_lg_type_returns_presigned_urls_and_200(
    set_env, lg_type_event, context, mock_udr_service, mock_upload_lambda_enabled, mock_add_document_enabled
):
    mock_udr_service.update_document_reference_request.return_value = LG_MOCK_RESPONSE
    expected = ApiGatewayResponse(
        200, json.dumps(LG_MOCK_RESPONSE), "PUT"
    ).create_api_gateway_response()
    actual = lambda_handler(lg_type_event, context)
    assert actual == expected

def test_update_document_reference_with_nhs_number_not_in_pds_returns_404(
    set_env, lg_type_event, context, mock_udr_service, mock_upload_lambda_enabled, mock_add_document_enabled
):
    mock_udr_service.update_document_reference_request.side_effect = (
        SearchPatientException(404, LambdaError.SearchPatientNoPDS)
    )

    expected_body = {
        "message": "Patient does not exist for given NHS number",
        "err_code": "SP_4002",
        "interaction_id": "88888888-4444-4444-4444-121212121212",
    }

    expected = ApiGatewayResponse(
        404, json.dumps(expected_body), "PUT"
    ).create_api_gateway_response()
    actual = lambda_handler(lg_type_event, context)
    assert actual == expected

def test_invalid_nhs_number_returns_400(
    set_env,
    lg_type_event,
    context,
    mock_invalid_nhs_number_exception,
    mock_processing_event_details,
    mock_udr_service,
):

    expected = ApiGatewayResponse(
        400,
        LambdaError.PatientIdInvalid.create_error_body({"number": TEST_NHS_NUMBER}),
        "PUT",
    ).create_api_gateway_response()
    actual = lambda_handler(lg_type_event, context)

    assert actual == expected

    mock_processing_event_details.assert_not_called()
    mock_udr_service.assert_not_called()

def test_no_event_processing_when_upload_lambda_flag_disabled(
    set_env,
    lg_type_event,
    context,
    mock_processing_event_details,
    mock_upload_lambda_disabled,
):
    expected_body = {
        "message": "Feature is not enabled",
        "err_code": "FFL_5003",
        "interaction_id": "88888888-4444-4444-4444-121212121212",
    }

    expected = ApiGatewayResponse(
        404, json.dumps(expected_body), "PUT"
    ).create_api_gateway_response()
    actual = lambda_handler(lg_type_event, context)

    assert expected == actual
    mock_processing_event_details.assert_not_called()

def test_no_event_processing_when_add_document_flag_disabled(
    set_env,
    lg_type_event,
    context,
    mock_processing_event_details,
    mock_upload_lambda_enabled,
    mock_add_document_disabled,
):
    expected_body = {
        "message": "Feature is not enabled",
        "err_code": "FFL_5003",
        "interaction_id": "88888888-4444-4444-4444-121212121212",
    }

    expected = ApiGatewayResponse(
        404, json.dumps(expected_body), "PUT"
    ).create_api_gateway_response()
    actual = lambda_handler(lg_type_event, context)

    assert expected == actual
    mock_processing_event_details.assert_not_called()

def test_ods_code_not_in_pilot_returns_404(
    set_env, context, lg_type_event, mock_udr_service, mock_upload_lambda_enabled, mock_add_document_enabled
):
    mock_udr_service.update_document_reference_request.side_effect = (
        UpdateDocumentRefException(404, LambdaError.CreateDocRefOdsCodeNotAllowed)
    )

    expected_body = {
        "message": "ODS code does not match any of the allowed.",
        "err_code": "CDR_4009",
        "interaction_id": "88888888-4444-4444-4444-121212121212",
    }

    expected = ApiGatewayResponse(
        404, json.dumps(expected_body), "PUT"
    ).create_api_gateway_response()
    actual = lambda_handler(lg_type_event, context)

    assert actual == expected

    mock_udr_service.update_document_reference_request.update_document_reference.assert_not_called()