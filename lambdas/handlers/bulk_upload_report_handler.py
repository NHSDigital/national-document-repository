from services.bulk_upload_report_service import BulkUploadReportService
from utils.audit_logging_setup import LoggingService
from utils.decorators.ensure_env_var import ensure_environment_variables
from utils.decorators.handle_lambda_exceptions import handle_lambda_exceptions
from utils.decorators.override_error_check import override_error_check
from utils.decorators.set_audit_arg import set_request_context_for_logging
from utils.lambda_response import ApiGatewayResponse

logger = LoggingService(__name__)


@set_request_context_for_logging
@ensure_environment_variables(
    names=[
        "STATISTICAL_REPORTS_BUCKET",
        "BULK_UPLOAD_DYNAMODB_NAME",
    ]
)
@override_error_check
@handle_lambda_exceptions
def lambda_handler(event, context):
    logger.info("Starting bulk upload report process")

    bulk_upload_report_service = BulkUploadReportService()
    bulk_upload_report_service.report_handler()

    return ApiGatewayResponse(
        status_code=200,
        body="Bulk upload summary and ODS reports created successfully",
        methods="GET",
    ).create_api_gateway_response()
