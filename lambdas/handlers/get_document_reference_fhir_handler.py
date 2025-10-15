from enums.lambda_error import LambdaError
from oauthlib.oauth2 import WebApplicationClient
from services.base.ssm_service import SSMService
from services.dynamic_configuration_service import DynamicConfigurationService
from services.get_fhir_document_reference_service import GetFhirDocumentReferenceService
from services.oidc_service import OidcService
from services.search_patient_details_service import SearchPatientDetailsService
from utils.audit_logging_setup import LoggingService
from utils.decorators.ensure_env_var import ensure_environment_variables
from utils.decorators.handle_lambda_exceptions import handle_lambda_exceptions_fhir
from utils.decorators.set_audit_arg import set_request_context_for_logging
from utils.exceptions import AuthorisationException, OidcApiException
from utils.lambda_exceptions import (
    GetFhirDocumentReferenceException,
    SearchPatientException,
)
from utils.lambda_response import ApiGatewayResponse

logger = LoggingService(__name__)


@handle_lambda_exceptions_fhir
@set_request_context_for_logging
@ensure_environment_variables(
    names=[
        "APPCONFIG_APPLICATION",
        "APPCONFIG_CONFIGURATION",
        "APPCONFIG_ENVIRONMENT",
        "LLOYD_GEORGE_DYNAMODB_NAME",
        "PDM_DYNAMODB_NAME",
        "PRESIGNED_ASSUME_ROLE",
        "CLOUDFRONT_URL",
    ]
)
def lambda_handler(event, context):
    try:
        bearer_token = extract_bearer_token(event)
        selected_role_id = event.get("headers", {}).get("cis2-urid", None)
        document_id, snomed_code = extract_document_parameters(event)

        get_document_service = GetFhirDocumentReferenceService()
        document_reference = get_document_service.handle_get_document_reference_request(
            snomed_code, document_id
        )

        if selected_role_id:
            verify_user_authorisation(
                bearer_token, selected_role_id, document_reference.nhs_number
            )

        document_reference_response = (
            get_document_service.create_document_reference_fhir_response(
                document_reference
            )
        )

        logger.info(
            f"Successfully retrieved document reference for document_id: {document_id}, snomed_code: {snomed_code}"
        )

        return ApiGatewayResponse(
            status_code=200, body=document_reference_response, methods="GET"
        ).create_api_gateway_response()

    except GetFhirDocumentReferenceException as exception:
        return ApiGatewayResponse(
            status_code=exception.status_code,
            body=exception.error.create_error_response().create_error_fhir_response(
                exception.error.value.get("fhir_coding")
            ),
            methods="GET",
        ).create_api_gateway_response()


def extract_bearer_token(event):
    """Extract and validate bearer token from event"""
    bearer_token = event.get("headers", {}).get("Authorization", None)
    if not bearer_token or not bearer_token.startswith("Bearer "):
        logger.warning("No bearer token found in request")
        raise GetFhirDocumentReferenceException(
            401, LambdaError.DocumentReferenceUnauthorised
        )
    return bearer_token


def extract_document_parameters(event):
    """Extract document ID and SNOMED code from path parameters"""
    path_params = event.get("pathParameters", {}).get("id", None)
    document_id, snomed_code = get_id_and_snomed_from_path_parameters(path_params)

    if not document_id or not snomed_code:
        logger.error("Missing document id or snomed code in request path parameters.")
        raise GetFhirDocumentReferenceException(
            400, LambdaError.DocumentReferenceMissingParameters
        )

    return document_id, snomed_code


def verify_user_authorisation(bearer_token, selected_role_id, nhs_number):
    """Verify user authorisation for accessing patient data"""
    logger.info("Detected a cis2 user access request, checking for access permission")

    try:
        configuration_service = DynamicConfigurationService()
        configuration_service.set_auth_ssm_prefix()

        oidc_service = OidcService()
        oidc_service.set_up_oidc_parameters(SSMService, WebApplicationClient)
        userinfo = oidc_service.fetch_userinfo(bearer_token)

        org_ods_code = oidc_service.fetch_user_org_code(userinfo, selected_role_id)
        smartcard_role_code, _ = oidc_service.fetch_user_role_code(
            userinfo, selected_role_id, "R"
        )
    except (OidcApiException, AuthorisationException) as e:
        logger.error(f"Authorization error: {str(e)}")
        raise GetFhirDocumentReferenceException(
            403, LambdaError.DocumentReferenceUnauthorised
        )

    try:
        search_patient_service = SearchPatientDetailsService(
            smartcard_role_code, org_ods_code
        )
        search_patient_service.handle_search_patient_request(nhs_number, False)
    except SearchPatientException as e:
        raise GetFhirDocumentReferenceException(e.status_code, e.error)


def get_id_and_snomed_from_path_parameters(path_parameters):
    """Extract document ID and SNOMED code from path parameters"""
    if path_parameters:
        params = path_parameters.split("~")
        if len(params) == 2:
            return params[1], params[0]
    return None, None
