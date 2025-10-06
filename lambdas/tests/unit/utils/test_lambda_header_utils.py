import pytest

from enums.lambda_error import LambdaError
from enums.mtls import MtlsCommonNames
from utils.lambda_header_utils import validate_common_name_in_mtls
from utils.lambda_exceptions import CreateDocumentRefException


@pytest.fixture
def valid_non_mtls_header():
    return {
        "Accept": "text/json",
        "Host": "example.com",
    }


@pytest.fixture
def valid_mtls_header():
    return {
        "Accept": "text/json",
        "Host": "example.com",
        "x-amzn-mtls-clientcert-subject": "CN=foobar.main.dev.pdm.national.foobar.uk",
    }


@pytest.fixture
def invalid_mtls_header():
    return {
        "Accept": "text/json",
        "Host": "example.com",
        "x-amzn-mtls-clientcert-subject": "CN=foobar.main.dev.foobar.national.foobar.uk",
    }


@pytest.fixture
def invalid_mtls_header_wrong_cn_format():
    return {
        "Accept": "text/json",
        "Host": "example.com",
        "x-amzn-mtls-clientcert-subject": "CN=pdm.pdm.pdm",
    }


def test_validate_valid_common_name(valid_mtls_header):
    """Test validate_common_name when mtls and pdm."""
    result = validate_common_name_in_mtls(valid_mtls_header)

    assert result == MtlsCommonNames.PDM.value


def test_validate_invalid_common_name(invalid_mtls_header):
    """Test validate_common_name when mtls but not pdm."""
    with pytest.raises(CreateDocumentRefException) as excinfo:
        validate_common_name_in_mtls(invalid_mtls_header)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.CreateDocInvalidType


def test_validate_valid_non_mtls_header(valid_non_mtls_header):
    """Test validate_common_name when mtls and pdm."""
    result = validate_common_name_in_mtls(valid_non_mtls_header)

    assert result is None


def test_validate_invalid_common_name_wrong_cn_format(
    invalid_mtls_header_wrong_cn_format,
):
    """Test validate_common_name when mtls but incorrect cn format."""
    with pytest.raises(CreateDocumentRefException) as excinfo:
        validate_common_name_in_mtls(invalid_mtls_header_wrong_cn_format)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.CreateDocInvalidType
