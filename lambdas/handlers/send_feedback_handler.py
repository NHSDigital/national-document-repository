import os

from enums.lambda_error import LambdaError
from enums.logging_app_interaction import LoggingAppInteraction
from models.feedback_model import Feedback
from pydantic import ValidationError
from services.send_feedback_service import SendFeedbackService
from services.send_test_feedback_service import SendTestFeedbackService
from utils.audit_logging_setup import LoggingService
from utils.decorators.ensure_env_var import ensure_environment_variables
from utils.decorators.handle_lambda_exceptions import handle_lambda_exceptions
from utils.decorators.override_error_check import override_error_check
from utils.decorators.set_audit_arg import set_request_context_for_logging
from utils.exceptions import OdsErrorException
from utils.lambda_exceptions import SendFeedbackException
from utils.lambda_response import ApiGatewayResponse
from utils.request_context import request_context

logger = LoggingService(__name__)
failure_msg = "Failed to send feedback by email"


@set_request_context_for_logging
@override_error_check
@ensure_environment_variables(
    [
        "FROM_EMAIL_ADDRESS",
        "EMAIL_SUBJECT",
        "EMAIL_RECIPIENT_SSM_PARAM_KEY",
        "ITOC_TESTING_SLACK_BOT_TOKEN",
        "ITOC_TESTING_CHANNEL_ID",
        "ITOC_TESTING_TEAMS_WEBHOOK",
        "ITOC_TESTING_ODS_CODES",
    ]
)
@handle_lambda_exceptions
def lambda_handler(event, context):
    request_context.app_interaction = LoggingAppInteraction.SEND_FEEDBACK.value
    ods_code = request_context.authorization.get("selected_organisation", {}).get(
        "org_ods_code"
    )
    if not ods_code:
        raise OdsErrorException("No ODS code provided")

    logger.info("Send feedback handler triggered")

    event_body = event.get("body")
    if not event_body:
        logger.error(
            LambdaError.FeedbackMissingBody.to_str(),
            {"Result": "Failed to send feedback by email"},
        )
        raise SendFeedbackException(400, LambdaError.FeedbackMissingBody)

    logger.info("Parsing feedback content...")
    try:
        feedback = Feedback.model_validate_json(event_body)

    except ValidationError as e:
        logger.error(e)
        logger.error(
            LambdaError.FeedbackInvalidBody.to_str(),
            {"result": failure_msg},
        )
        raise SendFeedbackException(400, LambdaError.FeedbackInvalidBody)

    logger.info("Setting up SendFeedbackService...")

    feedback_service = SendFeedbackService()
    logger.info("SendFeedbackService ready, start processing feedback")

    feedback_service.process_feedback(feedback)
    logger.info("Process complete", {"Result": "Successfully sent feedback by email"})

    if is_itoc_test_feedback(ods_code):
        logger.info("Setting up SendTestFeedbackService")

        test_feedback_service = SendTestFeedbackService()
        test_feedback_service.process_feedback(feedback)

    return ApiGatewayResponse(
        200, "Feedback email processed", "POST"
    ).create_api_gateway_response()


def is_itoc_test_feedback(ods_code: str) -> bool:
    ods_codes = os.environ["ITOC_TESTING_ODS_CODES"].split(",")
    return ods_code in ods_codes
