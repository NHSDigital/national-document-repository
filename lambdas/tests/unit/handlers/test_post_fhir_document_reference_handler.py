import json

import pytest
from enums.lambda_error import LambdaError
from handlers.post_fhir_document_reference_handler import lambda_handler
from utils.lambda_exceptions import CreateDocumentRefException


@pytest.fixture
def valid_event():
    return {
        "body": json.dumps(
            {
                "resourceType": "DocumentReference",
                "subject": {
                    "identifier": {
                        "system": "https://fhir.nhs.uk/Id/nhs-number",
                        "value": "9000000009",
                    }
                },
            }
        ),
        "headers": json.dumps(
            {
                "Accept": "text/json",
                "Host": "example.com",
            }
        ),
        "requestContext": json.dumps(
            {
                "accountId": "123456789012",
                "apiId": "abc123",
                "domainName": "api.example.com",
                "identity": {
                    "sourceIp": "1.2.3.4",
                    "userAgent": "curl/7.64.1",
                },
            }
        ),
    }


@pytest.fixture
def valid_mtls_event():
    return {
        "body": json.dumps(
            {
                "resourceType": "DocumentReference",
                "subject": {
                    "identifier": {
                        "system": "https://fhir.nhs.uk/Id/nhs-number",
                        "value": "9000000009",
                    }
                },
            }
        ),
        "headers": json.dumps(
            {
                "Accept": "text/json",
                "Host": "example.com",
            }
        ),
        "requestContext": json.dumps(
            {
                "accountId": "123456789012",
                "apiId": "abc123",
                "domainName": "api.example.com",
                "identity": {
                    "sourceIp": "1.2.3.4",
                    "userAgent": "curl/7.64.1",
                    "clientCert": {
                        "clientCertPem": "-----BEGIN CERTIFICATE-----...",
                        "subjectDN": "CN=ndrclient.main.int.pdm.national.nhs.uk,O=NHS,C=UK",
                        "issuerDN": "CN=NHS Root CA,O=NHS,C=UK",
                        "serialNumber": "12:34:56",
                        "validity": {
                            "notBefore": "May 10 00:00:00 2024 GMT",
                            "notAfter": "May 10 00:00:00 2025 GMT",
                        },
                    },
                },
            }
        ),
    }


@pytest.fixture
def mock_service(mocker):
    mock_service = mocker.patch(
        "handlers.post_fhir_document_reference_handler.PostFhirDocumentReferenceService"
    )
    mock_service_instance = mock_service.return_value
    return mock_service_instance


def test_lambda_handler_success(valid_event, context, mock_service):
    """Test successful lambda execution."""
    mock_response = {"resourceType": "DocumentReference", "id": "test-id"}

    mock_service.process_fhir_document_reference.return_value = json.dumps(
        mock_response
    )

    result = lambda_handler(valid_event, context)

    assert result["statusCode"] == 200
    assert json.loads(result["body"]) == mock_response

    mock_service.process_fhir_document_reference.assert_called_once_with(
        valid_event["body"], valid_event["requestContext"]
    )


def test_lambda_handler_exception_handling(valid_event, context, mock_service):
    """Test lambda exception handling."""
    mock_error = CreateDocumentRefException(400, LambdaError.CreateDocNoParse)

    mock_service.process_fhir_document_reference.side_effect = mock_error

    result = lambda_handler(valid_event, context)

    assert result["statusCode"] == 400
    assert "resourceType" in json.loads(result["body"])

    mock_service.process_fhir_document_reference.assert_called_once_with(
        valid_event["body"], valid_event["headers"]
    )


def test_mtls_lambda_handler_success(valid_mtls_event, context, mock_service):
    """Test successful lambda execution."""
    mock_response = {"resourceType": "DocumentReference", "id": "test-id"}

    mock_service.process_fhir_document_reference.return_value = json.dumps(
        mock_response
    )

    result = lambda_handler(valid_mtls_event, context)

    assert result["statusCode"] == 200
    assert json.loads(result["body"]) == mock_response

    mock_service.process_fhir_document_reference.assert_called_once_with(
        valid_mtls_event["body"], valid_mtls_event["requestContext"]
    )
