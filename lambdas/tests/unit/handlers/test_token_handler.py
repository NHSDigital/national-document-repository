import json

import pytest
from enums.repository_role import RepositoryRole
from handlers.token_handler import lambda_handler
from services.login_service import LoginService
from utils.audit_logging_setup import LoggingService
from utils.exceptions import AuthorisationException
from utils.lambda_response import ApiGatewayResponse


@pytest.fixture
def mock_login_service(mocker):
    mock_service = mocker.patch("handlers.token_handler.LoginService")
    yield mock_service.return_value



@pytest.fixture
def mock_logging_service(mocker):
    yield mocker.patch.object(LoggingService, "__init__", return_value=None)


def test_lambda_handler_respond_with_200_including_org_info_and_auth_token(
    set_env,
    mock_logging_service,
    mock_login_service,
    mocker,
    context,
):
    expected_jwt = "mock_ndr_auth_token"
    login_service_response = {"local_role": RepositoryRole.PCSE, "jwt": expected_jwt}
    mock_login_service.generate_session.return_value = login_service_response

    auth_code = "auth_code"
    state = "test_state"
    test_event = {
        "queryStringParameters": {"code": auth_code, "state": state},
        "httpmethod": "GET",
    }

    expected_response_body = {
        "role": "PCSE",
        "authorisation_token": expected_jwt,
    }

    expected = ApiGatewayResponse(
        200, json.dumps(expected_response_body), "GET"
    ).create_api_gateway_response()

    actual = lambda_handler(test_event, context)

    assert actual == expected

    mock_login_service["exchange_token"].expect_called_with(auth_code, state)


def test_handler_passes_error_details_in_response(
    set_env,
    mock_logging_service,
    mock_login_service,
    mocker,
    context,
):
    expected_status = 400
    expected_body = "Error desc"
    exception = AuthorisationException(
        status_code=expected_status, message=expected_body
    )
    mock_login_service.generate_session.side_effect = exception

    auth_code = "auth_code"
    state = "test_state"
    test_event = {
        "queryStringParameters": {"code": auth_code, "state": state},
        "httpmethod": "GET",
    }

    expected = ApiGatewayResponse(
        expected_status, json.dumps(expected_body), "GET"
    ).create_api_gateway_response()

    actual = lambda_handler(test_event, context)

    assert actual == expected

    mock_login_service["exchange_token"].expect_called_with(auth_code, state)


# TODO Test errors including autherrors (return 401) and erroneous errors (e.g. encoding, keyerrors (return 500)
