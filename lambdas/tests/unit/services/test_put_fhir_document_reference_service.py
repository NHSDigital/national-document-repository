import json

import pytest
from botocore.exceptions import ClientError
from enums.lambda_error import LambdaError
from enums.snomed_codes import SnomedCode, SnomedCodes
from models.document_reference import DocumentReference
from models.fhir.R4.base_models import Identifier, Reference
from models.fhir.R4.fhir_document_reference import Attachment
from models.fhir.R4.fhir_document_reference import (
    DocumentReference as FhirDocumentReference,
)
from models.fhir.R4.fhir_document_reference import DocumentReferenceContent
from services.put_fhir_document_reference_service import (
    PutFhirDocumentReferenceService
)
from tests.unit.conftest import APIM_API_URL
from tests.unit.conftest import (
    EXPECTED_PARSED_PATIENT_BASE_CASE as mock_pds_patient_details,
)
from tests.unit.helpers.data.bulk_upload.test_data import TEST_DOCUMENT_REFERENCE
from utils.exceptions import PatientNotFoundException
from utils.lambda_exceptions import UpdateFhirDocumentReferenceException
from tests.unit.helpers.data.test_documents import create_test_doc_store_refs


@pytest.fixture
def mock_pds_service_fetch(mocker):
    mock_service_object = mocker.MagicMock()
    mocker.patch(
        "services.put_fhir_document_reference_service.get_pds_service",
        return_value=mock_service_object,
    )
    mock_service_object.fetch_patient_details.return_value = mock_pds_patient_details


@pytest.fixture
def mock_service(set_env, mocker, mock_pds_service_fetch):
    mock_s3 = mocker.patch("services.put_fhir_document_reference_service.S3Service")
    mock_dynamo = mocker.patch(
        "services.put_fhir_document_reference_service.DynamoDBService"
    )
    mock_document_service = mocker.patch("services.put_fhir_document_reference_service.DocumentService")
    service = PutFhirDocumentReferenceService()
    service.s3_service = mock_s3.return_value
    service.dynamo_service = mock_dynamo.return_value
    service.document_service = mock_document_service.return_value

    yield service


@pytest.fixture
def valid_fhir_doc_json():
    return json.dumps(
        {
            "resourceType": "DocumentReference",
            "docStatus": "final",
            "status": "current",
            "subject": {
                "identifier": {
                    "system": "https://fhir.nhs.uk/Id/nhs-number",
                    "value": "9000000009",
                }
            },
            "type": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": SnomedCodes.LLOYD_GEORGE.value.code,
                        "display": SnomedCodes.LLOYD_GEORGE.value.display_name,
                    }
                ]
            },
            "custodian": {
                "identifier": {
                    "system": "https://fhir.nhs.uk/Id/ods-organization-code",
                    "value": "A12345",
                }
            },
            "author": [
                {
                    "identifier": {
                        "system": "https://fhir.nhs.uk/Id/ods-organization-code",
                        "value": "A12345",
                    }
                }
            ],
            "content": [
                {
                    "attachment": {
                        "contentType": "application/pdf",
                        "language": "en-GB",
                        "title": "test-file.pdf",
                        "creation": "2023-01-01T12:00:00Z",
                    }
                }
            ],
            "meta": {
                "versionId": "1"
            }
        }
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
    mock_service, valid_fhir_doc_json, version_number
):
    mock_presigned_url_response = "https://test-bucket.s3.amazonaws.com/"

    mock_service.s3_service.create_put_presigned_url.return_value = (
        mock_presigned_url_response
    )

    documents = create_test_doc_store_refs()
    documents[0].version = str(version_number)
    doc = json.loads(valid_fhir_doc_json)
    doc["meta"]["versionId"] = str(version_number)
    valid_fhir_doc_json = json.dumps(doc)

    mock_service.document_service.fetch_documents_from_table.return_value = documents

    result = mock_service.process_fhir_document_reference(valid_fhir_doc_json)
    expected_pre_sign_url = mock_presigned_url_response

    assert isinstance(result, str)
    result_json = json.loads(result)
    assert result_json["resourceType"] == "DocumentReference"
    assert result_json["content"][0]["attachment"]["url"] == expected_pre_sign_url

    mock_service.s3_service.create_put_presigned_url.assert_called_once()
    mock_service.dynamo_service.create_item.assert_called_once()
    mock_service.s3_service.upload_file_obj.assert_not_called()

    assert mock_service.dynamo_service.create_item.call_args.args[1]["Version"] == str(version_number + 1)


@pytest.mark.parametrize(
        "version_number",
        range(1, 10)
)
def test_process_fhir_document_reference_with_binary(
    mock_service, valid_fhir_doc_with_binary, version_number
):
    """Test a happy path with binary data in the request."""
    custom_endpoint = f"{APIM_API_URL}/DocumentReference"

    documents = create_test_doc_store_refs()
    documents[0].version = str(version_number)
    doc = json.loads(valid_fhir_doc_with_binary)
    doc["meta"]["versionId"] = str(version_number)
    valid_fhir_doc_with_binary = json.dumps(doc)

    mock_service.document_service.fetch_documents_from_table.return_value = documents

    result = mock_service.process_fhir_document_reference(valid_fhir_doc_with_binary)

    assert isinstance(result, str)
    result_json = json.loads(result)
    assert result_json["resourceType"] == "DocumentReference"
    attachment_url = result_json["content"][0]["attachment"]["url"]
    assert custom_endpoint in attachment_url

    mock_service.s3_service.upload_file_obj.assert_called_once()
    mock_service.dynamo_service.create_item.assert_called_once()
    mock_service.s3_service.create_upload_presigned_url.assert_not_called()

    assert mock_service.dynamo_service.create_item.call_args.args[1]["Version"] == str(version_number + 1)


def test_validation_error(mock_service):
    """Test handling of an invalid FHIR document."""
    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service.process_fhir_document_reference("{invalid json}")

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.CreateDocNoParse


@pytest.mark.parametrize(
    "modify_doc, expected_error",
    [
        # Missing NHS number (wrong system)
        (
            lambda doc: {
                **doc,
                "type": {"coding": [{"system": "wrong-system", "code": "9000000009"}]},
            },
            LambdaError.CreateDocInvalidType,
        ),
        # Invalid document type
        (
            lambda doc: {
                **doc,
                "type": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "invalid-code",
                            "display": "Invalid",
                        }
                    ]
                },
            },
            LambdaError.CreateDocInvalidType,
        ),
        # Missing document type
        (lambda doc: {**doc, "type": {"coding": []}}, LambdaError.CreateDocInvalidType),
    ],
)
def test_document_validation_errors(
    mock_service, valid_fhir_doc_json, modify_doc, expected_error
):
    """Test validation error scenarios."""
    doc = json.loads(valid_fhir_doc_json)
    modified_doc = FhirDocumentReference(**modify_doc(doc))

    with pytest.raises(UpdateFhirDocumentReferenceException) as e:
        mock_service._determine_document_type(modified_doc)

    assert e.value.status_code == 400
    assert e.value.error == expected_error


def test_dynamo_error(mock_service, valid_fhir_doc_json):
    """Test handling of DynamoDB error."""
    mock_service.dynamo_service.create_item.side_effect = ClientError(
        {"Error": {"Code": "InternalServerError", "Message": "Test error"}},
        "CreateItem",
    )

    documents = create_test_doc_store_refs()
    documents[0].version = "1"
    mock_service.document_service.fetch_documents_from_table.return_value = documents

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service.process_fhir_document_reference(valid_fhir_doc_json)

    assert excinfo.value.status_code == 500
    assert excinfo.value.error == LambdaError.CreateDocUploadInternalError


def test_save_document_reference_to_dynamo_error(mock_service, mocker):
    """Test _save_document_reference_to_dynamo method with DynamoDB error."""

    mock_service.dynamo_service.create_item.side_effect = ClientError(
        {"Error": {"Code": "InternalServerError", "Message": "Test error"}},
        "CreateItem",
    )
    document_ref = DocumentReference(
        id="test-id",
        nhs_number="9000000009",
        current_gp_ods="A12345",
        custodian="A12345",
        s3_bucket_name="test-bucket",
        content_type="application/pdf",
        file_name="test-file.pdf",
        document_snomed_code_type="test-code",
    )

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service._save_document_reference_to_dynamo("test-table", document_ref)

    assert excinfo.value.status_code == 500
    assert excinfo.value.error == LambdaError.CreateDocUploadInternalError

    mock_service.dynamo_service.create_item.assert_called_once()


def test_pds_error(mock_service, valid_fhir_doc_json, mocker):
    """Test handling of PDS error."""

    mock_service._check_nhs_number_with_pds = mocker.MagicMock()
    mock_service._check_nhs_number_with_pds.side_effect = UpdateFhirDocumentReferenceException(
        400, LambdaError.MockError
    )

    documents = create_test_doc_store_refs()
    mock_service.document_service.fetch_documents_from_table.return_value = documents

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service.process_fhir_document_reference(valid_fhir_doc_json)
    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.MockError


def test_process_fhir_document_reference_with_pds_error(
    mock_service, valid_fhir_doc_json, mocker
):
    """Test process_fhir_document_reference with a real PDS error (PatientNotFoundException)."""
    pds_service_mock = mocker.MagicMock()
    mocker.patch(
        "services.put_fhir_document_reference_service.get_pds_service",
        return_value=pds_service_mock,
    )
    pds_service_mock.fetch_patient_details.side_effect = PatientNotFoundException(
        "Patient not found"
    )

    documents = create_test_doc_store_refs()
    mock_service.document_service.fetch_documents_from_table.return_value = documents

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service.process_fhir_document_reference(valid_fhir_doc_json)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.CreatePatientSearchInvalid


def test_s3_presigned_url_error(mock_service, valid_fhir_doc_json):
    """Test handling of S3 presigned URL error."""
    mock_service.s3_service.create_put_presigned_url.side_effect = ClientError(
        {"Error": {"Code": "InternalServerError", "Message": "Test error"}},
        "CreatePresignedUrl",
    )

    documents = create_test_doc_store_refs()
    mock_service.document_service.fetch_documents_from_table.return_value = documents

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service.process_fhir_document_reference(valid_fhir_doc_json)

    assert excinfo.value.status_code == 500
    assert excinfo.value.error == LambdaError.InternalServerError


def test_s3_upload_error(mock_service, valid_fhir_doc_with_binary):
    """Test handling of S3 upload error."""
    mock_service.s3_service.upload_file_obj.side_effect = ClientError(
        {"Error": {"Code": "InternalServerError", "Message": "Test error"}}, "PutObject"
    )

    documents = create_test_doc_store_refs()
    mock_service.document_service.fetch_documents_from_table.return_value = documents

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service.process_fhir_document_reference(valid_fhir_doc_with_binary)

    assert excinfo.value.status_code == 500
    assert excinfo.value.error == LambdaError.CreateDocNoParse


def test_check_nhs_number_with_pds_raise_error(mock_service, mocker):
    """Test handling of PDS error."""
    mock_service_object = mocker.MagicMock()
    mocker.patch(
        "services.put_fhir_document_reference_service.get_pds_service",
        return_value=mock_service_object,
    )
    mock_service_object.fetch_patient_details.side_effect = PatientNotFoundException(
        "test test"
    )
    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service._check_nhs_number_with_pds("9000000009")
    assert excinfo.value.status_code == 400


def test_extract_nhs_number_from_fhir_with_invalid_system(mock_service, mocker):
    """Test _extract_nhs_number_from_fhir method with an invalid NHS number system."""

    fhir_doc = mocker.MagicMock(spec=FhirDocumentReference)
    fhir_doc.subject = Reference(
        identifier=Identifier(system="invalid-system", value="9000000009")
    )

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service._extract_nhs_number_from_fhir(fhir_doc)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.CreateDocNoParse


def test_get_dynamo_table_for_non_lloyd_george_doc_type(mock_service):
    """Test _get_dynamo_table_for_doc_type method with a non-Lloyd George document type."""

    non_lg_code = SnomedCode(code="non-lg-code", display_name="Non Lloyd George")

    result = mock_service._get_dynamo_table_for_doc_type(non_lg_code)

    assert result == mock_service.arf_dynamo_table


def test_create_document_reference_with_author(mock_service, mocker):
    """Test _create_document_reference method with author information included."""

    fhir_doc = mocker.MagicMock(spec=FhirDocumentReference)
    fhir_doc.content = [
        DocumentReferenceContent(
            attachment=Attachment(
                contentType="application/pdf",
                title="test-file.pdf",
                creation="2023-01-01T12:00:00Z",
            )
        )
    ]
    fhir_doc.custodian = Reference(
        identifier=Identifier(
            system="https://fhir.nhs.uk/Id/ods-organization-code", value="A12345"
        )
    )
    fhir_doc.author = [
        Reference(
            identifier=Identifier(
                system="https://fhir.nhs.uk/Id/ods-organization-code", value="B67890"
            )
        )
    ]

    doc_type = SnomedCode(code="test-code", display_name="Test Type")

    result = mock_service._create_document_reference(
        nhs_number="9000000009",
        doc_type=doc_type,
        fhir_doc=fhir_doc,
        current_gp_ods="C13579",
        version="2",
    )

    assert result.nhs_number == "9000000009"
    assert result.document_snomed_code_type == "test-code"
    assert result.custodian == "A12345"
    assert result.current_gp_ods == "C13579"
    assert result.author == "B67890"  # Verify author is set


def test_create_document_reference_without_custodian(mock_service, mocker):
    """Test _create_document_reference method without custodian information."""

    fhir_doc = mocker.MagicMock(spec=FhirDocumentReference)
    fhir_doc.content = [
        DocumentReferenceContent(
            attachment=Attachment(
                contentType="application/pdf",
                title="test-file.pdf",
                creation="2023-01-01T12:00:00Z",
            )
        )
    ]
    fhir_doc.author = [
        Reference(
            identifier=Identifier(
                system="https://fhir.nhs.uk/Id/ods-organization-code", value="B67890"
            )
        )
    ]
    fhir_doc.custodian = None

    doc_type = SnomedCode(code="test-code", display_name="Test Type")
    current_gp_ods = "C13579"

    result = mock_service._create_document_reference(
        nhs_number="9000000009",
        doc_type=doc_type,
        fhir_doc=fhir_doc,
        current_gp_ods=current_gp_ods,
        version="2",
    )

    assert (
        result.custodian == current_gp_ods
    )  # Custodian should default to current_gp_ods


def test_create_fhir_response_with_presigned_url(mock_service, mocker):
    """Test _create_fhir_response method with a presigned URL."""

    mocker.patch.object(
        SnomedCodes, "find_by_code", return_value=SnomedCodes.LLOYD_GEORGE.value
    )

    document_ref = DocumentReference(
        id="test-id",
        nhs_number="9000000009",
        current_gp_ods="A12345",
        custodian="A12345",
        s3_bucket_name="test-bucket",
        content_type="application/pdf",
        file_name="test-file.pdf",
        document_snomed_code_type=SnomedCodes.LLOYD_GEORGE.value.code,
        document_scan_creation="2023-01-01T12:00:00Z",
    )
    presigned_url = "https://test-presigned-url.com"

    result = mock_service._create_fhir_response(document_ref, presigned_url)

    result_json = json.loads(result)
    assert result_json["resourceType"] == "DocumentReference"
    assert result_json["content"][0]["attachment"]["url"] == presigned_url


def test_create_fhir_response_without_presigned_url(mock_service, mocker):
    """Test _create_fhir_response method without a presigned URL (for binary uploads)."""

    mocker.patch.object(
        SnomedCodes, "find_by_code", return_value=SnomedCodes.LLOYD_GEORGE.value
    )
    custom_endpoint = f"{APIM_API_URL}/DocumentReference"

    document_ref = DocumentReference(
        id="test-id",
        nhs_number="9000000009",
        current_gp_ods="A12345",
        custodian="A12345",
        s3_bucket_name="test-bucket",
        content_type="application/pdf",
        file_name="test-file.pdf",
        document_snomed_code_type=SnomedCodes.LLOYD_GEORGE.value.code,
        document_scan_creation="2023-01-01T12:00:00Z",
    )

    result = mock_service._create_fhir_response(document_ref, None)

    result_json = json.loads(result)
    assert result_json["resourceType"] == "DocumentReference"
    expected_url = (
        f"{custom_endpoint}/{SnomedCodes.LLOYD_GEORGE.value.code}~{document_ref.id}"
    )
    assert result_json["content"][0]["attachment"]["url"] == expected_url


def test_extract_nhs_number_from_fhir_with_missing_identifier(mock_service, mocker):
    """Test _extract_nhs_number_from_fhir method when identifier is missing."""
    fhir_doc = mocker.MagicMock(spec=FhirDocumentReference)
    fhir_doc.subject = Reference(identifier=None)

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service._extract_nhs_number_from_fhir(fhir_doc)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.CreateDocNoParse


def test_determine_document_type_with_missing_type(mock_service, mocker):
    """Test _determine_document_type method when type is missing entirely."""
    fhir_doc = mocker.MagicMock(spec=FhirDocumentReference)
    fhir_doc.type = None

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service._determine_document_type(fhir_doc)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.CreateDocInvalidType


def test_determine_document_type_with_missing_coding(mock_service, mocker):
    """Test _determine_document_type method when coding is missing."""
    fhir_doc = mocker.MagicMock(spec=FhirDocumentReference)
    fhir_doc.type = mocker.MagicMock()
    fhir_doc.type.coding = None

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service._determine_document_type(fhir_doc)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.CreateDocInvalidType


def test_get_dynamo_table_for_lloyd_george_doc_type(mock_service):
    """Test _get_dynamo_table_for_doc_type method with Lloyd George document type."""
    lg_code = SnomedCodes.LLOYD_GEORGE.value

    result = mock_service._get_dynamo_table_for_doc_type(lg_code)

    assert result == mock_service.lg_dynamo_table


def test_process_fhir_document_reference_with_malformed_json(mock_service):
    """Test process_fhir_document_reference with malformed JSON."""
    malformed_json = '{"resourceType": "DocumentReference", "invalid": }'

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service.process_fhir_document_reference(malformed_json)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.CreateDocNoParse


def test_process_fhir_document_reference_with_empty_string(mock_service):
    """Test process_fhir_document_reference with an empty string."""
    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service.process_fhir_document_reference("")

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.CreateDocNoParse


def test_process_fhir_document_reference_with_none(mock_service):
    """Test process_fhir_document_reference with None input."""
    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service.process_fhir_document_reference(None)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.CreateDocNoParse


def test_check_nhs_number_with_pds_success(mock_service, mocker):
    """Test successful NHS number validation with PDS."""
    mock_service_object = mocker.MagicMock()
    mocker.patch(
        "services.put_fhir_document_reference_service.get_pds_service",
        return_value=mock_service_object,
    )
    mock_service_object.fetch_patient_details.return_value = mock_pds_patient_details

    # This should not raise an exception
    result = mock_service._check_nhs_number_with_pds("9000000009")

    # Verify the method was called correctly
    mock_service_object.fetch_patient_details.assert_called_once_with("9000000009")
    assert result == mock_pds_patient_details


def test_save_document_reference_to_dynamo_success(mock_service):
    """Test successful save to DynamoDB."""
    document_ref = DocumentReference(
        id="test-id",
        nhs_number="9000000009",
        current_gp_ods="A12345",
        custodian="A12345",
        s3_bucket_name="test-bucket",
        content_type="application/pdf",
        file_name="test-file.pdf",
        document_snomed_code_type="test-code",
    )

    mock_service._save_document_reference_to_dynamo("test-table", document_ref)

    mock_service.dynamo_service.create_item.assert_called()


def test_store_binary_in_s3_success(mock_service, mocker):
    """Test successful binary storage in S3."""
    binary_data = b"SGVsbG8gV29ybGQ="  # Base64 encoded "Hello World"

    mock_service.s3_service.upload_file_obj.return_value = None

    mock_service._store_binary_in_s3(TEST_DOCUMENT_REFERENCE, binary_data)

    mock_service.s3_service.upload_file_obj.assert_called_once_with(
        file_obj=mocker.ANY,
        s3_bucket_name=TEST_DOCUMENT_REFERENCE.s3_bucket_name,
        file_key=TEST_DOCUMENT_REFERENCE.s3_file_key,
    )


def test_store_binary_in_s3_with_client_error(mock_service):
    """Test _store_binary_in_s3 method with S3 ClientError."""
    binary_data = b"SGVsbG8gV29ybGQ="

    mock_service.s3_service.upload_file_obj.side_effect = ClientError(
        {
            "Error": {
                "Code": "NoSuchBucket",
                "Message": "The specified bucket does not exist",
            }
        },
        "PutObject",
    )

    with pytest.raises(UpdateFhirDocumentReferenceException) as excinfo:
        mock_service._store_binary_in_s3(TEST_DOCUMENT_REFERENCE, binary_data)

    assert excinfo.value.status_code == 500
    assert excinfo.value.error == LambdaError.CreateDocNoParse


def test_store_binary_in_s3_with_large_binary_data(mock_service):
    """Test _store_binary_in_s3 method with large binary data."""
    # Create a large binary data (8MB)
    binary_data = b"A" * (8 * 1024 * 1024)

    mock_service._store_binary_in_s3(TEST_DOCUMENT_REFERENCE, binary_data)

    mock_service.s3_service.upload_file_obj.assert_called_once()


def test_process_fhir_document_reference_with_invalid_base64_data(mock_service):
    """Test process_fhir_document_reference with invalid base64 data."""
    with pytest.raises(UpdateFhirDocumentReferenceException):
        mock_service._store_binary_in_s3(
            TEST_DOCUMENT_REFERENCE, b"invalid-base64-data!!!"
        )