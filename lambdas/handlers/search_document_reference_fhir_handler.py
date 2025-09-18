import json
from typing import Any, Dict, Optional, Tuple

from enums.lambda_error import LambdaError
from oauthlib.oauth2 import WebApplicationClient
from services.base.ssm_service import SSMService
from services.document_reference_search_service import DocumentReferenceSearchService
from services.dynamic_configuration_service import DynamicConfigurationService
from services.oidc_service import OidcService
from services.search_patient_details_service import SearchPatientDetailsService
from utils.audit_logging_setup import LoggingService
from utils.decorators.ensure_env_var import ensure_environment_variables
from utils.decorators.handle_lambda_exceptions import handle_lambda_exceptions_fhir
from utils.decorators.set_audit_arg import set_request_context_for_logging
from utils.decorators.validate_patient_id import validate_patient_id_fhir
from utils.exceptions import AuthorisationException, OidcApiException
from utils.lambda_exceptions import DocumentRefSearchException, SearchPatientException
from utils.lambda_response import ApiGatewayResponse
from utils.request_context import request_context

logger = LoggingService(__name__)

# Constants
HEADER_AUTHORIZATION = "Authorization"
HEADER_CIS2_USER_ID = "cis2-urid"
PARAM_TYPE_IDENTIFIER = "type:identifier"
PARAM_CUSTODIAN_IDENTIFIER = "custodian:identifier"
PARAM_SUBJECT_IDENTIFIER = "subject:identifier"
PARAM_NEXT_PAGE_TOKEN = "next-page-token"


@ensure_environment_variables(
    names=["DYNAMODB_TABLE_LIST", "DOCUMENT_RETRIEVE_ENDPOINT_APIM"]
)
@set_request_context_for_logging
@validate_patient_id_fhir
@handle_lambda_exceptions_fhir
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for searching document references by NHS number.
    Args:
        event: API Gateway event containing query parameters with NHS number
        context: Lambda context
    Returns:
        API Gateway response containing FHIR document references or 404 if none is found
    """
    logger.info("Received request to search for document references")

    bearer_token = extract_bearer_token(event)
    selected_role_id = event.get("headers", {}).get(HEADER_CIS2_USER_ID, "")

    nhs_number, search_filters = parse_query_parameters(
        event.get("queryStringParameters", {})
    )
    request_context.patient_nhs_no = nhs_number

    if selected_role_id:
        validate_user_access(bearer_token, selected_role_id, nhs_number)

    service = DocumentReferenceSearchService()
    document_references = service.get_document_references(
        nhs_number=nhs_number,
        return_fhir=True,
        additional_filters=search_filters,
        check_upload_completed=False,
    )

    if not document_references:
        logger.info(f"No document references found for NHS number: {nhs_number}")
        return ApiGatewayResponse(
            404,
            LambdaError.DocumentReferenceNotFound.create_error_response().create_error_fhir_response(
                LambdaError.DocumentReferenceNotFound.value.get("fhir_coding")
            ),
            "GET",
        ).create_api_gateway_response()
    return ApiGatewayResponse(
        200, json.dumps(document_references), "GET"
    ).create_api_gateway_response()


def parse_query_parameters(
    query_string: Dict[str, str]
) -> Tuple[Optional[str], Dict[str, str]]:
    """
    Parse and extract NHS number and search filters from query parameters.

    Args:
        query_string: Dictionary of query parameters

    Returns:
        Tuple of (NHS number, search filters dictionary)
    """
    search_filters = {}
    nhs_number = None

    for key, value in query_string.items():
        if key == PARAM_TYPE_IDENTIFIER:
            search_filters["file_type"] = value.split("|")[-1]
        elif key == PARAM_CUSTODIAN_IDENTIFIER:
            search_filters["custodian"] = value.split("|")[-1]
        elif key == PARAM_SUBJECT_IDENTIFIER:
            nhs_number = value.split("|")[-1]
        elif key == PARAM_NEXT_PAGE_TOKEN:
            pass  # Handled elsewhere
        else:
            logger.warning(f"Unknown query parameter: {key}")

    return nhs_number, search_filters


def validate_user_access(
    bearer_token: str, selected_role_id: str, nhs_number: str
) -> None:
    """
    Validate that the user has permission to access the requested patient data.

    Args:
        bearer_token: Authentication token
        selected_role_id: CIS2 user role ID
        nhs_number: NHS number to validate access for

    Raises:
        DocumentRefSearchException: If the user doesn't have permission
    """
    logger.info("Detected a cis2 user access request, checking for access permission")

    # Initialize services
    configuration_service = DynamicConfigurationService()
    configuration_service.set_auth_ssm_prefix()

    try:
        # Authenticate user and get role information
        oidc_service = OidcService()
        oidc_service.set_up_oidc_parameters(SSMService, WebApplicationClient)
        userinfo = oidc_service.fetch_userinfo(bearer_token)
        org_ods_code = oidc_service.fetch_user_org_code(userinfo, selected_role_id)
        smartcard_role_code, _ = oidc_service.fetch_user_role_code(
            userinfo, selected_role_id, "R"
        )
    except (OidcApiException, AuthorisationException) as e:
        logger.error(f"Authorization failed: {e}")
        raise DocumentRefSearchException(403, LambdaError.DocumentReferenceUnauthorised)

    try:
        # Validate patient access
        search_patient_service = SearchPatientDetailsService(
            smartcard_role_code, org_ods_code
        )
        search_patient_service.handle_search_patient_request(nhs_number, False)
    except SearchPatientException as e:
        raise DocumentRefSearchException(e.status_code, e.error)


def extract_bearer_token(event):
    """Extract and validate bearer token from event"""
    headers = event.get("headers", {})
    if not headers:
        logger.warning("No headers found in request")
        raise DocumentRefSearchException(401, LambdaError.DocumentReferenceUnauthorised)
    bearer_token = headers.get("Authorization", None)
    if not bearer_token or not bearer_token.startswith("Bearer "):
        logger.warning("No bearer token found in request")
        raise DocumentRefSearchException(401, LambdaError.DocumentReferenceUnauthorised)
    return bearer_token
