import pytest
from enums.lambda_error import LambdaError
from enums.mtls import MtlsCommonNames
from utils.lambda_exceptions import InvalidDocTypeException
from utils.lambda_header_utils import validate_common_name_in_mtls


@pytest.fixture
def valid_non_mtls_request_context():
    return {
        "accountId": "123456789012",
        "apiId": "abc123",
        "domainName": "api.example.com",
        "identity": {
            "sourceIp": "1.2.3.4",
            "userAgent": "curl/7.64.1",
        },
    }


@pytest.fixture
def valid_mtls_request_context():
    return {
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


@pytest.fixture
def invalid_mtls_request_context():
    return {
        "accountId": "123456789012",
        "apiId": "abc123",
        "domainName": "api.example.com",
        "identity": {
            "sourceIp": "1.2.3.4",
            "userAgent": "curl/7.64.1",
            "clientCert": {
                "clientCertPem": "-----BEGIN CERTIFICATE-----...",
                "subjectDN": "CN=ndrclient.main.int.foobar.national.nhs.uk,O=NHS,C=UK",
                "issuerDN": "CN=NHS Root CA,O=NHS,C=UK",
                "serialNumber": "12:34:56",
                "validity": {
                    "notBefore": "May 10 00:00:00 2024 GMT",
                    "notAfter": "May 10 00:00:00 2025 GMT",
                },
            },
        },
    }


def test_validate_valid_common_name(valid_mtls_request_context):
    """Test validate_common_name when mtls and pdm."""
    result = validate_common_name_in_mtls(valid_mtls_request_context)

    assert result == MtlsCommonNames.PDM.value


def test_validate_invalid_common_name(invalid_mtls_request_context):
    """Test validate_common_name when mtls but not allowed."""
    with pytest.raises(InvalidDocTypeException) as excinfo:
        validate_common_name_in_mtls(invalid_mtls_request_context)
    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.DocTypeInvalid


def test_validate_valid_non_mtls_header(valid_non_mtls_request_context):
    """Test validate header when no common name."""
    result = validate_common_name_in_mtls(valid_non_mtls_request_context)

    assert result is None
