import pytest
from enums.supported_document_types import SupportedDocumentTypes
from tests.unit.conftest import (MOCK_ARF_TABLE_NAME, MOCK_LG_TABLE_NAME,
                                 MOCK_LG_TABLE_NAME_ENV_NAME)
from utils.exceptions import InvalidDocTypeException


@pytest.mark.parametrize(
    ["doc_type", "expected"], [("ARF", MOCK_ARF_TABLE_NAME), ("LG", MOCK_LG_TABLE_NAME)]
)
def test_get_dynamodb_table_name_return_table_name(set_env, doc_type, expected):
    doc_type_enum = SupportedDocumentTypes(doc_type)
    actual = doc_type_enum.get_dynamodb_table_name()

    assert actual == expected


def test_get_dynamodb_table_name_raise_error_for_doc_type_that_dont_have_a_dynamo_table(
    set_env,
):
    with pytest.raises(InvalidDocTypeException):
        SupportedDocumentTypes.ALL.get_dynamodb_table_name()


def test_get_dynamodb_table_name_raise_error_when_env_var_is_missing(
    set_env, monkeypatch, caplog
):
    monkeypatch.delenv(MOCK_LG_TABLE_NAME_ENV_NAME)

    with pytest.raises(InvalidDocTypeException):
        SupportedDocumentTypes.LG.get_dynamodb_table_name()

    assert (
        caplog.records[-1].msg
        == "An error occurred due to missing environment variable for doc_type LG"
    )
    assert caplog.records[-1].levelname == "ERROR"
