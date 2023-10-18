import pytest
from utils.exceptions import InvalidResourceIdException
from utils.utilities import camelize_dict, validate_id


def test_validate_id_with_valid_id_returns_true():
    nhs_number = "0000000000"

    result = validate_id(nhs_number)

    assert result


def test_validate_id_with_valid_id_raises_InvalidResourceIdException():
    nhs_number = "000000000"

    with pytest.raises(InvalidResourceIdException):
        validate_id(nhs_number)


def test_decapitalise_keys():
    test_dict = {"FileName": "test", "VirusScannerResult": "test"}

    expected = {"fileName": "test", "virusScannerResult": "test"}

    actual = camelize_dict(test_dict)

    assert actual == expected
