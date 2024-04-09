import json
from enum import Enum

import pytest
from enums.lambda_error import LambdaError
from enums.repository_role import RepositoryRole
from handlers.token_handler import lambda_handler
from utils.lambda_exceptions import LoginException
from utils.lambda_response import ApiGatewayResponse


class MockError(Enum):
    Error = {
        "message": "Client error",
        "err_code": "AB_XXXX",
        "interaction_id": "88888888-4444-4444-4444-121212121212",
    }


@pytest.fixture
def mock_configuration_service(mocker):
    mock_service = mocker.patch("handlers.token_handler.DynamicConfigurationService")
    yield mock_service


@pytest.fixture
def mock_login_service(mocker, set_env):
    mock_service = mocker.patch("handlers.token_handler.LoginService")
    yield mock_service.return_value


def test_lambda_handler_respond_with_200_including_org_info_and_auth_token(
    mock_login_service, context, mock_configuration_service
):
    expected_jwt = "mock_ndr_auth_token"
    login_service_response = {
        "isBSOL": False,
        "role": RepositoryRole.PCSE.value,
        "authorisation_token": expected_jwt,
    }
    mock_login_service.generate_session.return_value = login_service_response

    auth_code = "auth_code"
    state = "test_state"
    test_event = {
        "queryStringParameters": {"code": auth_code, "state": state},
        "httpmethod": "GET",
    }

    expected_response_body = {
        "isBSOL": False,
        "role": "PCSE",
        "authorisation_token": expected_jwt,
    }
    expected = ApiGatewayResponse(
        200, json.dumps(expected_response_body), "GET"
    ).create_api_gateway_response()

    actual = lambda_handler(test_event, context)

    assert actual == expected

    mock_login_service.generate_session.assert_called_with(state, auth_code)


def test_handler_passes_error_details_in_response(
    mock_configuration_service,
    mock_login_service,
    context,
):
    expected_status = 400
    expected_body = json.dumps(MockError.Error.value)
    exception = LoginException(status_code=expected_status, error=LambdaError.MockError)
    mock_login_service.generate_session.side_effect = exception

    auth_code = "auth_code"
    state = "test_state"
    test_event = {
        "queryStringParameters": {"code": auth_code, "state": state},
        "httpmethod": "GET",
    }

    expected = ApiGatewayResponse(
        expected_status,
        expected_body,
        "GET",
    ).create_api_gateway_response()

    actual = lambda_handler(test_event, context)

    assert actual == expected

    mock_login_service.generate_session.assert_called_with(state, auth_code)


def test_missing_query_string_params_raise_key_error(
    mock_configuration_service, mock_login_service, context
):
    expected_status = 400
    expected_body = json.dumps(
        {
            "message": "No auth err_code and/or state in the query string parameters",
            "err_code": "LIN_4007",
            "interaction_id": "88888888-4444-4444-4444-121212121212",
        }
    )

    auth_code = "auth_code"
    test_event = {
        "queryStringParameters": {"test": auth_code},
        "httpmethod": "GET",
    }

    expected = ApiGatewayResponse(
        expected_status,
        expected_body,
        "GET",
    ).create_api_gateway_response()

    actual = lambda_handler(test_event, context)

    assert actual == expected

    mock_login_service.generate_session.assert_not_called()


def test_missing_query_string_params_raise_login_error(
    mock_configuration_service,
    mock_login_service,
    context,
):
    expected_status = 400
    expected_body = json.dumps(
        {
            "message": "No auth err_code and/or state in the query string parameters",
            "err_code": "LIN_4001",
            "interaction_id": "88888888-4444-4444-4444-121212121212",
        }
    )

    test_event = {
        "queryStringParameters": {"code": "", "state": ""},
        "httpmethod": "GET",
    }
    expected = ApiGatewayResponse(
        expected_status,
        expected_body,
        "GET",
    ).create_api_gateway_response()

    actual = lambda_handler(test_event, context)

    assert actual == expected
    mock_login_service.generate_session.assert_not_called()
