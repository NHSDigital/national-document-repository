import json

from enums.logging_app_interaction import LoggingAppInteraction
from services.send_feedback_service import SendFeedbackService
from utils.audit_logging_setup import LoggingService
from utils.decorators.handle_lambda_exceptions import handle_lambda_exceptions
from utils.decorators.override_error_check import override_error_check
from utils.decorators.set_audit_arg import set_request_context_for_logging
from utils.lambda_response import ApiGatewayResponse
from utils.request_context import request_context

logger = LoggingService(__name__)


@set_request_context_for_logging
@override_error_check
@handle_lambda_exceptions
def lambda_handler(event, context):
    request_context.app_interaction = LoggingAppInteraction.SEND_FEEDBACK.value

    logger.info("Send feedback handler triggered")

    if not event["body"]:
        return ApiGatewayResponse(
            400, "Missing POST request body", "POST"
        ).create_api_gateway_response()

    feedback_service = SendFeedbackService()
    feedback_service.process_feedback(event["body"])

    logger.info("Processed Feedback email")

    return ApiGatewayResponse(
        200, "Feedback email processed", "POST"
    ).create_api_gateway_response()
