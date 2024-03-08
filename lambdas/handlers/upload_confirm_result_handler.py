import json
from json import JSONDecodeError

from enums.lambda_error import LambdaError
from enums.logging_app_interaction import LoggingAppInteraction
from services.upload_confirm_result_service import UploadConfirmResultService
from utils.audit_logging_setup import LoggingService
from utils.decorators.ensure_env_var import ensure_environment_variables
from utils.decorators.handle_lambda_exceptions import handle_lambda_exceptions
from utils.decorators.override_error_check import override_error_check
from utils.decorators.set_audit_arg import set_request_context_for_logging
from utils.lambda_exceptions import UploadConfirmResultException
from utils.lambda_response import ApiGatewayResponse
from utils.request_context import request_context

logger = LoggingService(__name__)


@set_request_context_for_logging
@ensure_environment_variables(
    names=[
        "APPCONFIG_APPLICATION",
        "APPCONFIG_CONFIGURATION",
        "APPCONFIG_ENVIRONMENT",
        "DOCUMENT_STORE_BUCKET_NAME",
        "DOCUMENT_STORE_DYNAMODB_NAME",
        "LLOYD_GEORGE_BUCKET_NAME",
        "LLOYD_GEORGE_DYNAMODB_NAME",
        "STAGING_STORE_BUCKET_NAME",
    ]
)
@override_error_check
@handle_lambda_exceptions
def lambda_handler(event, context):
    request_context.app_interaction = LoggingAppInteraction.UPLOAD_CONFIRMATION.value

    logger.info("Upload confirm result handler triggered")

    nhs_number, documents = processing_event_details(event)
    request_context.patient_nhs_no = nhs_number
    upload_confirm_result_service = UploadConfirmResultService(nhs_number)

    upload_confirm_result_service.process_documents(documents)
    response_body = "Finished processing all documents"
    logger.info(response_body, {"Result": "Successfully processed all documents"})

    return ApiGatewayResponse(
        status_code=204, body=response_body, methods="POST"
    ).create_api_gateway_response()


def processing_event_details(event):
    failed_message = "Upload confirm result failed"

    try:
        body = json.loads(event.get("body", ""))

        if not body or not isinstance(body, dict):
            logger.error(
                f"{LambdaError.UploadConfirmResultMissingBody.to_str()}",
                {"Result": failed_message},
            )
            raise UploadConfirmResultException(
                400, LambdaError.UploadConfirmResultMissingBody
            )

        nhs_number = body.get("patientId")
        documents = body.get("documents")

        if not nhs_number or not documents:
            logger.error(
                f"{LambdaError.UploadConfirmResultProps.to_str()}",
                {"Result": failed_message},
            )
            raise UploadConfirmResultException(
                400, LambdaError.UploadConfirmResultProps
            )
        return nhs_number, documents

    except JSONDecodeError as e:
        logger.error(
            f"{LambdaError.UploadConfirmResultPayload.to_str()}: {str(e)}",
            {"Result": failed_message},
        )
        raise UploadConfirmResultException(400, LambdaError.UploadConfirmResultPayload)
