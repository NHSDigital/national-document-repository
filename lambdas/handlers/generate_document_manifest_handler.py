from enums.lambda_error import LambdaError
from enums.logging_app_interaction import LoggingAppInteraction
from models.zip_trace import DocumentManifestZipTrace
from pydantic import ValidationError
from services.zip_service import DocumentZipService
from utils.audit_logging_setup import LoggingService
from utils.decorators.ensure_env_var import ensure_environment_variables
from utils.decorators.handle_lambda_exceptions import handle_lambda_exceptions
from utils.decorators.override_error_check import override_error_check
from utils.decorators.set_audit_arg import set_request_context_for_logging
from utils.lambda_exceptions import DocumentManifestServiceException
from utils.lambda_response import ApiGatewayResponse
from utils.request_context import request_context

logger = LoggingService(__name__)


@set_request_context_for_logging
@ensure_environment_variables(
    names=[
        "ZIPPED_STORE_BUCKET_NAME",
        "ZIPPED_STORE_DYNAMODB_NAME",
    ]
)
@override_error_check
@handle_lambda_exceptions
def lambda_handler(event, context):
    request_context.app_interaction = LoggingAppInteraction.DOWNLOAD_RECORD.value

    logger.info("Triggered by Dynamo INSERT event")

    dynamo_records = event.get("Records")

    if not dynamo_records:
        return ApiGatewayResponse(400, "", "GET").create_api_gateway_response()

    for record in dynamo_records:
        dynamo_new_item = record.get("dynamodb", {}).get("NewImage")
        event_name = record.get("eventName")
        if not dynamo_new_item or event_name != "INSERT":
            return ApiGatewayResponse(400, "", "GET").create_api_gateway_response()

        try:
            zip_trace_item = prepare_zip_trace_data(dynamo_new_item)
            zip_trace = DocumentManifestZipTrace.model_validate(zip_trace_item)

        except ValidationError as e:
            logger.error(
                f"{LambdaError.ManifestValidation.to_str()}: {str(e)}",
                {"Result": "Failed to create document manifest"},
            )
            raise DocumentManifestServiceException(
                status_code=500, error=LambdaError.ManifestValidation
            )
        zip_service = DocumentZipService(zip_trace)
        zip_service.handle_zip_request()

    return ApiGatewayResponse(200, "", "GET").create_api_gateway_response()


def prepare_zip_trace_data(dynamo_new_item):
    for key, nested_object in dynamo_new_item.items():
        value = list(nested_object.values())[0]
        if isinstance(value, dict):
            prepare_zip_trace_data(value)

        dynamo_new_item[key] = list(nested_object.values())[0]

    return dynamo_new_item
