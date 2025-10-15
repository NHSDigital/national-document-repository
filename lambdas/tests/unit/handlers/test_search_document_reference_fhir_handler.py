import json
from unittest.mock import MagicMock, patch

import pytest
from enums.lambda_error import LambdaError
from handlers.search_document_reference_fhir_handler import (
    extract_bearer_token,
    lambda_handler,
    parse_query_parameters,
    validate_user_access,
)
from utils.exceptions import AuthorisationException, OidcApiException
from utils.lambda_exceptions import DocumentRefSearchException


@pytest.fixture
def valid_nhs_number_event():
    return {
        "httpMethod": "GET",
        "headers": {
            "Authorization": "Bearer valid-token",
        },
        "queryStringParameters": {
            "subject:identifier": "https://fhir.nhs.uk/Id/nhs-number|9000000009"
        },
    }


@pytest.fixture
def valid_event_with_filters():
    return {
        "httpMethod": "GET",
        "headers": {
            "Authorization": "Bearer valid-token",
        },
        "queryStringParameters": {
            "subject:identifier": "https://fhir.nhs.uk/Id/nhs-number|9000000009",
            "type:identifier": "http://snomed.info/sct|736253002",
            "custodian:identifier": "https://fhir.nhs.uk/Id/ods-organization-code|Y12345",
            "next-page-token": "some-token",
            "unknown-param": "some-value",
        },
    }


@pytest.fixture
def invalid_nhs_number_event():
    return {
        "httpMethod": "GET",
        "queryStringParameters": {"subject:identifier": "invalid-nhs-number"},
    }


@pytest.fixture
def missing_nhs_number_event():
    return {
        "httpMethod": "GET",
        "queryStringParameters": {},
    }


@pytest.fixture
def valid_event_with_auth():
    return {
        "httpMethod": "GET",
        "headers": {"Authorization": "Bearer valid-token", "cis2-urid": "role-id-123"},
        "queryStringParameters": {
            "subject:identifier": "https://fhir.nhs.uk/Id/nhs-number|9000000009"
        },
    }


@pytest.fixture
def invalid_auth_event():
    return {
        "httpMethod": "GET",
        "headers": {"Authorization": "invalid-token"},
        "queryStringParameters": {
            "subject:identifier": "https://fhir.nhs.uk/Id/nhs-number|9000000009"
        },
    }


@pytest.fixture
def missing_auth_event():
    return {
        "httpMethod": "GET",
        "headers": {},
        "queryStringParameters": {
            "subject:identifier": "https://fhir.nhs.uk/Id/nhs-number|9000000009"
        },
    }


@pytest.fixture
def mock_document_reference_search_service():
    with patch(
        "handlers.search_document_reference_fhir_handler.DocumentReferenceSearchService"
    ) as mock_service:
        service_instance = mock_service.return_value
        yield service_instance


@pytest.fixture
def mock_oidc_service():
    with patch(
        "handlers.search_document_reference_fhir_handler.OidcService"
    ) as mock_service:
        service_instance = mock_service.return_value
        yield service_instance


@pytest.fixture
def mock_search_patient_service():
    with patch(
        "handlers.search_document_reference_fhir_handler.SearchPatientDetailsService"
    ) as mock_service:
        yield mock_service


@pytest.fixture
def mock_dynamic_config_service():
    with patch(
        "handlers.search_document_reference_fhir_handler.DynamicConfigurationService"
    ) as mock_service:
        service_instance = mock_service.return_value
        yield service_instance


def test_lambda_handler_returns_200_with_documents(
    mock_document_reference_search_service, valid_nhs_number_event, context, set_env
):
    mock_document_references = [
        {"resourceType": "DocumentReference", "status": "current"},
        {"resourceType": "DocumentReference", "status": "current"},
    ]
    mock_document_reference_search_service.get_document_references.return_value = (
        mock_document_references
    )

    response = lambda_handler(valid_nhs_number_event, context)

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == mock_document_references
    mock_document_reference_search_service.get_document_references.assert_called_once_with(
        nhs_number="9000000009",
        return_fhir=True,
        additional_filters={},
        check_upload_completed=False,
    )


def test_lambda_handler_returns_404_when_no_documents(
    mock_document_reference_search_service, valid_nhs_number_event, context, set_env
):
    mock_document_reference_search_service.get_document_references.return_value = []

    response = lambda_handler(valid_nhs_number_event, context)

    assert response["statusCode"] == 404
    mock_document_reference_search_service.get_document_references.assert_called_once_with(
        nhs_number="9000000009",
        return_fhir=True,
        additional_filters={},
        check_upload_completed=False,
    )


def test_lambda_handler_returns_400_for_invalid_nhs_number(
    mock_document_reference_search_service, invalid_nhs_number_event, context, set_env
):
    response = lambda_handler(invalid_nhs_number_event, context)

    assert response["statusCode"] == 400

    mock_document_reference_search_service.get_document_references.assert_not_called()


def test_lambda_handler_returns_400_for_missing_nhs_number(
    mock_document_reference_search_service, missing_nhs_number_event, context, set_env
):
    response = lambda_handler(missing_nhs_number_event, context)

    assert response["statusCode"] == 400

    mock_document_reference_search_service.get_document_references.assert_not_called()


def test_lambda_handler_with_additional_filters(
    mock_document_reference_search_service, valid_event_with_filters, context, set_env
):
    mock_document_references = [
        {"resourceType": "DocumentReference", "status": "current"},
    ]
    mock_document_reference_search_service.get_document_references.return_value = (
        mock_document_references
    )

    response = lambda_handler(valid_event_with_filters, context)

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == mock_document_references

    # Check that the filters were correctly parsed and passed
    expected_filters = {"file_type": "736253002", "custodian": "Y12345"}
    mock_document_reference_search_service.get_document_references.assert_called_once_with(
        nhs_number="9000000009",
        return_fhir=True,
        additional_filters=expected_filters,
        check_upload_completed=False,
    )


def test_lambda_handler_with_auth_validation(
    mock_document_reference_search_service,
    mock_oidc_service,
    mock_search_patient_service,
    mock_dynamic_config_service,
    valid_event_with_auth,
    context,
    set_env,
):
    # Setup mocks
    mock_document_references = [
        {"resourceType": "DocumentReference", "status": "current"}
    ]
    mock_document_reference_search_service.get_document_references.return_value = (
        mock_document_references
    )

    # Mock successful authorisation
    mock_userinfo = {"some": "userinfo"}
    mock_oidc_service.fetch_userinfo.return_value = mock_userinfo
    mock_oidc_service.fetch_user_org_code.return_value = "Y12345"
    mock_oidc_service.fetch_user_role_code.return_value = ("B0428", "Some Role")

    # Mock successful patient search
    mock_search_instance = MagicMock()
    mock_search_patient_service.return_value = mock_search_instance

    response = lambda_handler(valid_event_with_auth, context)

    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == mock_document_references

    # Verify authorisation flow
    mock_dynamic_config_service.set_auth_ssm_prefix.assert_called_once()
    mock_oidc_service.set_up_oidc_parameters.assert_called_once()
    mock_oidc_service.fetch_userinfo.assert_called_once_with("Bearer valid-token")
    mock_oidc_service.fetch_user_org_code.assert_called_once_with(
        mock_userinfo, "role-id-123"
    )
    mock_oidc_service.fetch_user_role_code.assert_called_once_with(
        mock_userinfo, "role-id-123", "R"
    )

    # Verify patient search
    mock_search_patient_service.assert_called_once_with("B0428", "Y12345")
    mock_search_instance.handle_search_patient_request.assert_called_once_with(
        "9000000009", False
    )


def test_lambda_handler_with_invalid_auth_token(
    mock_document_reference_search_service, invalid_auth_event, context, set_env
):
    response = lambda_handler(invalid_auth_event, context)

    assert response["statusCode"] == 401
    mock_document_reference_search_service.get_document_references.assert_not_called()


def test_lambda_handler_with_missing_auth_token(
    mock_document_reference_search_service, missing_auth_event, context, set_env
):
    response = lambda_handler(missing_auth_event, context)

    assert response["statusCode"] == 401
    mock_document_reference_search_service.get_document_references.assert_not_called()


def test_lambda_handler_with_oidc_auth_failure(
    mock_document_reference_search_service,
    mock_oidc_service,
    mock_dynamic_config_service,
    valid_event_with_auth,
    context,
    set_env,
):
    # Setup mocks to simulate OIDC authentication failure
    mock_oidc_service.fetch_userinfo.side_effect = OidcApiException("OIDC API error")

    response = lambda_handler(valid_event_with_auth, context)

    assert response["statusCode"] == 403
    mock_document_reference_search_service.get_document_references.assert_not_called()


def test_lambda_handler_with_patient_search_failure(
    mock_document_reference_search_service,
    mock_oidc_service,
    mock_search_patient_service,
    mock_dynamic_config_service,
    valid_event_with_auth,
    context,
    set_env,
):
    # Setup mocks
    mock_userinfo = {"some": "userinfo"}
    mock_oidc_service.fetch_userinfo.return_value = mock_userinfo
    mock_oidc_service.fetch_user_org_code.return_value = "Y12345"
    mock_oidc_service.fetch_user_role_code.return_value = ("B0428", "Some Role")

    # Mock patient search failure
    from utils.lambda_exceptions import SearchPatientException

    mock_search_instance = MagicMock()
    mock_search_patient_service.return_value = mock_search_instance
    mock_search_instance.handle_search_patient_request.side_effect = (
        SearchPatientException(403, LambdaError.SearchPatientNoAuth)
    )

    response = lambda_handler(valid_event_with_auth, context)

    assert response["statusCode"] == 403
    mock_document_reference_search_service.get_document_references.assert_not_called()


def test_parse_query_parameters():
    query_params = {
        "subject:identifier": "https://fhir.nhs.uk/Id/nhs-number|9000000009",
        "type:identifier": "http://snomed.info/sct|736253002",
        "custodian:identifier": "https://fhir.nhs.uk/Id/ods-organization-code|Y12345",
        "next-page-token": "some-token",
        "unknown-param": "some-value",
    }

    nhs_number, filters = parse_query_parameters(query_params)

    assert nhs_number == "9000000009"
    assert filters == {"file_type": "736253002", "custodian": "Y12345"}

    # Test with empty parameters
    nhs_number, filters = parse_query_parameters({})
    assert nhs_number is None
    assert filters == {}


def test_extract_bearer_token_valid():
    event = {"headers": {"Authorization": "Bearer valid-token"}}

    token = extract_bearer_token(event)
    assert token == "Bearer valid-token"


def test_extract_bearer_token_invalid_format():
    event = {"headers": {"Authorization": "Token valid-token"}}

    with pytest.raises(DocumentRefSearchException) as e:
        extract_bearer_token(event)

    assert e.value.status_code == 401


def test_extract_bearer_token_missing():
    event = {"headers": {}}

    with pytest.raises(DocumentRefSearchException) as e:
        extract_bearer_token(event)

    assert e.value.status_code == 401


@patch("handlers.search_document_reference_fhir_handler.OidcService")
@patch("handlers.search_document_reference_fhir_handler.SearchPatientDetailsService")
@patch("handlers.search_document_reference_fhir_handler.DynamicConfigurationService")
@patch("handlers.search_document_reference_fhir_handler.SSMService")
@patch("handlers.search_document_reference_fhir_handler.WebApplicationClient")
def test_validate_user_access_success(
    mock_web_client,
    mock_ssm,
    mock_config_service,
    mock_search_service,
    mock_oidc_service,
):
    # Setup mocks
    mock_config_instance = mock_config_service.return_value
    mock_oidc_instance = mock_oidc_service.return_value
    mock_search_instance = mock_search_service.return_value

    # Mock successful authentication
    mock_userinfo = {"some": "userinfo"}
    mock_oidc_instance.fetch_userinfo.return_value = mock_userinfo
    mock_oidc_instance.fetch_user_org_code.return_value = "Y12345"
    mock_oidc_instance.fetch_user_role_code.return_value = ("B0428", "Some Role")

    # Call function
    validate_user_access("Bearer valid-token", "role-id-123", "9000000009")

    # Verify function calls
    mock_config_instance.set_auth_ssm_prefix.assert_called_once()
    mock_oidc_instance.set_up_oidc_parameters.assert_called_once_with(
        mock_ssm, mock_web_client
    )
    mock_oidc_instance.fetch_userinfo.assert_called_once_with("Bearer valid-token")
    mock_oidc_instance.fetch_user_org_code.assert_called_once_with(
        mock_userinfo, "role-id-123"
    )
    mock_oidc_instance.fetch_user_role_code.assert_called_once_with(
        mock_userinfo, "role-id-123", "R"
    )

    mock_search_service.assert_called_once_with("B0428", "Y12345")
    mock_search_instance.handle_search_patient_request.assert_called_once_with(
        "9000000009", False
    )


@patch("handlers.search_document_reference_fhir_handler.OidcService")
@patch("handlers.search_document_reference_fhir_handler.DynamicConfigurationService")
def test_validate_user_access_oidc_failure(mock_config_service, mock_oidc_service):
    # Setup mocks
    mock_oidc_instance = mock_oidc_service.return_value

    # Mock OIDC failure
    mock_oidc_instance.fetch_userinfo.side_effect = OidcApiException("OIDC API error")

    # Call function and expect exception
    with pytest.raises(DocumentRefSearchException) as e:
        validate_user_access("Bearer valid-token", "role-id-123", "9000000009")

    assert e.value.status_code == 403


@patch("handlers.search_document_reference_fhir_handler.OidcService")
@patch("handlers.search_document_reference_fhir_handler.SearchPatientDetailsService")
@patch("handlers.search_document_reference_fhir_handler.DynamicConfigurationService")
def test_validate_user_access_patient_search_failure(
    mock_config_service, mock_search_service, mock_oidc_service
):
    # Setup mocks
    mock_oidc_instance = mock_oidc_service.return_value
    mock_search_instance = mock_search_service.return_value

    # Mock successful authentication
    mock_userinfo = {"some": "userinfo"}
    mock_oidc_instance.fetch_userinfo.return_value = mock_userinfo
    mock_oidc_instance.fetch_user_org_code.return_value = "Y12345"
    mock_oidc_instance.fetch_user_role_code.return_value = ("B0428", "Some Role")

    # Mock patient search failure
    from utils.lambda_exceptions import SearchPatientException

    mock_search_instance.handle_search_patient_request.side_effect = (
        SearchPatientException(403, LambdaError.SearchPatientNoAuth)
    )

    # Call function and expect exception
    with pytest.raises(DocumentRefSearchException) as e:
        validate_user_access("Bearer valid-token", "role-id-123", "9000000009")

    assert e.value.status_code == 403


@patch("handlers.search_document_reference_fhir_handler.OidcService")
@patch("handlers.search_document_reference_fhir_handler.DynamicConfigurationService")
def test_validate_user_access_authorization_failure(
    mock_config_service, mock_oidc_service
):
    # Setup mocks
    mock_oidc_instance = mock_oidc_service.return_value

    # Mock authorisation failure
    mock_oidc_instance.fetch_userinfo.side_effect = AuthorisationException(
        "Authorization error"
    )

    # Call function and expect exception
    with pytest.raises(DocumentRefSearchException) as e:
        validate_user_access("Bearer valid-token", "role-id-123", "9000000009")

    assert e.value.status_code == 403
