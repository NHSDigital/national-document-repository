import json

import pytest
from botocore.exceptions import ClientError
from models.document_reference import DocumentReference
from services.document_reference_search_service import DocumentReferenceSearchService
from utils.exceptions import (
    DocumentRefSearchException,
    DynamoDbException,
    InvalidResourceIdException,
)

MOCK_DATA = {
    "ID": "3d8683b9-1665-40d2-8499-6e8302d507ff",
    "ContentType": "type",
    "Created": "2023-08-23T00:38:04.095Z",
    "Deleted": "",
    "FileLocation": "s3://test-bucket/9000000009/test-key-123",
    "FileName": "document.csv",
    "NhsNumber": "9000000009",
    "VirusScannerResult": "Clean",
}

MOCK_DOCUMENT_REFERENCE = [DocumentReference.model_validate(MOCK_DATA)]

EXPECTED_RESPONSE = {
    "created": "2023-08-23T00:38:04.095Z",
    "fileName": "document.csv",
    "virusScannerResult": "Clean",
}


@pytest.fixture
def patched_service(mocker, set_env):
    service = DocumentReferenceSearchService()
    mocker.patch.object(service, "s3_service")
    mocker.patch.object(service, "dynamo_service")
    mocker.patch.object(service, "fetch_documents_from_table_with_filter")
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
    patched_service.fetch_documents_from_table_with_filter.side_effect = (
        validation_error
    )
    with pytest.raises(DocumentRefSearchException):
        patched_service.get_document_references("111111111")


def test_get_document_references_raise_invalid_resource_error(patched_service):
    patched_service.fetch_documents_from_table_with_filter.side_effect = (
        InvalidResourceIdException()
    )
    with pytest.raises(DocumentRefSearchException):
        patched_service.get_document_references("111111111")


def test_get_document_references_raise_client_error(patched_service):
    patched_service.fetch_documents_from_table_with_filter.side_effect = ClientError(
        {
            "Error": {
                "Code": "test",
                "Message": "test",
            }
        },
        "test",
    )
    with pytest.raises(DocumentRefSearchException):
        patched_service.get_document_references("111111111")


def test_get_document_references_raise_dynamodb_error(patched_service):
    patched_service.fetch_documents_from_table_with_filter.side_effect = (
        DynamoDbException()
    )
    with pytest.raises(DocumentRefSearchException):
        patched_service.get_document_references("111111111")


def test_get_document_references_dynamo_return_empty_response(patched_service):
    patched_service.fetch_documents_from_table_with_filter.return_value = []
    expected_results = []

    actual = patched_service.get_document_references("1111111111")

    assert actual == expected_results


def test_get_document_references_dynamo_return_successful_response_single_table(
    patched_service, monkeypatch
):
    monkeypatch.setenv("DYNAMODB_TABLE_LIST", json.dumps(["test_table"]))

    patched_service.fetch_documents_from_table_with_filter.return_value = (
        MOCK_DOCUMENT_REFERENCE
    )
    expected_results = [EXPECTED_RESPONSE]

    actual = patched_service.get_document_references("1111111111")

    assert actual == expected_results


def test_get_document_references_dynamo_return_successful_response_multiple_tables(
    patched_service,
):
    patched_service.fetch_documents_from_table_with_filter.return_value = (
        MOCK_DOCUMENT_REFERENCE
    )
    expected_results = [EXPECTED_RESPONSE, EXPECTED_RESPONSE]

    actual = patched_service.get_document_references("1111111111")

    assert actual == expected_results
