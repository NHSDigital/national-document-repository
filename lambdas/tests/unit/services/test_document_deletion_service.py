import pytest
from enums.s3_lifecycle_tags import S3LifecycleTags
from enums.supported_document_types import SupportedDocumentTypes
from services.document_deletion_service import DocumentDeletionService
from tests.unit.conftest import MOCK_ARF_TABLE_NAME, MOCK_LG_TABLE_NAME, TEST_NHS_NUMBER
from tests.unit.helpers.data.test_documents import (
    create_test_doc_store_refs,
    create_test_lloyd_george_doc_store_refs,
)

TEST_DOC_STORE_REFERENCES = create_test_doc_store_refs()
TEST_LG_DOC_STORE_REFERENCES = create_test_lloyd_george_doc_store_refs()
TEST_NHS_NUMBER_WITH_NO_RECORD = "1234567890"
TEST_NHS_NUMBER_WITH_ONLY_LG_RECORD = "234567890"


def mocked_document_query(
    nhs_number: str, doc_type: SupportedDocumentTypes, filter_expression
):
    if nhs_number == TEST_NHS_NUMBER and doc_type == SupportedDocumentTypes.LG:
        return TEST_LG_DOC_STORE_REFERENCES
    elif nhs_number == TEST_NHS_NUMBER and doc_type == SupportedDocumentTypes.ARF:
        return TEST_DOC_STORE_REFERENCES
    elif (
        nhs_number == TEST_NHS_NUMBER_WITH_ONLY_LG_RECORD
        and doc_type == SupportedDocumentTypes.LG
    ):
        return TEST_LG_DOC_STORE_REFERENCES
    return []


@pytest.fixture
def mock_deletion_service(set_env):
    yield DocumentDeletionService()


@pytest.fixture
def mock_delete_doc(mocker):
    yield mocker.patch("services.document_service.DocumentService.delete_documents")


@pytest.fixture
def mock_delete_specific_doc_type(mocker):
    def mocked_method(nhs_number: str, doc_type: SupportedDocumentTypes):
        filter_expression = None
        return mocked_document_query(nhs_number, doc_type, filter_expression)

    yield mocker.patch.object(
        DocumentDeletionService,
        "delete_specific_doc_type",
        side_effect=mocked_method,
    )


@pytest.fixture
def mock_document_query(mocker):
    yield mocker.patch(
        "services.document_service.DocumentService.fetch_available_document_references_by_type",
        side_effect=mocked_document_query,
    )


def test_handle_delete_for_all_doc_type(
    mock_delete_specific_doc_type, mock_deletion_service
):
    expected = TEST_DOC_STORE_REFERENCES + TEST_LG_DOC_STORE_REFERENCES

    actual = mock_deletion_service.handle_delete(
        TEST_NHS_NUMBER, SupportedDocumentTypes.ALL
    )

    assert expected == actual

    assert mock_delete_specific_doc_type.call_count == 2
    mock_delete_specific_doc_type.assert_any_call(
        TEST_NHS_NUMBER, SupportedDocumentTypes.ARF
    )
    mock_delete_specific_doc_type.assert_any_call(
        TEST_NHS_NUMBER, SupportedDocumentTypes.LG
    )


def test_handle_delete_all_doc_type_when_only_lg_records_available(
    mock_delete_specific_doc_type, mock_deletion_service
):
    nhs_number = TEST_NHS_NUMBER_WITH_ONLY_LG_RECORD

    expected = TEST_LG_DOC_STORE_REFERENCES
    actual = mock_deletion_service.handle_delete(nhs_number, SupportedDocumentTypes.ALL)

    assert expected == actual

    assert mock_delete_specific_doc_type.call_count == 2
    mock_delete_specific_doc_type.assert_any_call(
        nhs_number, SupportedDocumentTypes.ARF
    )
    mock_delete_specific_doc_type.assert_any_call(nhs_number, SupportedDocumentTypes.LG)


@pytest.mark.parametrize(
    ["doc_type", "expected"],
    [
        (SupportedDocumentTypes.ARF, TEST_DOC_STORE_REFERENCES),
        (SupportedDocumentTypes.LG, TEST_LG_DOC_STORE_REFERENCES),
    ],
)
def test_handle_delete_for_one_doc_type(
    doc_type, expected, mock_delete_specific_doc_type, mock_deletion_service
):
    actual = mock_deletion_service.handle_delete(TEST_NHS_NUMBER, doc_type)

    assert actual == expected

    assert mock_delete_specific_doc_type.call_count == 1
    mock_delete_specific_doc_type.assert_called_with(TEST_NHS_NUMBER, doc_type)


def test_handle_delete_when_no_record_for_patient_return_empty_list(
    mock_delete_specific_doc_type, mock_deletion_service
):
    expected = []
    actual = mock_deletion_service.handle_delete(
        TEST_NHS_NUMBER_WITH_NO_RECORD, SupportedDocumentTypes.ALL
    )

    assert actual == expected


@pytest.mark.parametrize(
    ["doc_type", "table_name", "doc_ref"],
    [
        (SupportedDocumentTypes.ARF, MOCK_ARF_TABLE_NAME, TEST_DOC_STORE_REFERENCES),
        (SupportedDocumentTypes.LG, MOCK_LG_TABLE_NAME, TEST_LG_DOC_STORE_REFERENCES),
    ],
)
def test_delete_specific_doc_type(
    doc_type,
    table_name,
    doc_ref,
    mock_document_query,
    mock_delete_doc,
    mock_deletion_service,
):
    type_of_delete = str(S3LifecycleTags.SOFT_DELETE.value)

    expected = doc_ref
    actual = mock_deletion_service.delete_specific_doc_type(TEST_NHS_NUMBER, doc_type)

    assert actual == expected

    mock_delete_doc.assert_called_once_with(
        table_name=table_name,
        document_references=doc_ref,
        type_of_delete=type_of_delete,
    )


@pytest.mark.parametrize(
    "doc_type",
    [SupportedDocumentTypes.ARF, SupportedDocumentTypes.LG],
)
def test_delete_specific_doc_type_when_no_record_for_given_patient(
    doc_type,
    mock_document_query,
    mock_deletion_service,
    mock_delete_doc,
):
    expected = []
    actual = mock_deletion_service.delete_specific_doc_type(
        TEST_NHS_NUMBER_WITH_NO_RECORD, doc_type
    )

    assert actual == expected

    mock_delete_doc.assert_not_called()
