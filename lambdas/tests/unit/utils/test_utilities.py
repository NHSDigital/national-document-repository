import pytest
from services.mock_pds_service import MockPdsApiService
from services.pds_api_service import PdsApiService
from utils.exceptions import InvalidResourceIdException
from utils.utilities import (
    camelize_dict,
    flatten,
    format_cloudfront_url,
    get_file_key_from_s3_url,
    get_pds_service,
    redact_id_to_last_4_chars,
    validate_nhs_number,
)


def test_validate_nhs_number_with_valid_number_returns_true():
    nhs_number = "9876543210"
    assert validate_nhs_number(nhs_number)


def test_validate_nhs_number_with_valid_number_with_spaces_returns_true():
    nhs_number = "987 654 3210"
    assert validate_nhs_number(nhs_number)


def test_validate_nhs_number_with_valid_number_with_dashes_returns_true():
    nhs_number = "987-654-3210"
    assert validate_nhs_number(nhs_number)


def test_validate_nhs_number_with_valid_number_with_mixed_formatting_returns_true():
    nhs_number = " 987 - 654 3210 "
    assert validate_nhs_number(nhs_number)


def test_validate_nhs_number_with_too_short_number_raises_exception():
    nhs_number = "123456789"
    with pytest.raises(InvalidResourceIdException):
        validate_nhs_number(nhs_number)


def test_validate_nhs_number_with_non_numeric_characters_raises_exception():
    nhs_number = "943A765874"
    with pytest.raises(InvalidResourceIdException):
        validate_nhs_number(nhs_number)


def test_validate_nhs_number_with_invalid_checksum_raises_exception():
    nhs_number = "9876543213"
    with pytest.raises(InvalidResourceIdException):
        validate_nhs_number(nhs_number)


def test_decapitalise_keys():
    test_dict = {"FileName": "test", "VirusScannerResult": "test"}

    expected = {"fileName": "test", "virusScannerResult": "test"}

    actual = camelize_dict(test_dict)

    assert actual == expected


@pytest.mark.parametrize(
    "stub_value",
    [
        ("True"),
        ("true"),
    ],
)
def test_get_pds_service_returns_stubbed_pds_when_true(monkeypatch, stub_value):
    monkeypatch.setenv("PDS_FHIR_IS_STUBBED", stub_value)

    response = get_pds_service()

    assert isinstance(response, MockPdsApiService)


def test_get_pds_service_returns_stubbed_pds_when_unset():
    response = get_pds_service()

    assert isinstance(response, MockPdsApiService)


@pytest.mark.parametrize(
    "stub_value",
    [
        ("False"),
        ("false"),
    ],
)
def test_get_pds_service_returns_real_pds(monkeypatch, stub_value):
    monkeypatch.setenv("PDS_FHIR_IS_STUBBED", stub_value)

    response = get_pds_service()

    assert isinstance(response, PdsApiService)


def test_redact_id():
    mock_session_id = "1234532532432"
    expected = "2432"

    actual = redact_id_to_last_4_chars(mock_session_id)

    assert expected == actual


def test_get_file_key_from_s3_url():
    test_url = "s3://test-s3-bucket/9000000009/user-upload/arf/3575f1ab-e7ae-4edf-958b-410ac0d42461"
    expected = "9000000009/user-upload/arf/3575f1ab-e7ae-4edf-958b-410ac0d42461"
    actual = get_file_key_from_s3_url(test_url)

    assert actual == expected


def test_flatten_reduce_one_level_of_nesting_given_a_nested_list():
    nested_list = [["a", "b", "c"], ["d", "e"], ["f"], ["a"]]
    expected = ["a", "b", "c", "d", "e", "f", "a"]

    actual = flatten(nested_list)

    assert actual == expected


def test_format_cloudfront_url_valid():
    presign_url = "path/to/resource"
    cloudfront_domain = "d12345.cloudfront.net"
    expected_url = "https://d12345.cloudfront.net/path/to/resource"
    assert format_cloudfront_url(presign_url, cloudfront_domain) == expected_url
