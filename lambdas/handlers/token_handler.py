import json

from enums.logging_app_interaction import LoggingAppInteraction
from services.login_service import LoginService
from utils.audit_logging_setup import LoggingService
from utils.decorators.ensure_env_var import ensure_environment_variables
from utils.decorators.override_error_check import override_error_check
from utils.decorators.set_audit_arg import set_request_context_for_logging
from utils.exceptions import AuthorisationException
from utils.lambda_response import ApiGatewayResponse
from utils.request_context import request_context

logger = LoggingService(__name__)


@set_request_context_for_logging
@override_error_check
@ensure_environment_variables(
    names=["AUTH_STATE_TABLE_NAME", "AUTH_SESSION_TABLE_NAME"]
)
def lambda_handler(event, context):
    login_service = LoginService()

    request_context.app_interaction = LoggingAppInteraction.LOGIN.value

    missing_value_response_body = (
        "No auth code and/or state in the query string parameters"
    )

    try:
        auth_code = event["queryStringParameters"]["code"]
        state = event["queryStringParameters"]["state"]
        if not (auth_code and state):
            return respond_with(400, missing_value_response_body)
    except (KeyError, TypeError):
        return respond_with(400, missing_value_response_body)

    try:
        session_info = login_service.generate_session(state, auth_code)

        logger.info("Creating response")
        response = {
            "role": session_info["local_role"].value,
            "authorisation_token": session_info["jwt"],
        }

        logger.audit_splunk_info(
            "User logged in successfully", {"Result": "Successful login"}
        )
        return respond_with(200, json.dumps(response))

    except AuthorisationException as error:
        logger.error(error, {"Result": "Unauthorised"})
        return respond_with(error.status_code, error.message)


def respond_with(http_status_code, body):
    return ApiGatewayResponse(
        http_status_code, body, "GET"
    ).create_api_gateway_response()
