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
    MOCK_STAGING_STORE_BUCKET,
)
from utils.common_query_filters import FinalStatusAndNotSuperceded, PreliminaryStatus
from utils.exceptions import DocumentServiceException, FileProcessingException


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
    mock_document_reference2 = Mock(spec=DocumentReference)
    mock_document_reference2.id = "another-doc-id"
    mock_document_reference2.doc_status = "final"
    
    # First call fetches preliminary doc, second call fetches existing final docs to supersede
    service.document_service.fetch_documents_from_table.side_effect = [
        [mock_document_reference],
        [mock_document_reference2]
    ]
    service.virus_scan_service.scan_file = mocker.MagicMock(
        return_value=VirusScanResult.CLEAN
    )

    service.handle_upload_document_reference_request(object_key, object_size)

    assert service.document_service.fetch_documents_from_table.call_count == 2
    service.dynamo_service.transact_write_items.assert_called_once()
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


def test_fetch_preliminary_document_reference_success(service, mock_document_reference):
    """Test successful document reference fetching"""
    document_key = "test-doc-id"
    service.document_service.fetch_documents_from_table.return_value = [
        mock_document_reference
    ]

    result = service._fetch_preliminary_document_reference(document_key)

    assert result == mock_document_reference
    service.document_service.fetch_documents_from_table.assert_called_once_with(
        table=MOCK_LG_TABLE_NAME,
        search_condition=document_key,
        search_key="ID",
        query_filter=PreliminaryStatus,
    )


def test_fetch_preliminary_document_reference_no_documents_found(service):
    """Test handling when no documents are found"""
    document_key = "test-doc-id"
    service.document_service.fetch_documents_from_table.return_value = []

    result = service._fetch_preliminary_document_reference(document_key)

    assert result is None


def test_fetch_preliminary_document_reference_multiple_documents_warning(
    service, mock_document_reference
):
    """Test handling when multiple documents are found"""
    document_key = "test-doc-id"
    mock_doc_2 = Mock(spec=DocumentReference)
    service.document_service.fetch_documents_from_table.return_value = [
        mock_document_reference,
        mock_doc_2,
    ]

    result = service._fetch_preliminary_document_reference(document_key)

    assert result == mock_document_reference


def test_fetch_preliminary_document_reference_exception(service):
    """Test handling of exceptions during document fetching"""
    document_key = "test-doc-id"
    service.document_service.fetch_documents_from_table.side_effect = (
        ClientError({"error": "test error message"}, "test"),
    )

    with pytest.raises(DocumentServiceException):
        service._fetch_preliminary_document_reference(document_key)


def test__process_preliminary_document_reference_clean_virus_scan(
    service, mock_document_reference, mocker
):
    """Test processing document reference with a clean virus scan"""
    object_key = "staging/test-doc-id"

    mocker.patch.object(
        service, "_perform_virus_scan", return_value=VirusScanResult.CLEAN
    )
    mock_process_clean = mocker.patch.object(service, "_process_clean_document")
    mock_finalize_transaction = mocker.patch.object(service, "_finalize_and_supersede_with_transaction")
    
    service._process_preliminary_document_reference(mock_document_reference, object_key, 1222)

    mock_process_clean.assert_called_once()
    mock_finalize_transaction.assert_called_once_with(mock_document_reference)
    assert mock_document_reference.doc_status == "final"
    assert mock_document_reference.uploaded is True
    assert mock_document_reference.uploading is False


def test__process_preliminary_document_reference_infected_virus_scan(
    service, mock_document_reference, mocker
):
    """Test processing document reference with an infected virus scan"""
    object_key = "staging/test-doc-id"

    mocker.patch.object(
        service, "_perform_virus_scan", return_value=VirusScanResult.INFECTED
    )
    mock_process_clean = mocker.patch.object(service, "_process_clean_document")
    mock_update_dynamo = mocker.patch.object(service, "_update_dynamo_table")
    service._process_preliminary_document_reference(mock_document_reference, object_key, 1222)

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
    service._update_dynamo_table(mock_document_reference)
    
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
    service._update_dynamo_table(mock_document_reference)

    service.document_service.update_document.assert_called_once()


def test_update_dynamo_table_client_error(service, mock_document_reference):
    """Test handling of ClientError during DynamoDB update"""
    client_error = ClientError(
        error_response={
            "Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}
        },
        operation_name="UpdateItem",
    )
    service.document_service.update_document.side_effect = client_error

    with pytest.raises(DocumentServiceException):
        service._update_dynamo_table(mock_document_reference)

@pytest.mark.parametrize(
    "object_key,expected_document_key,expected_nhs_number",
    [
        ("staging/documents/test-doc-123", "test-doc-123", "9000000001"),
        ("folder/subfolder/another-doc", "another-doc", "9000000001"),
        ("simple-doc", "simple-doc", "9000000001"),
    ],
)
def test_document_key_extraction_from_object_key(
    service, mock_document_reference, object_key, expected_document_key, expected_nhs_number
):
    """Test extraction of a document key from various object key formats"""
    # First call returns preliminary doc, second call returns empty list (no existing finals)
    service.document_service.fetch_documents_from_table.side_effect = [
        [mock_document_reference],
        []
    ]

    service.handle_upload_document_reference_request(object_key)

    # Verify the method was called twice
    assert service.document_service.fetch_documents_from_table.call_count == 2
    
    # Check first call (preliminary document)
    first_call = service.document_service.fetch_documents_from_table.call_args_list[0]
    assert first_call[1]['table'] == MOCK_LG_TABLE_NAME
    assert first_call[1]['search_condition'] == expected_document_key
    assert first_call[1]['search_key'] == "ID"
    
    # Check second call (existing final documents)
    second_call = service.document_service.fetch_documents_from_table.call_args_list[1]
    assert second_call[1]['table'] == MOCK_LG_TABLE_NAME
    assert second_call[1]['search_condition'] == expected_nhs_number
    assert second_call[1]['search_key'] == "NhsNumber"


def test_finalize_and_supersede_with_transaction_with_existing_finals(service, mock_document_reference, mocker):
    """Test transaction-based finalization with existing final documents to supersede"""
    new_doc = mock_document_reference
    new_doc.id = "new-doc-id"
    new_doc.nhs_number = "9000000001"
    new_doc.doc_status = "final"
    
    existing_final_doc = Mock(spec=DocumentReference)
    existing_final_doc.id = "old-doc-id"
    existing_final_doc.doc_status = "final"
    
    service.document_service.fetch_documents_from_table.return_value = [existing_final_doc]
    
    new_doc.model_dump = Mock(return_value={
        "VirusScannerResult": "Clean",
        "DocStatus": "final",
        "FileLocation": "s3://bucket/key",
        "FileSize": 1234,
        "Uploaded": True,
        "Uploading": False,
    })
    
    mock_build_update = Mock(return_value={"Update": "transaction1"})
    service.dynamo_service.build_update_transaction_item = mock_build_update
    
    service._finalize_and_supersede_with_transaction(new_doc)
    
    service.document_service.fetch_documents_from_table.assert_called_once_with(
        table=MOCK_LG_TABLE_NAME,
        index_name="NhsNumberIndex",
        search_condition=new_doc.nhs_number,
        search_key="NhsNumber",
        query_filter=FinalStatusAndNotSuperceded,
    )
    
    assert service.dynamo_service.build_update_transaction_item.call_count == 2
    service.dynamo_service.transact_write_items.assert_called_once()
    call_args = service.dynamo_service.transact_write_items.call_args[0][0]
    assert len(call_args) == 2  # Two transaction items


def test_finalize_and_supersede_with_transaction_no_existing_docs(service, mock_document_reference, mocker):
    """Test transaction-based finalization when no existing final documents found"""
    new_doc = mock_document_reference
    new_doc.id = "new-doc-id"
    new_doc.nhs_number = "9000000001"
    new_doc.doc_status = "final"
    
    service.document_service.fetch_documents_from_table.return_value = []
    
    new_doc.model_dump = Mock(return_value={
        "VirusScannerResult": "Clean",
        "DocStatus": "final",
        "FileLocation": "s3://bucket/key",
        "FileSize": 1234,
        "Uploaded": True,
        "Uploading": False,
    })
    
    mock_build_update = Mock(return_value={"Update": "transaction1"})
    service.dynamo_service.build_update_transaction_item = mock_build_update
    
    service._finalize_and_supersede_with_transaction(new_doc)
    
    service.document_service.fetch_documents_from_table.assert_called_once()
    assert service.dynamo_service.build_update_transaction_item.call_count == 1
    
    service.dynamo_service.transact_write_items.assert_called_once()
    call_args = service.dynamo_service.transact_write_items.call_args[0][0]
    assert len(call_args) == 1


def test_finalize_and_supersede_with_transaction_multiple_existing(service, mock_document_reference, mocker):
    """Test transaction-based finalization superseding multiple existing final documents"""
    new_doc = mock_document_reference
    new_doc.id = "new-doc-id"
    new_doc.nhs_number = "9000000001"
    new_doc.doc_status = "final"
    
    existing_doc1 = Mock(spec=DocumentReference)
    existing_doc1.id = "old-doc-1"
    existing_doc1.doc_status = "final"
    
    existing_doc2 = Mock(spec=DocumentReference)
    existing_doc2.id = "old-doc-2"
    existing_doc2.doc_status = "final"
    
    service.document_service.fetch_documents_from_table.return_value = [existing_doc1, existing_doc2]
    
    new_doc.model_dump = Mock(return_value={
        "VirusScannerResult": "Clean",
        "DocStatus": "final",
        "FileLocation": "s3://bucket/key",
        "FileSize": 1234,
        "Uploaded": True,
        "Uploading": False,
    })
    
    mock_build_update = Mock(return_value={"Update": "transaction"})
    service.dynamo_service.build_update_transaction_item = mock_build_update
    
    service._finalize_and_supersede_with_transaction(new_doc)
    
    assert service.dynamo_service.build_update_transaction_item.call_count == 3
    
    service.dynamo_service.transact_write_items.assert_called_once()
    call_args = service.dynamo_service.transact_write_items.call_args[0][0]
    assert len(call_args) == 3


def test_finalize_and_supersede_with_transaction_skips_same_id(service, mock_document_reference, mocker):
    """Test that transaction skips documents with the same ID"""
    new_doc = mock_document_reference
    new_doc.id = "same-doc-id"
    new_doc.nhs_number = "9000000001"
    new_doc.doc_status = "final"
    
    existing_doc = Mock(spec=DocumentReference)
    existing_doc.id = "same-doc-id"
    existing_doc.doc_status = "final"
    
    service.document_service.fetch_documents_from_table.return_value = [existing_doc]
    
    new_doc.model_dump = Mock(return_value={
        "VirusScannerResult": "Clean",
        "DocStatus": "final",
        "FileLocation": "s3://bucket/key",
        "FileSize": 1234,
        "Uploaded": True,
        "Uploading": False,
    })
    
    mock_build_update = Mock(return_value={"Update": "transaction"})
    service.dynamo_service.build_update_transaction_item = mock_build_update
    
    service._finalize_and_supersede_with_transaction(new_doc)
    
    # Should only build 1 transaction (for new doc, skipping same ID)
    assert service.dynamo_service.build_update_transaction_item.call_count == 1
    
    # Verify transaction was executed with only 1 item
    call_args = service.dynamo_service.transact_write_items.call_args[0][0]
    assert len(call_args) == 1


def test_finalize_and_supersede_with_transaction_handles_transaction_cancelled(service, mock_document_reference, mocker):
    """Test handling of TransactionCanceledException (concurrent update detected)"""
    from utils.exceptions import TransactionConflictException
    
    new_doc = mock_document_reference
    new_doc.id = "new-doc-id"
    new_doc.nhs_number = "9000000001"
    new_doc.doc_status = "final"
    
    service.document_service.fetch_documents_from_table.return_value = []
    
    # Mock model_dump
    new_doc.model_dump = Mock(return_value={
        "VirusScannerResult": "Clean",
        "DocStatus": "final",
        "FileLocation": "s3://bucket/key",
        "FileSize": 1234,
        "Uploaded": True,
        "Uploading": False,
    })
    
    mock_build_update = Mock(return_value={"Update": "transaction"})
    service.dynamo_service.build_update_transaction_item = mock_build_update
    
    # Simulate TransactionCanceledException
    transaction_error = ClientError(
        error_response={'Error': {'Code': 'TransactionCanceledException'}},
        operation_name='TransactWriteItems'
    )
    service.dynamo_service.transact_write_items.side_effect = transaction_error
    
    # Should raise TransactionConflictException
    with pytest.raises(TransactionConflictException):
        service._finalize_and_supersede_with_transaction(new_doc)


def test_handle_upload_document_reference_request_no_document_found(service):
    """Test handling when no preliminary document is found in database"""
    object_key = "staging/test-doc-id"
    object_size = 1234
    
    service.document_service.fetch_documents_from_table.return_value = []
    
    service.handle_upload_document_reference_request(object_key, object_size)
    
    # Should fetch but not proceed with processing
    service.document_service.fetch_documents_from_table.assert_called_once()
    service.s3_service.copy_across_bucket.assert_not_called()
    service.document_service.update_document.assert_not_called()


def test_process_preliminary_document_reference_exception_during_processing(
    service, mock_document_reference, mocker
):
    """Test that exceptions during processing are properly raised"""
    object_key = "staging/test-doc-id"
    
    mocker.patch.object(
        service, "_perform_virus_scan", return_value=VirusScanResult.CLEAN
    )
    mocker.patch.object(
        service, "_process_clean_document", side_effect=Exception("Processing failed")
    )
    
    with pytest.raises(Exception) as exc_info:
        service._process_preliminary_document_reference(
            mock_document_reference, object_key, 1222
        )
    
    assert "Processing failed" in str(exc_info.value)


