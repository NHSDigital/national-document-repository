import json

import pytest
from botocore.exceptions import ClientError
from models.document_reference import DocumentReference
from services.document_reference_search_service import DocumentReferenceSearchService
from tests.unit.helpers.data.dynamo.dynamo_responses import MOCK_SEARCH_RESPONSE
from utils.exceptions import DynamoServiceException
from utils.lambda_exceptions import DocumentRefSearchException

MOCK_DOCUMENT_REFERENCE = [
    DocumentReference.model_validate(MOCK_SEARCH_RESPONSE["Items"][0])
]

MOCK_FILE_SIZE = 24000

EXPECTED_RESPONSE = {
    "created": "2024-01-01T12:00:00.000Z",
    "fileName": "document.csv",
    "virusScannerResult": "Clean",
    "ID": "3d8683b9-1665-40d2-8499-6e8302d507ff",
    "fileSize": MOCK_FILE_SIZE,
}


@pytest.fixture
def patched_service(mocker, set_env):
    service = DocumentReferenceSearchService()
    mock_s3_service = mocker.patch.object(service, "s3_service")
    mocker.patch.object(mock_s3_service, "get_file_size", return_value=MOCK_FILE_SIZE)
    mocker.patch.object(service, "dynamo_service")
    mocker.patch.object(service, "fetch_documents_from_table_with_nhs_number")
    mocker.patch.object(service, "is_upload_in_process", return_value=False)
    yield service


def test_get_document_references_raise_json_error_when_no_table_list(
    patched_service, monkeypatch
):
    monkeypatch.setenv("DYNAMODB_TABLE_LIST", "")
    with pytest.raises(DocumentRefSearchException):
        patched_service.get_document_references("111111111")


def test_get_document_references_raise_validation_error(
    patched_service, validation_error
):
    patched_service.fetch_documents_from_table_with_nhs_number.side_effect = (
        validation_error
    )
    with pytest.raises(DocumentRefSearchException):
        patched_service.get_document_references("111111111")


def test_get_document_references_raise_client_error(patched_service):
    patched_service.fetch_documents_from_table_with_nhs_number.side_effect = (
        ClientError(
            {
                "Error": {
                    "Code": "test",
                    "Message": "test",
                }
            },
            "test",
        )
    )
    with pytest.raises(DocumentRefSearchException):
        patched_service.get_document_references("111111111")


def test_get_document_references_raise_dynamodb_error(patched_service):
    patched_service.fetch_documents_from_table_with_nhs_number.side_effect = (
        DynamoServiceException()
    )
    with pytest.raises(DocumentRefSearchException):
        patched_service.get_document_references("111111111")


def test_get_document_references_dynamo_return_empty_response(patched_service):
    patched_service.fetch_documents_from_table_with_nhs_number.return_value = []
    expected_results = []

    actual = patched_service.get_document_references("1111111111")

    assert actual == expected_results


def test_get_document_references_dynamo_return_successful_response_single_table(
    patched_service, monkeypatch
):
    monkeypatch.setenv("DYNAMODB_TABLE_LIST", json.dumps(["test_table"]))

    patched_service.fetch_documents_from_table_with_nhs_number.return_value = (
        MOCK_DOCUMENT_REFERENCE
    )
    expected_results = [EXPECTED_RESPONSE]
    actual = patched_service.get_document_references("1111111111")

    assert actual == expected_results


def test_get_document_references_dynamo_return_successful_response_multiple_tables(
    patched_service,
):
    patched_service.fetch_documents_from_table_with_nhs_number.return_value = (
        MOCK_DOCUMENT_REFERENCE
    )
    expected_results = [EXPECTED_RESPONSE, EXPECTED_RESPONSE]

    actual = patched_service.get_document_references("1111111111")

    assert actual == expected_results


def test_get_document_references_raise_error_when_upload_is_in_process(
    patched_service,
):
    patched_service.fetch_documents_from_table_with_nhs_number.return_value = (
        MOCK_DOCUMENT_REFERENCE
    )
    patched_service.is_upload_in_process.return_value = True

    with pytest.raises(DocumentRefSearchException):
        patched_service.get_document_references("111111111")
