from enums.logging_app_interaction import LoggingAppInteraction
from services.upload_document_reference_service import UploadDocumentReferenceService
from utils.audit_logging_setup import LoggingService
from utils.decorators.ensure_env_var import ensure_environment_variables
from utils.decorators.handle_lambda_exceptions import handle_lambda_exceptions
from utils.decorators.set_audit_arg import set_request_context_for_logging
from utils.lambda_response import ApiGatewayResponse
from utils.request_context import request_context

logger = LoggingService(__name__)


@set_request_context_for_logging
@ensure_environment_variables(
    names=[
        "LLOYD_GEORGE_DYNAMODB_NAME",
        "PDM_DYNAMODB_NAME",
        "STAGING_STORE_BUCKET_NAME",
        "LLOYD_GEORGE_BUCKET_NAME",
        "PDM_BUCKET_NAME",
        "VIRUS_SCAN_STUB",
    ]
)
@handle_lambda_exceptions
def lambda_handler(event, context):
    request_context.app_interaction = LoggingAppInteraction.VIRUS_SCAN.value
    upload_document_reference_service = UploadDocumentReferenceService()

    for s3_object in event.get("Records"):
        object_key = s3_object["s3"]["object"]["key"]
        object_size = s3_object["s3"]["object"]["size"]
        upload_document_reference_service.handle_upload_document_reference_request(
            object_key, object_size
        )

    return ApiGatewayResponse(
        200, "Virus Scan was successful", "POST"
    ).create_api_gateway_response()
