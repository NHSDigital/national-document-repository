import base64
import copy
import json
from io import BytesIO

import pytest
from enums.lambda_error import LambdaError
from enums.snomed_codes import SnomedCode, SnomedCodes
from services.get_fhir_document_reference_service import GetFhirDocumentReferenceService
from tests.unit.conftest import MOCK_LG_TABLE_NAME, MOCK_PDM_TABLE_NAME
from tests.unit.helpers.data.test_documents import create_test_doc_store_refs
from utils.lambda_exceptions import (
    GetFhirDocumentReferenceException,
    InvalidDocTypeException,
)
from utils.lambda_exceptions import GetFhirDocumentReferenceException
from utils.ods_utils import PCSE_ODS_CODE


@pytest.fixture
def patched_service(mocker, set_env, context):
    mocker.patch("services.base.s3_service.IAMService")
    mocker.patch("services.get_fhir_document_reference_service.S3Service")
    mocker.patch("services.get_fhir_document_reference_service.SSMService")
    mocker.patch("services.get_fhir_document_reference_service.DocumentService")
    service = GetFhirDocumentReferenceService()

    yield service


def test_get_document_reference_service(patched_service):
    documents = create_test_doc_store_refs()
    patched_service.document_service.fetch_documents_from_table.return_value = documents

    actual = patched_service.get_document_references(
        "3d8683b9-1665-40d2-8499-6e8302d507ff", MOCK_LG_TABLE_NAME
    )
    assert actual == documents[0]


def test_handle_get_document_reference_request(patched_service, mocker, set_env):
    documents = create_test_doc_store_refs()

    expected = documents[0]
    mock_document_ref = documents[0]
    mocker.patch.object(
        patched_service, "get_document_references", return_value=mock_document_ref
    )

    actual = patched_service.handle_get_document_reference_request(
        SnomedCodes.LLOYD_GEORGE.value.code, "test-id"
    )

    assert expected == actual


def test_get_dynamo_table_for_patient_data_doc_type(patched_service):
    """Test _get_dynamo_table_for_doc_type method with a non-Lloyd George document type."""

    patient_data_code = SnomedCodes.PATIENT_DATA.value

    result = patched_service._get_dynamo_table_for_doc_type(patient_data_code)
    assert result == MOCK_PDM_TABLE_NAME


def test_get_dynamo_table_for_unsupported_doc_type(patched_service):
    """Test _get_dynamo_table_for_doc_type method with a non-Lloyd George document type."""

    non_lg_code = SnomedCode(code="non-lg-code", display_name="Non Lloyd George")

    with pytest.raises(InvalidDocTypeException) as excinfo:
        patched_service._get_dynamo_table_for_doc_type(non_lg_code)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.DocTypeDB


def test_get_dynamo_table_for_lloyd_george_doc_type(patched_service):
    """Test _get_dynamo_table_for_doc_type method with Lloyd George document type."""
    lg_code = SnomedCodes.LLOYD_GEORGE.value

    result = patched_service._get_dynamo_table_for_doc_type(lg_code)

    assert result == MOCK_LG_TABLE_NAME


def test_get_presigned_url(patched_service, mocker):

    patched_service.s3_service.create_download_presigned_url.return_value = (
        "https://example.com/path/to/resource"
    )

    result = patched_service.get_presigned_url(
        "test-s3-bucket", "9000000009/test-key-123"
    )
    assert result == "https://example.com/path/to/resource"

    patched_service.s3_service.create_download_presigned_url.assert_called_once_with(
        s3_bucket_name="test-s3-bucket",
        file_key="9000000009/test-key-123",
    )


def test_get_document_references_empty_result(patched_service):
    # Test when no documents are found
    patched_service.document_service.fetch_documents_from_table.return_value = []

    with pytest.raises(GetFhirDocumentReferenceException) as exc_info:
        patched_service.get_document_references("test-id", MOCK_LG_TABLE_NAME)

    assert exc_info.value.error == LambdaError.DocumentReferenceNotFound
    assert exc_info.value.status_code == 404


def test_get_presigned_url_failure(patched_service, mocker):
    # Test when S3 service raises an exception
    patched_service.s3_service.create_download_presigned_url.side_effect = Exception(
        "S3 error"
    )

    with pytest.raises(Exception) as exc_info:
        patched_service.get_presigned_url("file-key", "bucket-name")

    assert str(exc_info.value) == "S3 error"
    patched_service.s3_service.create_download_presigned_url.assert_called_once()


def test_create_document_reference_fhir_response_with_presign_url_document_data(
    patched_service, mocker
):
    # Test creating FHIR response with different document data
    test_doc = create_test_doc_store_refs()[0]

    # Modify the document reference to test different values
    modified_doc = copy.deepcopy(test_doc)
    modified_doc.file_name = "different_file.pdf"
    modified_doc.created = "2023-05-15T10:30:00.000Z"
    modified_doc.document_scan_creation = "2023-05-15"

    patched_service.s3_service.get_file_size.return_value = 8000000
    patched_service.get_presigned_url = mocker.MagicMock(
        return_value="https://new-test-url.com"
    )
    result = patched_service.create_document_reference_fhir_response(modified_doc)

    result_json = json.loads(result)
    assert result_json["content"][0]["attachment"]["url"] == "https://new-test-url.com"
    assert result_json["content"][0]["attachment"]["title"] == "different_file.pdf"
    assert result_json["content"][0]["attachment"]["creation"] == "2023-05-15"


def test_create_document_reference_fhir_response_with_binary_document_data(
    patched_service,
):
    # Test creating FHIR response with different document data
    test_doc = create_test_doc_store_refs()[0]
    # Modify the document reference to test different values
    modified_doc = copy.deepcopy(test_doc)
    modified_doc.file_name = "different_file.pdf"
    modified_doc.created = "2023-05-15T10:30:00.000Z"
    modified_doc.document_scan_creation = "2023-05-15"

    patched_service.s3_service.get_file_size.return_value = 7999999
    mock_binary_file = BytesIO(b"binary data")
    patched_service.s3_service.get_object_stream.return_value = mock_binary_file

    result = patched_service.create_document_reference_fhir_response(modified_doc)
    result_json = json.loads(result)
    mock_binary_file.seek(0)
    expected_encoded = base64.b64encode(mock_binary_file.read()).decode("utf-8")
    assert result_json["content"][0]["attachment"]["data"] == expected_encoded
    assert result_json["content"][0]["attachment"]["title"] == "different_file.pdf"
    assert result_json["content"][0]["attachment"]["creation"] == "2023-05-15"


def test_create_document_reference_fhir_response_non_final_status(
    patched_service, mocker
):
    """Test FHIR response creation for documents with non-final status."""
    test_doc = create_test_doc_store_refs()[0]
    modified_doc = copy.deepcopy(test_doc)
    modified_doc.doc_status = "preliminary"

    patched_service.get_presigned_url = mocker.MagicMock()

    result = patched_service.create_document_reference_fhir_response(modified_doc)
    result_json = json.loads(result)

    # Should not include data or url fields
    assert "data" not in result_json["content"][0]["attachment"]
    assert "url" not in result_json["content"][0]["attachment"]

    # Verify methods were not called
    patched_service.s3_service.get_binary_file.assert_not_called()
    patched_service.get_presigned_url.assert_not_called()

def test_create_document_reference_fhir_response_when_patient_is_deceased(
    patched_service, mocker
):
    """Test FHIR response creation for documents with non-final status."""
    test_doc = create_test_doc_store_refs()[0]
    modified_doc = copy.deepcopy(test_doc)
    modified_doc.custodian = "DECE"
    modified_doc.doc_status = "preliminary"

    patched_service.get_presigned_url = mocker.MagicMock()

    result = patched_service.create_document_reference_fhir_response(modified_doc)
    result_json = json.loads(result)

    assert result_json["custodian"]["identifier"]["value"] == PCSE_ODS_CODE
