from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError
from enums.virus_scan_result import VirusScanResult
from models.document_reference import DocumentReference
from services.mock_virus_scan_service import MockVirusScanService
from services.upload_document_reference_service import UploadDocumentReferenceService
from tests.unit.conftest import (
    MOCK_LG_BUCKET,
    MOCK_LG_TABLE_NAME,
    MOCK_PDM_BUCKET,
    MOCK_PDM_TABLE_NAME,
    MOCK_STAGING_STORE_BUCKET,
)
from utils.common_query_filters import PreliminaryStatus
from utils.exceptions import DocumentServiceException, FileProcessingException

from lambdas.enums.snomed_codes import SnomedCodes


@pytest.fixture
def mock_document_reference():
    """Create a mock document reference"""
    doc_ref = Mock(spec=DocumentReference)
    doc_ref.id = "test-doc-id"
    doc_ref.nhs_number = "9000000001"
    doc_ref.s3_file_key = "original/test-key"
    doc_ref.s3_bucket_name = "original-bucket"
    doc_ref.file_location = "original-location"
    doc_ref.virus_scanner_result = None
    doc_ref.file_size = 1234567890
    doc_ref.doc_status = "uploading"
    doc_ref._build_s3_location = Mock(
        return_value="s3://test-lg-bucket/9000000001/test-doc-id"
    )
    return doc_ref


@pytest.fixture
def mock_pdm_document_reference():
    """Create a mock document reference"""
    doc_ref = Mock(spec=DocumentReference)
    doc_ref.id = "test-doc-id"
    doc_ref.nhs_number = "9000000001"
    doc_ref.s3_file_key = (
        f"fhir_upload/{SnomedCodes.PATIENT_DATA.value.code}/9000000001/test-doc-id"
    )
    doc_ref.s3_bucket_name = "test-staging-bucket"
    doc_ref.virus_scanner_result = None
    doc_ref.file_size = 1234567890
    doc_ref.doc_status = "uploading"
    doc_ref._build_s3_location = Mock(
        return_value=f"s3://test-staging-bucket/fhir_upload/{SnomedCodes.PATIENT_DATA.value.code}/9000000001/test-doc-id"
    )
    return doc_ref


@pytest.fixture
def mock_virus_scan_service(
    mocker,
):
    mock = mocker.patch(
        "services.upload_document_reference_service.get_virus_scan_service"
    )
    yield mock


@pytest.fixture
def service(set_env, mock_virus_scan_service):
    with patch.multiple(
        "services.upload_document_reference_service",
        DocumentService=Mock(),
        DynamoDBService=Mock(),
        S3Service=Mock(),
    ):
        service = UploadDocumentReferenceService()
        service.document_service = Mock()
        service.dynamo_service = Mock()
        service.virus_scan_service = MockVirusScanService()
        service.s3_service = Mock()
        return service


@pytest.fixture
def pdm_service(set_env, mock_virus_scan_service):
    with patch.multiple(
        "services.upload_document_reference_service",
        DocumentService=Mock(),
        DynamoDBService=Mock(),
        S3Service=Mock(),
    ):
        service = UploadDocumentReferenceService()
        service.document_service = Mock()
        service.dynamo_service = Mock()
        service.virus_scan_service = MockVirusScanService()
        service.s3_service = Mock()
        service.table_name = MOCK_PDM_TABLE_NAME
        service.destination_bucket_name = MOCK_PDM_BUCKET
        return service


def test_handle_upload_document_reference_request_with_empty_object_key(service):
    """Test handling of an empty object key"""
    service.handle_upload_document_reference_request("", 122)

    service.document_service.fetch_documents_from_table.assert_not_called()


def test_handle_upload_document_reference_request_with_none_object_key(service):
    """Test handling of a None object key"""
    service.handle_upload_document_reference_request(None, 122)

    service.document_service.fetch_documents_from_table.assert_not_called()


def test_handle_upload_document_reference_request_success(
    service, mock_document_reference, mocker
):
    """Test successful handling of the upload document reference request"""
    object_key = "staging/test-doc-id"
    object_size = 1111
    service.document_service.fetch_documents_from_table.return_value = [
        mock_document_reference
    ]
    service.virus_scan_service.scan_file = mocker.MagicMock(
        return_value=VirusScanResult.CLEAN
    )

    service.handle_upload_document_reference_request(object_key, object_size)

    service.document_service.fetch_documents_from_table.assert_called_once()
    service.document_service.update_document.assert_called_once()
    service.s3_service.copy_across_bucket.assert_called_once()
    service.s3_service.delete_object.assert_called_once()
    service.virus_scan_service.scan_file.assert_called_once()


def test_handle_upload_document_reference_request_with_exception(service):
    """Test handling of exceptions during processing"""
    object_key = "staging/test-doc-id"

    service.document_service.fetch_documents_from_table.side_effect = Exception(
        "Test error"
    )

    service.handle_upload_document_reference_request(object_key)


def test_fetch_document_reference_success(service, mock_document_reference):
    """Test successful document reference fetching"""
    document_key = "test-doc-id"
    service.document_service.fetch_documents_from_table.return_value = [
        mock_document_reference
    ]

    result = service._fetch_document_reference(document_key)

    assert result == mock_document_reference
    service.document_service.fetch_documents_from_table.assert_called_once_with(
        table=MOCK_LG_TABLE_NAME,
        search_condition=document_key,
        search_key="ID",
        query_filter=PreliminaryStatus,
    )


def test_fetch_document_reference_no_documents_found(service):
    """Test handling when no documents are found"""
    document_key = "test-doc-id"
    service.document_service.fetch_documents_from_table.return_value = []

    result = service._fetch_document_reference(document_key)

    assert result is None


def test_fetch_document_reference_multiple_documents_warning(
    service, mock_document_reference
):
    """Test handling when multiple documents are found"""
    document_key = "test-doc-id"
    mock_doc_2 = Mock(spec=DocumentReference)
    service.document_service.fetch_documents_from_table.return_value = [
        mock_document_reference,
        mock_doc_2,
    ]

    result = service._fetch_document_reference(document_key)

    assert result == mock_document_reference


def test_fetch_document_reference_exception(service):
    """Test handling of exceptions during document fetching"""
    document_key = "test-doc-id"
    service.document_service.fetch_documents_from_table.side_effect = (
        ClientError({"error": "test error message"}, "test"),
    )

    with pytest.raises(DocumentServiceException):
        service._fetch_document_reference(document_key)


def test_process_document_reference_clean_virus_scan(
    service, mock_document_reference, mocker
):
    """Test processing document reference with a clean virus scan"""
    object_key = "staging/test-doc-id"

    mocker.patch.object(
        service, "_perform_virus_scan", return_value=VirusScanResult.CLEAN
    )
    mock_process_clean = mocker.patch.object(service, "_process_clean_document")
    mock_update_dynamo = mocker.patch.object(service, "update_dynamo_table")
    service._process_document_reference(mock_document_reference, object_key, 1222)

    mock_process_clean.assert_called_once()
    mock_update_dynamo.assert_called_once()


def test_process_document_reference_infected_virus_scan(
    service, mock_document_reference, mocker
):
    """Test processing document reference with an infected virus scan"""
    object_key = "staging/test-doc-id"

    mocker.patch.object(
        service, "_perform_virus_scan", return_value=VirusScanResult.INFECTED
    )
    mock_process_clean = mocker.patch.object(service, "_process_clean_document")
    mock_update_dynamo = mocker.patch.object(service, "update_dynamo_table")
    service._process_document_reference(mock_document_reference, object_key, 1222)

    mock_process_clean.assert_not_called()
    mock_update_dynamo.assert_called_once()


def test_perform_virus_scan_returns_clean_hardcoded(service, mock_document_reference):
    """Test virus scan returns hardcoded CLEAN result"""

    result = service._perform_virus_scan(mock_document_reference)
    assert result == VirusScanResult.CLEAN


def test_perform_virus_scan_exception_returns_infected(
    service, mock_document_reference, mocker
):
    """Test virus scan exception handling returns INFECTED for safety"""
    mock_virus_service = mocker.patch.object(service, "virus_scan_service")
    mock_virus_service.scan_file.side_effect = Exception("Scan error")

    result = service._perform_virus_scan(mock_document_reference)

    assert result == VirusScanResult.ERROR


def test_process_clean_document_success(service, mock_document_reference, mocker):
    """Test successful processing of a clean document"""
    object_key = "staging/test-doc-id"

    mock_copy = mocker.patch.object(service, "copy_files_from_staging_bucket")
    mock_delete = mocker.patch.object(service, "delete_file_from_staging_bucket")

    service._process_clean_document(
        mock_document_reference,
        object_key,
    )

    mock_copy.assert_called_once_with(mock_document_reference, object_key)
    mock_delete.assert_called_once_with(object_key)


def test_process_clean_document_exception_restores_original_values(
    service, mock_document_reference, mocker
):
    """Test that original values are restored when processing fails"""
    object_key = "staging/test-doc-id"
    original_s3_key = "original/test-key"
    original_bucket = "original-bucket"
    original_location = "original-location"

    mocker.patch.object(
        service, "copy_files_from_staging_bucket", side_effect=Exception("Copy failed")
    )
    with pytest.raises(FileProcessingException):
        service._process_clean_document(
            mock_document_reference,
            object_key,
        )

    assert mock_document_reference.s3_file_key == original_s3_key
    assert mock_document_reference.s3_bucket_name == original_bucket
    assert mock_document_reference.file_location == original_location
    assert mock_document_reference.doc_status == "cancelled"


def test_copy_files_from_staging_bucket_success(service, mock_document_reference):
    """Test successful file copying from staging bucket"""
    source_file_key = "staging/test-doc-id"
    expected_dest_key = (
        f"{mock_document_reference.nhs_number}/{mock_document_reference.id}"
    )

    service.copy_files_from_staging_bucket(mock_document_reference, source_file_key)

    service.s3_service.copy_across_bucket.assert_called_once_with(
        source_bucket=MOCK_STAGING_STORE_BUCKET,
        source_file_key=source_file_key,
        dest_bucket=MOCK_LG_BUCKET,
        dest_file_key=expected_dest_key,
    )

    assert mock_document_reference.s3_file_key == expected_dest_key
    assert mock_document_reference.s3_bucket_name == MOCK_LG_BUCKET


def test_copy_files_from_staging_bucket_client_error(service, mock_document_reference):
    """Test handling of ClientError during file copying"""
    source_file_key = "staging/test-doc-id"
    client_error = ClientError(
        error_response={
            "Error": {"Code": "NoSuchBucket", "Message": "Bucket does not exist"}
        },
        operation_name="CopyObject",
    )
    service.s3_service.copy_across_bucket.side_effect = client_error

    with pytest.raises(FileProcessingException):
        service.copy_files_from_staging_bucket(mock_document_reference, source_file_key)


def test_delete_file_from_staging_bucket_success(service):
    """Test successful file deletion from staging bucket"""
    source_file_key = "staging/test-doc-id"

    service.delete_file_from_staging_bucket(source_file_key)

    service.s3_service.delete_object.assert_called_once_with(
        MOCK_STAGING_STORE_BUCKET, source_file_key
    )


def test_delete_pdm_file_from_staging_bucket_success(service):
    """Test successful file deletion from staging bucket"""
    source_file_key = (
        f"fhir_upload/{SnomedCodes.PATIENT_DATA.value.code}/staging/test-doc-id"
    )

    service.delete_file_from_staging_bucket(source_file_key)

    service.s3_service.delete_object.assert_called_once_with(
        MOCK_STAGING_STORE_BUCKET, source_file_key
    )


def test_delete_file_from_staging_bucket_client_error(service):
    """Test handling of ClientError during file deletion"""
    source_file_key = "staging/test-doc-id"
    client_error = ClientError(
        error_response={
            "Error": {"Code": "NoSuchKey", "Message": "Key does not exist"}
        },
        operation_name="DeleteObject",
    )
    service.s3_service.delete_object.side_effect = client_error

    # Should not raise exception, just log the error
    try:
        service.delete_file_from_staging_bucket(source_file_key)
    except Exception as e:
        assert False, f"Unexpected exception: {e}"


def test_update_dynamo_table_clean_scan_result(service, mock_document_reference):
    """Test updating DynamoDB table with a clean scan result"""
    scan_result = VirusScanResult.CLEAN

    service.update_dynamo_table(mock_document_reference, scan_result)

    assert mock_document_reference.doc_status == "final"
    service.document_service.update_document.assert_called_once_with(
        table_name=MOCK_LG_TABLE_NAME,
        document_reference=mock_document_reference,
        update_fields_name={
            "virus_scanner_result",
            "doc_status",
            "file_location",
            "file_size",
            "uploaded",
            "uploading",
        },
    )


def test_update_dynamo_table_infected_scan_result(service, mock_document_reference):
    """Test updating DynamoDB table with an infected scan result"""
    scan_result = VirusScanResult.INFECTED

    service.update_dynamo_table(mock_document_reference, scan_result)

    assert mock_document_reference.doc_status == "cancelled"
    service.document_service.update_document.assert_called_once()


def test_update_dynamo_table_client_error(service, mock_document_reference):
    """Test handling of ClientError during DynamoDB update"""
    scan_result = VirusScanResult.CLEAN
    client_error = ClientError(
        error_response={
            "Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}
        },
        operation_name="UpdateItem",
    )
    service.document_service.update_document.side_effect = client_error

    with pytest.raises(DocumentServiceException):
        service.update_dynamo_table(mock_document_reference, scan_result)


def test_integration_full_workflow_clean_document(service, mock_document_reference):
    """Test full workflow integration for a clean document"""
    object_key = "staging/test-doc-id"

    service.document_service.fetch_documents_from_table.return_value = [
        mock_document_reference
    ]

    service.handle_upload_document_reference_request(object_key)

    service.document_service.fetch_documents_from_table.assert_called_once()
    service.s3_service.copy_across_bucket.assert_called_once()
    service.s3_service.delete_object.assert_called_once()
    service.document_service.update_document.assert_called_once()

    assert mock_document_reference.virus_scanner_result == VirusScanResult.CLEAN
    assert mock_document_reference.doc_status == "final"


@pytest.mark.parametrize(
    "object_key,expected_document_key,expected_table",
    [
        (
            "staging/documents/test-doc-123",
            "test-doc-123",
            MOCK_LG_TABLE_NAME,
        ),
        ("folder/subfolder/another-doc", "another-doc", MOCK_LG_TABLE_NAME),
        ("simple-doc", "simple-doc", MOCK_LG_TABLE_NAME),
        (
            f"fhir_upload/{SnomedCodes.PATIENT_DATA.value.code}/staging/test-doc-123",
            "test-doc-123",
            MOCK_PDM_TABLE_NAME,
        ),
        (
            f"{SnomedCodes.LLOYD_GEORGE.value.code}/staging/test-doc-123",
            "test-doc-123",
            MOCK_LG_TABLE_NAME,
        ),
        (
            f"fhir_upload/{SnomedCodes.LLOYD_GEORGE.value.code}/staging/test-doc-123",
            "test-doc-123",
            MOCK_LG_TABLE_NAME,
        ),
    ],
)
def test_document_type_extraction_from_object_key(
    service,
    mock_document_reference,
    object_key,
    expected_document_key,
    expected_table,
):
    """Test extraction of a document key from various object key formats"""
    service.document_service.fetch_documents_from_table.return_value = [
        mock_document_reference
    ]

    service.handle_upload_document_reference_request(object_key)

    service.document_service.fetch_documents_from_table.assert_called_with(
        table=expected_table,
        search_condition=expected_document_key,
        search_key="ID",
        query_filter=PreliminaryStatus,
    )


def test_handle_upload_pdm_document_reference_request_success(
    service, mock_document_reference, mocker
):
    """Test successful handling of the upload document reference request"""
    pdm_snomed = SnomedCodes.PATIENT_DATA.value
    object_key = f"fhir_upload/{pdm_snomed.code}/staging/test-doc-id"
    object_size = 1111
    service.document_service.fetch_documents_from_table.return_value = [
        mock_document_reference
    ]
    service.virus_scan_service.scan_file = mocker.MagicMock(
        return_value=VirusScanResult.CLEAN
    )

    service.handle_upload_document_reference_request(object_key, object_size)

    service.document_service.fetch_documents_from_table.assert_called_once()
    service.document_service.update_document.assert_called_once()
    service.s3_service.copy_across_bucket.assert_called_once()
    service.s3_service.delete_object.assert_called_once()
    service.virus_scan_service.scan_file.assert_called_once()


def test_copy_files_from_staging_bucket_to_pdm_success(
    pdm_service, mock_pdm_document_reference
):
    """Test successful file copying from staging bucket"""
    source_file_key = (
        f"fhir_upload/{SnomedCodes.PATIENT_DATA.value.code}/staging/test-doc-id"
    )
    expected_dest_key = (
        f"{mock_pdm_document_reference.nhs_number}/{mock_pdm_document_reference.id}"
    )
    pdm_service.copy_files_from_staging_bucket(
        mock_pdm_document_reference, source_file_key
    )
    pdm_service.s3_service.copy_across_bucket.assert_called_once_with(
        source_bucket=MOCK_STAGING_STORE_BUCKET,
        source_file_key=source_file_key,
        dest_bucket=MOCK_PDM_BUCKET,
        dest_file_key=expected_dest_key,
    )

    assert mock_pdm_document_reference.s3_file_key == expected_dest_key
    assert mock_pdm_document_reference.s3_bucket_name == MOCK_PDM_BUCKET
