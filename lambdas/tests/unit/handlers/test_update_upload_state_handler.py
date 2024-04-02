import json
from enum import Enum

import pytest
from handlers.update_upload_state_handler import lambda_handler
from tests.unit.helpers.data.update_upload_state import (
    MOCK_INVALID_ALL_EVENT,
    MOCK_INVALID_BODY_EVENT,
    MOCK_NO_BODY_EVENT,
    MOCK_VALID_ARF_EVENT,
    MOCK_VALID_LG_EVENT,
)
from utils.lambda_response import ApiGatewayResponse


class MockError(Enum):
    Error = {
        "message": "Client error",
        "err_code": "AB_XXXX",
        "interaction_id": "88888888-4444-4444-4444-121212121212",
    }


@pytest.fixture
def mock_update_upload_state_service(mocker):
    mocked_class = mocker.patch(
        "handlers.update_upload_state_handler.UpdateUploadStateService"
    )
    mocker.patch.object(mocked_class, "handle_update_state")
    mocked_instance = mocked_class.return_value
    yield mocked_instance


def test_update_upload_state_handler_success_lg(
    set_env, context, mock_update_upload_state_service
):
    expected = ApiGatewayResponse(
        200, "Update upload state successful", "POST"
    ).create_api_gateway_response()

    actual = lambda_handler(MOCK_VALID_LG_EVENT, context)

    assert expected == actual


def test_update_upload_state_handler_success_arf(
    set_env, context, mock_update_upload_state_service
):
    expected = ApiGatewayResponse(
        200, "Update upload state successful", "POST"
    ).create_api_gateway_response()

    actual = lambda_handler(MOCK_VALID_ARF_EVENT, context)

    assert expected == actual


def test_update_upload_state_handler_both_doc_types_raise_error(set_env, context):

    expected_body = {
        "message": "Doctype invalid",
        "err_code": "US_4003",
        "interaction_id": "88888888-4444-4444-4444-121212121212",
    }
    expected = ApiGatewayResponse(
        404, json.dumps(expected_body), "POST"
    ).create_api_gateway_response()

    actual = lambda_handler(MOCK_INVALID_ALL_EVENT, context)

    assert expected == actual


arf_environment_variables = [
    "DOCUMENT_STORE_DYNAMODB_NAME",
]
lg_environment_variables = ["LLOYD_GEORGE_DYNAMODB_NAME"]


@pytest.mark.parametrize("environment_variable", lg_environment_variables)
def test_lambda_handler_missing_environment_variables_type_lg_returns_500(
    set_env,
    monkeypatch,
    environment_variable,
    context,
):
    monkeypatch.delenv(environment_variable)

    expected_body = {
        "message": f"An error occurred due to missing environment variable: '{environment_variable}'",
        "err_code": "ENV_5001",
        "interaction_id": "88888888-4444-4444-4444-121212121212",
    }
    expected = ApiGatewayResponse(
        500,
        json.dumps(expected_body),
        "POST",
    ).create_api_gateway_response()
    actual = lambda_handler(MOCK_VALID_LG_EVENT, context)
    assert expected == actual


@pytest.mark.parametrize("environment_variable", arf_environment_variables)
def test_lambda_handler_missing_environment_variables_type_arf_returns_500(
    set_env,
    monkeypatch,
    environment_variable,
    context,
):
    monkeypatch.delenv(environment_variable)

    expected_body = {
        "message": f"An error occurred due to missing environment variable: '{environment_variable}'",
        "err_code": "ENV_5001",
        "interaction_id": "88888888-4444-4444-4444-121212121212",
    }
    expected = ApiGatewayResponse(
        500,
        json.dumps(expected_body),
        "POST",
    ).create_api_gateway_response()
    actual = lambda_handler(MOCK_VALID_ARF_EVENT, context)
    assert expected == actual


def test_lambda_handler_invalid_body_raises_exception(set_env, context):
    expected_body = {
        "message": "Invalid request body",
        "err_code": "US_4005",
        "interaction_id": "88888888-4444-4444-4444-121212121212",
    }
    expected = ApiGatewayResponse(
        400,
        json.dumps(expected_body),
        "POST",
    ).create_api_gateway_response()
    actual = lambda_handler(MOCK_INVALID_BODY_EVENT, context)
    assert expected == actual


def test_lambda_handler_missing_body_raises_exception(set_env, context):
    expected_body = {
        "message": "Missing request body",
        "err_code": "US_4001",
        "interaction_id": "88888888-4444-4444-4444-121212121212",
    }
    expected = ApiGatewayResponse(
        400,
        json.dumps(expected_body),
        "POST",
    ).create_api_gateway_response()
    actual = lambda_handler(MOCK_NO_BODY_EVENT, context)
    assert expected == actual
