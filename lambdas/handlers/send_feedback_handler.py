from enums.lambda_error import LambdaError
from enums.logging_app_interaction import LoggingAppInteraction
from services.send_feedback_service import SendFeedbackService
from utils.audit_logging_setup import LoggingService
from utils.decorators.ensure_env_var import ensure_environment_variables
from utils.decorators.handle_lambda_exceptions import handle_lambda_exceptions
from utils.decorators.override_error_check import override_error_check
from utils.decorators.set_audit_arg import set_request_context_for_logging
from utils.lambda_exceptions import SendFeedbackException
from utils.lambda_response import ApiGatewayResponse
from utils.request_context import request_context

logger = LoggingService(__name__)


@set_request_context_for_logging
@override_error_check
@ensure_environment_variables(
    [
        "FROM_EMAIL_ADDRESS",
        "EMAIL_SUBJECT",
        "EMAIL_RECIPIENT_SSM_PARAM_KEY",
        "ITOC_TESTING_SLACK_BOT_TOKEN",
        "ITOC_TESTING_CHANNEL_ID",
        "ITOC_TESTING_EMAIL_ADDRESS",
        "ITOC_TESTING_TEAMS_WEBHOOK"
    ]
)
@handle_lambda_exceptions
def lambda_handler(event, context):
    request_context.app_interaction = LoggingAppInteraction.SEND_FEEDBACK.value

    logger.info("Send feedback handler triggered")

    event_body = event.get("body")
    if not event_body:
        logger.error(
            LambdaError.FeedbackMissingBody.to_str(),
            {"Result": "Failed to send feedback by email"},
        )
        raise SendFeedbackException(400, LambdaError.FeedbackMissingBody)

    logger.info("Setting up SendFeedbackService...")
    feedback_service = SendFeedbackService()

    logger.info("SendFeedbackService ready, start processing feedback")
    feedback_service.process_feedback(event_body)

    logger.info("Process complete", {"Result": "Successfully sent feedback by email"})

    return ApiGatewayResponse(
        200, "Feedback email processed", "POST"
    ).create_api_gateway_response()
