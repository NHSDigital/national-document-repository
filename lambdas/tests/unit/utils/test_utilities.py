from datetime import datetime

import pytest
from services.mock_pds_service import MockPdsApiService
from services.pds_api_service import PdsApiService
from utils.exceptions import InvalidNhsNumberException
from utils.utilities import (
    camelize_dict,
    flatten,
    format_cloudfront_url,
    get_file_key_from_s3_url,
    get_pds_service,
    parse_date,
    redact_id_to_last_4_chars,
    validate_nhs_number,
)


@pytest.mark.parametrize(
    "valid_nhs_number",
    ["9876543210", "987 654 3210", "987-654-3210", " 987 - 654 3210 "],
)
def test_validate_nhs_number_with_valid_number_returns_true(valid_nhs_number):
    assert validate_nhs_number(valid_nhs_number)


@pytest.mark.parametrize(
    "invalid_nhs_number",
    [
        "123456789",
        "943A765874",
        "9876543213",
    ],
)
def test_validate_nhs_number_with_invalid_number_raises_exception(invalid_nhs_number):
    with pytest.raises(InvalidNhsNumberException):
        validate_nhs_number(invalid_nhs_number)


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


@pytest.mark.parametrize(
    "input_date, expected_date",
    [
        ("25/12/2023", datetime(2023, 12, 25)),
        ("2023-12-25", datetime(2023, 12, 25)),
        ("25-12-2023", datetime(2023, 12, 25)),
        ("Dec 25, 2023", datetime(2023, 12, 25)),
        ("25-Dec-2023", datetime(2023, 12, 25)),
        ("24-NOV-2023", datetime(2023, 11, 24)),
        ("12/12/2024 12:12", None),
        ("25.12.2023", None),
        ("", None),
        ("test_text", None),
        (None, None),
    ],
)
def test_parse_date_returns_correct_date_for_valid_formats(input_date, expected_date):
    result = parse_date(input_date)
    assert result == expected_date
