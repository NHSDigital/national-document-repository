from enums.lambda_error import LambdaError
from enums.logging_app_interaction import LoggingAppInteraction
from services.search_patient_details_service import SearchPatientDetailsService
from utils.audit_logging_setup import LoggingService
from utils.decorators.ensure_env_var import ensure_environment_variables
from utils.decorators.handle_lambda_exceptions import handle_lambda_exceptions
from utils.decorators.override_error_check import override_error_check
from utils.decorators.set_audit_arg import set_request_context_for_logging
from utils.decorators.validate_patient_id import validate_patient_id
from utils.lambda_exceptions import SearchPatientException
from utils.lambda_response import ApiGatewayResponse
from utils.request_context import request_context

logger = LoggingService(__name__)


@set_request_context_for_logging
@validate_patient_id
@override_error_check
@ensure_environment_variables(names=["AUTH_SESSION_TABLE_NAME"])
@handle_lambda_exceptions
def lambda_handler(event, context):
    request_context.app_interaction = LoggingAppInteraction.PATIENT_SEARCH.value
    logger.info("Starting patient search process")

    nhs_number = event["queryStringParameters"]["patientId"]
    request_context.patient_nhs_no = nhs_number
    user_ods_code, user_role = "", ""
    if isinstance(request_context.authorization, dict):
        user_ods_code = request_context.authorization.get(
            "selected_organisation", {}
        ).get("org_ods_code", "")
        user_role = request_context.authorization.get("repository_role", "")
    if not user_role or not user_ods_code:
        logger.error(
            f"{LambdaError.SearchPatientMissing.to_str()}",
            {"Result": "Patient not found"},
        )
        raise SearchPatientException(400, LambdaError.SearchPatientMissing)

    search_service = SearchPatientDetailsService(
        user_role=user_role, user_ods_code=user_ods_code
    )

    # Get patient details from service
    patient_details = search_service.handle_search_patient_request(
        nhs_number,
    )
    formatted_response = patient_details.model_dump_json(
        by_alias=True,
        exclude={
            "death_notification_status",
            "general_practice_ods",
        },
    )

    return ApiGatewayResponse(
        200, formatted_response, "GET"
    ).create_api_gateway_response()
