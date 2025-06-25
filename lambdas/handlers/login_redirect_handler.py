from enums.logging_app_interaction import LoggingAppInteraction
from services.dynamic_configuration_service import DynamicConfigurationService
from services.login_redirect_service import LoginRedirectService
from services.mock_login_redirect_service import MockLoginRedirectService
from utils.audit_logging_setup import LoggingService
from utils.decorators.ensure_env_var import ensure_environment_variables
from utils.decorators.handle_lambda_exceptions import handle_lambda_exceptions
from utils.decorators.override_error_check import override_error_check
from utils.decorators.set_audit_arg import set_request_context_for_logging
from utils.lambda_response import ApiGatewayResponse
from utils.request_context import request_context

logger = LoggingService(__name__)


@set_request_context_for_logging
@override_error_check
@ensure_environment_variables(
    names=[
        "AUTH_DYNAMODB_NAME",
        "APPCONFIG_APPLICATION",
        "APPCONFIG_CONFIGURATION",
        "APPCONFIG_ENVIRONMENT",
        "OIDC_CALLBACK_URL",
    ]
)
@handle_lambda_exceptions
def lambda_handler(event, context):
    request_context.app_interaction = LoggingAppInteraction.LOGIN.value
    logger.info("Login Redirect handler triggered")

    configuration_service = DynamicConfigurationService()
    configuration_service.set_auth_ssm_prefix()
    if getattr(request_context, "auth_ssm_prefix") == "/auth/mock/":
        mock_login_redirect_service = MockLoginRedirectService()
        location_header = mock_login_redirect_service.prepare_redirect_response(event)
        return ApiGatewayResponse(303, "", "GET").create_api_gateway_response(
            headers=location_header
        )

    login_redirect_service = LoginRedirectService()
    location_header = login_redirect_service.prepare_redirect_response()
    return ApiGatewayResponse(303, "", "GET").create_api_gateway_response(
        headers=location_header
    )
