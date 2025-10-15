import json

import pytest
from enums.lambda_error import LambdaError
from enums.snomed_codes import SnomedCodes
from models.document_reference import DocumentReference
from models.fhir.R4.fhir_document_reference import (
    DocumentReference as FhirDocumentReference,
)
from services.put_fhir_document_reference_service import (
    PutFhirDocumentReferenceService
)
from tests.unit.conftest import APIM_API_URL
from utils.lambda_exceptions import UpdateFhirDocumentReferenceException
from tests.unit.helpers.data.test_documents import create_test_doc_store_refs, create_valid_fhir_doc_json
from utils.exceptions import DocumentServiceException
from pydantic import ValidationError

@pytest.fixture
def valid_nhs_number():
    return "9000000009"


@pytest.fixture
def mock_service(set_env, mocker):
    mock_s3 = mocker.patch("services.put_fhir_document_reference_service.S3Service")
    mock_dynamo = mocker.patch(
        "services.put_fhir_document_reference_service.DynamoDBService"
    )
    mock_document_service = mocker.patch("services.put_fhir_document_reference_service.DocumentService")
    mock_document_service.s3_service = mock_s3

    service = PutFhirDocumentReferenceService()
    service.s3_service = mock_s3.return_value
    service.dynamo_service = mock_dynamo.return_value
    service.document_service = mock_document_service.return_value

    yield service


@pytest.fixture
def valid_fhir_doc_json(valid_nhs_number):
    return create_valid_fhir_doc_json(valid_nhs_number)


@pytest.fixture
def valid_doc_ref(valid_fhir_doc_json):
    doc = json.loads(valid_fhir_doc_json)
    return DocumentReference(
        id="1",
        nhs_number=doc["subject"]["identifier"]["value"],
        file_name=doc["content"][0]["attachment"]["title"],
        attachment_url=None,
        doc_status="final",
        version="2",
    )
    


@pytest.fixture
def valid_fhir_doc_object(valid_fhir_doc_json):
    return FhirDocumentReference.model_validate_json(valid_fhir_doc_json)


@pytest.fixture
def valid_fhir_doc_with_binary(valid_fhir_doc_json):
    doc = json.loads(valid_fhir_doc_json)
    doc["content"][0]["attachment"][
        "data"
    ] = "SGVsbG8gV29ybGQ="  # Base64 encoded "Hello World"
    return json.dumps(doc)


@pytest.mark.parametrize(
        "version_number",
        range(1, 10)
)
def test_process_fhir_document_reference_with_presigned_url(
    mock_service, valid_fhir_doc_json, version_number, valid_doc_ref, valid_nhs_number
):
    mock_presigned_url_response = "https://test-bucket.s3.amazonaws.com/"

    mock_service.document_service.create_s3_presigned_url.return_value = (
        mock_presigned_url_response
    )

    document = create_test_doc_store_refs()[0]
    document.nhs_number = valid_nhs_number
    document.version = str(version_number)

    valid_doc_ref.version = str(version_number + 1)

    doc = json.loads(valid_fhir_doc_json)
    doc["meta"]["versionId"] = str(version_number)
    valid_fhir_doc_json = json.dumps(doc)

    mock_service.document_service.create_document_reference.return_value = valid_doc_ref
    mock_service.document_service.get_document_reference.return_value = document
    mock_service.document_service.extract_nhs_number_from_fhir.return_value = valid_nhs_number

    result = mock_service.process_fhir_document_reference(valid_fhir_doc_json)
    expected_pre_sign_url = mock_presigned_url_response

    assert isinstance(result, str)
    result_json = json.loads(result)
    assert result_json["resourceType"] == "DocumentReference"
    assert result_json["content"][0]["attachment"]["url"] == expected_pre_sign_url

    assert mock_service.document_service.save_document_reference_to_dynamo.call_args.args[1].version == str(version_number + 1)


@pytest.mark.parametrize(
        "version_number",
        range(1, 10)
)
def test_process_fhir_document_reference_with_binary(
    mock_service, valid_fhir_doc_with_binary, version_number, valid_doc_ref, valid_nhs_number
):
    """Test a happy path with binary data in the request."""
    custom_endpoint = f"{APIM_API_URL}/DocumentReference"

    document = create_test_doc_store_refs()[0]
    document.nhs_number = valid_nhs_number
    document.version = str(version_number)

    valid_doc_ref.version = str(version_number + 1)

    doc = json.loads(valid_fhir_doc_with_binary)
    doc["meta"]["versionId"] = str(version_number)
    valid_fhir_doc_with_binary = json.dumps(doc)

    mock_service.document_service.create_document_reference.return_value = valid_doc_ref
    mock_service.document_service.get_document_reference.return_value = document
    mock_service.document_service.extract_nhs_number_from_fhir.return_value = valid_nhs_number

    result = mock_service.process_fhir_document_reference(valid_fhir_doc_with_binary)

    assert isinstance(result, str)
    result_json = json.loads(result)
    assert result_json["resourceType"] == "DocumentReference"
    attachment_url = result_json["content"][0]["attachment"]["url"]
    assert custom_endpoint in attachment_url

    assert mock_service.document_service.save_document_reference_to_dynamo.call_args.args[1].version == str(version_number + 1)


def test_validation_error(mock_service):
    """Test handling of an invalid FHIR document."""
    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service.process_fhir_document_reference("{invalid json}")

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.UpdateDocNoParse


def test_pds_error(mock_service, valid_fhir_doc_json, mocker, valid_doc_ref, valid_nhs_number):
    """Test handling of PDS error."""

    mock_service.document_service.check_nhs_number_with_pds.side_effect = DocumentServiceException()

    document = create_test_doc_store_refs()[0]
    document.nhs_number = valid_nhs_number

    mock_service.document_service.create_document_reference.return_value = valid_doc_ref
    mock_service.document_service.get_document_reference.return_value = document
    mock_service.document_service.extract_nhs_number_from_fhir.return_value = valid_nhs_number

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service.process_fhir_document_reference(valid_fhir_doc_json)
    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.UpdatePatientSearchInvalid


def test_process_fhir_document_reference_with_pds_error(
    mock_service, valid_fhir_doc_json, valid_nhs_number
):
    """Test process_fhir_document_reference with a real PDS error (PatientNotFoundException)."""
    mock_service.document_service.check_nhs_number_with_pds.side_effect = DocumentServiceException()

    document = create_test_doc_store_refs()[0]
    document.nhs_number = valid_nhs_number

    mock_service.document_service.create_document_reference.return_value = valid_doc_ref
    mock_service.document_service.get_document_reference.return_value = document
    mock_service.document_service.extract_nhs_number_from_fhir.return_value = valid_nhs_number

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service.process_fhir_document_reference(valid_fhir_doc_json)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.UpdatePatientSearchInvalid


def test_s3_presigned_url_error(mock_service, valid_fhir_doc_json, valid_doc_ref, valid_nhs_number):
    """Test handling of S3 presigned URL error."""
    mock_service.document_service.create_s3_presigned_url.side_effect = DocumentServiceException()

    document = create_test_doc_store_refs()[0]
    document.nhs_number = valid_nhs_number

    mock_service.document_service.create_document_reference.return_value = valid_doc_ref
    mock_service.document_service.get_document_reference.return_value = document
    mock_service.document_service.extract_nhs_number_from_fhir.return_value = valid_nhs_number

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service.process_fhir_document_reference(valid_fhir_doc_json)

    assert excinfo.value.status_code == 500
    assert excinfo.value.error == LambdaError.InternalServerError


def test_s3_upload_error(mock_service, valid_fhir_doc_with_binary, valid_doc_ref, valid_nhs_number):
    """Test handling of S3 upload error."""
    mock_service.document_service.store_binary_in_s3.side_effect = DocumentServiceException()

    document = create_test_doc_store_refs()[0]
    document.nhs_number = valid_nhs_number

    mock_service.document_service.create_document_reference.return_value = valid_doc_ref
    mock_service.document_service.get_document_reference.return_value = document
    mock_service.document_service.extract_nhs_number_from_fhir.return_value = valid_nhs_number

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service.process_fhir_document_reference(valid_fhir_doc_with_binary)

    assert excinfo.value.status_code == 500
    assert excinfo.value.error == LambdaError.UpdateDocNoParse


def test_process_fhir_document_reference_with_malformed_json(mock_service):
    """Test process_fhir_document_reference with malformed JSON."""
    malformed_json = '{"resourceType": "DocumentReference", "invalid": }'

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service.process_fhir_document_reference(malformed_json)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.UpdateDocNoParse


def test_process_fhir_document_reference_with_empty_string(mock_service):
    """Test process_fhir_document_reference with an empty string."""
    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service.process_fhir_document_reference("")

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.UpdateDocNoParse


def test_process_fhir_document_reference_with_none(mock_service):
    """Test process_fhir_document_reference with None input."""
    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service.process_fhir_document_reference(None)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.UpdateDocNoParse


def test_validate_update_document_reference_request_with_non_final_document(mock_service, valid_fhir_doc_json, valid_doc_ref):
    """Test _validate_update_document_reference_request errors when document to edit is not final version"""
    valid_doc_ref.doc_status = "deprecated"
    mock_service.document_service.get_document_reference.return_value = valid_doc_ref

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service._validate_update_document_reference_request(valid_fhir_doc_json)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.UpdateDocNotLatestVersion


def test_validate_update_document_reference_request_mismatched_version(mock_service, valid_fhir_doc_json, valid_doc_ref, valid_nhs_number):
    """Test _validate_update_document_reference_request errors when document to edit is not final version"""
    valid_doc_ref.version = "10"
    valid_doc_ref.doc_status = "final"
    valid_doc_ref.nhs_number = valid_nhs_number
    mock_service.document_service.get_document_reference.return_value = valid_doc_ref
    mock_service.document_service.extract_nhs_number_from_fhir.return_value = valid_nhs_number

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service._validate_update_document_reference_request(valid_fhir_doc_json)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.UpdateDocVersionMismatch


def test_validate_update_document_reference_mismatched_nhs_number(mock_service, valid_fhir_doc_json, valid_doc_ref, valid_nhs_number):
    """Test _validate_update_document_reference_request error when the NHS number doesn't match"""
    valid_doc_ref.doc_status = "final"
    valid_doc_ref.nhs_number = "1"
    mock_service.document_service.get_document_reference.return_value = valid_doc_ref
    mock_service.document_service.extract_nhs_number_from_fhir.return_value = valid_nhs_number

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service._validate_update_document_reference_request(valid_fhir_doc_json)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.UpdateDocNHSNumberMismatch


def test_validate_update_document_reference_missing_meta_field(mock_service, valid_fhir_doc_json, valid_doc_ref, valid_nhs_number):
    """Test _validate_update_document_reference_request error when meta field is missing"""
    doc = json.loads(valid_fhir_doc_json)
    doc["meta"] = None
    valid_fhir_doc_json = json.dumps(doc)

    mock_service.document_service.get_document_reference.return_value = valid_doc_ref
    mock_service.document_service.extract_nhs_number_from_fhir.return_value = valid_nhs_number

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service._validate_update_document_reference_request(valid_fhir_doc_json)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.DocumentReferenceMissingParameters


def test_nhs_number_extraction_error(mock_service, valid_fhir_doc_object):
    """Test handling errors from extract_nhs_number_from_fhir"""
    mock_service.document_service.extract_nhs_number_from_fhir.side_effect = DocumentServiceException()

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service._update_document_references(valid_fhir_doc_object)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.UpdateDocNoParse


def test_determine_document_type_error(mock_service, valid_fhir_doc_object):
    """Test handling errors from determine_document_type"""
    mock_service.document_service.determine_document_type.side_effect = DocumentServiceException()

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service._update_document_references(valid_fhir_doc_object)
    
    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.UpdateDocInvalidType


def test_get_document_reference_error(mock_service, valid_fhir_doc_object):
    """Test handling of errors from get_document_reference"""#
    mock_service.document_service.get_document_reference.side_effect = DocumentServiceException()

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service._update_document_references(valid_fhir_doc_object)
    
    assert excinfo.value.status_code == 404
    assert excinfo.value.error == LambdaError.DocumentReferenceNotFound


def test_save_document_reference_to_dynamo_error(mock_service, valid_fhir_doc_object):
    """test handling errors from save_document_reference_to_dynamo"""
    mock_service.document_service.save_document_reference_to_dynamo.side_effect = DocumentServiceException()

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service._update_document_references(valid_fhir_doc_object)

    assert excinfo.value.status_code == 500
    assert excinfo.value.error == LambdaError.UpdateDocUploadInternalError


def test_create_fhir_response_validation_error(mocker, mock_service, valid_fhir_doc_object):
    """test handling errors from _create_fhir_response"""
    mock_service._create_fhir_response = mocker.patch("services.put_fhir_document_reference_service.PutFhirDocumentReferenceService._create_fhir_response")
    mock_service._create_fhir_response.side_effect = ValidationError("", [])

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service._update_document_references(valid_fhir_doc_object)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.UpdateDocNoParse


def test_document_reference_not_found_error(mock_service, valid_fhir_doc_json):
    """test handling current document reference not found"""
    mock_service.document_service.get_document_reference.return_value = None

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service._validate_update_document_reference_request(valid_fhir_doc_json)

    assert excinfo.value.status_code == 404
    assert excinfo.value.error == LambdaError.DocumentReferenceNotFound

