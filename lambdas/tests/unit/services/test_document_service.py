from datetime import datetime, timedelta
from unittest.mock import call

import pytest
from botocore.exceptions import ClientError
from enums.document_retention import DocumentRetentionDays
from enums.dynamo_filter import AttributeOperator
from enums.metadata_field_names import DocumentReferenceMetadataFields
from enums.supported_document_types import SupportedDocumentTypes
from freezegun import freeze_time
from models.document_reference import DocumentReference
from services.document_service import DocumentService
from tests.unit.conftest import (
    MOCK_ARF_TABLE_NAME,
    MOCK_LG_TABLE_NAME,
    MOCK_TABLE_NAME,
    TEST_NHS_NUMBER,
)
from tests.unit.helpers.data.dynamo.dynamo_responses import (
    MOCK_EMPTY_RESPONSE,
    MOCK_SEARCH_RESPONSE,
)
from tests.unit.helpers.data.test_documents import (
    create_test_lloyd_george_doc_store_refs,
)
from utils.common_query_filters import NotDeleted
from utils.dynamo_query_filter_builder import DynamoQueryFilterBuilder
from utils.exceptions import DocumentServiceException

MOCK_DOCUMENT = MOCK_SEARCH_RESPONSE["Items"][0]


@pytest.fixture
def mock_service(set_env, mocker):
    mocker.patch("services.document_service.S3Service")
    mocker.patch("services.document_service.DynamoDBService")
    service = DocumentService()
    yield service


@pytest.fixture
def mock_dynamo_service(mocker, mock_service):
    mocker.patch.object(mock_service.dynamo_service, "query_table_by_index")
    mocker.patch.object(mock_service.dynamo_service, "update_item")
    yield mock_service.dynamo_service


@pytest.fixture
def mock_s3_service(mocker, mock_service):
    mocker.patch.object(mock_service.s3_service, "create_object_tag")
    yield mock_service.s3_service


@pytest.fixture
def mock_filter_expression():
    filter_builder = DynamoQueryFilterBuilder()
    filter_expression = filter_builder.add_condition(
        attribute=str(DocumentReferenceMetadataFields.DELETED.value),
        attr_operator=AttributeOperator.EQUAL,
        filter_value="",
    ).build()
    yield filter_expression


def test_fetch_available_document_references_by_type_lg_returns_list_of_doc_references(
    mock_service, mock_dynamo_service, mock_filter_expression
):
    mock_dynamo_service.query_table.return_value = MOCK_SEARCH_RESPONSE["Items"]

    results = mock_service.fetch_available_document_references_by_type(
        TEST_NHS_NUMBER, SupportedDocumentTypes.LG, mock_filter_expression
    )

    assert len(results) == 3
    for result in results:
        assert isinstance(result, DocumentReference)

    mock_dynamo_service.query_table.assert_called_once_with(
        table_name=MOCK_LG_TABLE_NAME,
        index_name="NhsNumberIndex",
        search_key="NhsNumber",
        search_condition=TEST_NHS_NUMBER,
        query_filter=mock_filter_expression,
    )


def test_fetch_available_document_references_by_type_arf_returns_list_of_doc_references(
    mock_service, mock_dynamo_service, mock_filter_expression
):
    mock_dynamo_service.query_table.return_value = MOCK_SEARCH_RESPONSE["Items"]

    results = mock_service.fetch_available_document_references_by_type(
        TEST_NHS_NUMBER, SupportedDocumentTypes.ARF, mock_filter_expression
    )

    assert len(results) == 3
    for result in results:
        assert isinstance(result, DocumentReference)

    mock_dynamo_service.query_table.assert_called_once_with(
        table_name=MOCK_ARF_TABLE_NAME,
        index_name="NhsNumberIndex",
        search_key="NhsNumber",
        search_condition=TEST_NHS_NUMBER,
        query_filter=mock_filter_expression,
    )


def test_fetch_available_document_references_by_type_lg_returns_empty_list_of_doc_references(
    mock_service, mock_dynamo_service, mock_filter_expression
):
    mock_dynamo_service.query_table.return_value = MOCK_EMPTY_RESPONSE

    result = mock_service.fetch_available_document_references_by_type(
        TEST_NHS_NUMBER, SupportedDocumentTypes.LG, mock_filter_expression
    )
    assert len(result) == 0
    mock_dynamo_service.query_table.assert_called_once_with(
        table_name=MOCK_LG_TABLE_NAME,
        index_name="NhsNumberIndex",
        search_key="NhsNumber",
        search_condition=TEST_NHS_NUMBER,
        query_filter=mock_filter_expression,
    )


def test_fetch_documents_from_table_with_filter_returns_list_of_doc_references(
    mocker, mock_service, mock_dynamo_service, mock_filter_expression
):
    expected_calls = [
        mocker.call(
            table_name=MOCK_LG_TABLE_NAME,
            index_name="NhsNumberIndex",
            search_key="NhsNumber",
            search_condition=TEST_NHS_NUMBER,
            query_filter=mock_filter_expression,
        )
    ]

    mock_dynamo_service.query_table.return_value = MOCK_SEARCH_RESPONSE["Items"]

    results = mock_service.fetch_documents_from_table_with_nhs_number(
        nhs_number=TEST_NHS_NUMBER,
        table=MOCK_LG_TABLE_NAME,
        query_filter=mock_filter_expression,
    )

    assert len(results) == 3
    for result in results:
        assert isinstance(result, DocumentReference)

    mock_dynamo_service.query_table.assert_has_calls(expected_calls, any_order=True)


def test_fetch_documents_from_table_with_filter_returns_empty_list_of_doc_references(
    mocker, mock_service, mock_dynamo_service, mock_filter_expression
):
    expected_calls = [
        mocker.call(
            table_name=MOCK_LG_TABLE_NAME,
            index_name="NhsNumberIndex",
            search_key="NhsNumber",
            search_condition=TEST_NHS_NUMBER,
            query_filter=mock_filter_expression,
        )
    ]
    mock_dynamo_service.query_table.return_value = MOCK_EMPTY_RESPONSE

    results = mock_service.fetch_documents_from_table_with_nhs_number(
        nhs_number=TEST_NHS_NUMBER,
        table=MOCK_LG_TABLE_NAME,
        query_filter=mock_filter_expression,
    )

    assert len(results) == 0

    mock_dynamo_service.query_table.assert_has_calls(expected_calls, any_order=True)


@freeze_time("2023-10-1 13:00:00")
def test_delete_documents_soft_delete(mock_service, mock_dynamo_service):
    test_doc_ref = DocumentReference.model_validate(MOCK_DOCUMENT)

    test_date = datetime.now()
    ttl_date = test_date + timedelta(days=float(DocumentRetentionDays.SOFT_DELETE))

    test_update_fields = {
        "Deleted": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "TTL": int(ttl_date.timestamp()),
        "DocStatus": "deprecated",
    }

    mock_service.delete_document_references(
        MOCK_TABLE_NAME, [test_doc_ref], DocumentRetentionDays.SOFT_DELETE
    )

    mock_dynamo_service.update_item.assert_called_once_with(
        table_name=MOCK_TABLE_NAME,
        key_pair={"ID": test_doc_ref.id},
        updated_fields=test_update_fields,
    )


@freeze_time("2023-10-1 13:00:00")
def test_delete_documents_death_delete(mock_service, mock_dynamo_service):
    test_doc_ref = DocumentReference.model_validate(MOCK_DOCUMENT)

    test_date = datetime.now()
    ttl_date = test_date + timedelta(days=float(DocumentRetentionDays.DEATH))

    test_update_fields = {
        "Deleted": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "TTL": int(ttl_date.timestamp()),
        "DocStatus": "deprecated",
    }

    mock_service.delete_document_references(
        MOCK_TABLE_NAME, [test_doc_ref], DocumentRetentionDays.DEATH
    )

    mock_dynamo_service.update_item.assert_called_once_with(
        table_name=MOCK_TABLE_NAME,
        key_pair={"ID": test_doc_ref.id},
        updated_fields=test_update_fields,
    )


def test_update_document(mock_service, mock_dynamo_service):
    test_doc_ref = DocumentReference.model_validate(MOCK_DOCUMENT)

    test_update_fields = {"doc_status"}

    update_item_call = call(
        table_name=MOCK_TABLE_NAME,
        key_pair={"ID": test_doc_ref.id},
        updated_fields={"DocStatus": "final"},
    )

    mock_service.update_document(MOCK_TABLE_NAME, test_doc_ref, test_update_fields)

    mock_dynamo_service.update_item.assert_has_calls([update_item_call])


def test_hard_delete_metadata_records(mock_service, mock_dynamo_service):
    test_doc_refs = [
        DocumentReference.model_validate(mock_document)
        for mock_document in MOCK_SEARCH_RESPONSE["Items"][:2]
    ]
    expected_deletion_keys = [
        {DocumentReferenceMetadataFields.ID.value: doc_ref.id}
        for doc_ref in test_doc_refs
    ]

    mock_service.hard_delete_metadata_records(MOCK_TABLE_NAME, test_doc_refs)

    mock_dynamo_service.delete_item.assert_has_calls(
        [
            call(MOCK_TABLE_NAME, expected_deletion_keys[0]),
            call(MOCK_TABLE_NAME, expected_deletion_keys[1]),
        ]
    )


@freeze_time("2023-10-30T10:25:00")
def test_check_existing_lloyd_george_records_return_true_if_upload_in_progress(
    mock_service,
):
    two_minutes_ago = 1698661380  # 2023-10-30T10:23:00
    mock_records_upload_in_process = create_test_lloyd_george_doc_store_refs(
        override={
            "uploaded": False,
            "uploading": True,
            "last_updated": two_minutes_ago,
            "doc_status": "preliminary",
        }
    )

    response = mock_service.is_upload_in_process(mock_records_upload_in_process[0])

    assert response


def test_delete_document_object_successfully_deletes_s3_object(mock_service, caplog):
    test_bucket = "test-s3-bucket"
    test_file_key = "9000000000/test-file.pdf"

    expected_log_message = f"Located file `{test_file_key}` in `{test_bucket}`, attempting S3 object deletion"

    mock_service.s3_service.file_exist_on_s3.side_effect = [
        True,
        False,
    ]

    mock_service.delete_document_object(bucket=test_bucket, key=test_file_key)

    assert mock_service.s3_service.file_exist_on_s3.call_count == 2
    mock_service.s3_service.file_exist_on_s3.assert_called_with(
        s3_bucket_name=test_bucket, file_key=test_file_key
    )
    mock_service.s3_service.delete_object.assert_called_with(
        s3_bucket_name=test_bucket, file_key=test_file_key
    )

    assert expected_log_message in caplog.records[-1].msg


def test_delete_document_object_fails_to_delete_s3_object(mock_service, caplog):
    test_bucket = "test-s3-bucket"
    test_file_key = "9000000000/test-file.pdf"

    expected_err_msg = "Document located in S3 after deletion"

    mock_service.s3_service.file_exist_on_s3.side_effect = [
        True,
        True,
    ]

    with pytest.raises(DocumentServiceException) as e:
        mock_service.delete_document_object(bucket=test_bucket, key=test_file_key)

    assert mock_service.s3_service.file_exist_on_s3.call_count == 2
    mock_service.s3_service.file_exist_on_s3.assert_called_with(
        s3_bucket_name=test_bucket, file_key=test_file_key
    )
    mock_service.s3_service.delete_object.assert_called_with(
        s3_bucket_name=test_bucket, file_key=test_file_key
    )
    assert expected_err_msg == str(e.value)


def test_get_nhs_numbers_based_on_ods_code(mock_service, mocker):
    ods_code = "Y12345"
    expected_nhs_number = "9000000009"

    mock_documents = create_test_lloyd_george_doc_store_refs()

    mock_fetch = mocker.patch.object(
        mock_service,
        "fetch_documents_from_table",
        return_value=mock_documents,
    )

    result = mock_service.get_nhs_numbers_based_on_ods_code(ods_code)

    assert result == [expected_nhs_number]

    mock_fetch.assert_called_once_with(
        table="test_lg_dynamoDB_table",
        index_name="OdsCodeIndex",
        search_key=DocumentReferenceMetadataFields.CURRENT_GP_ODS.value,
        search_condition=ods_code,
        query_filter=NotDeleted,
    )


def test_get_batch_document_references_by_id_success(mock_service):
    document_ids = ["doc1", "doc2"]
    doc_type = SupportedDocumentTypes.LG
    table_name = doc_type.get_dynamodb_table_name()
    mock_dynamo_response = [
        {
            "ID": "doc1",
            "NhsNumber": "1234567890",
            "FileName": "file1.pdf",
            "Created": "2023-01-01T00:00:00Z",
            "Deleted": "",
            "VirusScannerResult": "Clean",
        },
        {
            "ID": "doc2",
            "NhsNumber": "1234567890",
            "FileName": "file2.pdf",
            "Created": "2023-01-02T00:00:00Z",
            "Deleted": "",
            "VirusScannerResult": "Clean",
        },
    ]

    mock_service.dynamo_service.batch_get_items.return_value = mock_dynamo_response

    result = mock_service.get_batch_document_references_by_id(document_ids, doc_type)

    mock_service.dynamo_service.batch_get_items.assert_called_with(
        table_name=table_name, key_list=document_ids
    )
    assert len(result) == 2
    assert isinstance(result[0], DocumentReference)
    assert result[0].id == "doc1"
    assert result[1].id == "doc2"


def test_get_batch_document_references_by_id_not_found(mock_service):
    document_ids = ["doc3"]
    doc_type = SupportedDocumentTypes.ARF
    table_name = doc_type.get_dynamodb_table_name()

    mock_service.dynamo_service.batch_get_items.return_value = []

    result = mock_service.get_batch_document_references_by_id(document_ids, doc_type)

    mock_service.dynamo_service.batch_get_items.assert_called_with(
        table_name=table_name, key_list=document_ids
    )
    assert len(result) == 0


def test_get_batch_document_references_by_id_client_error(
    mock_service, mock_dynamo_service
):
    document_ids = ["doc1"]
    doc_type = SupportedDocumentTypes.LG
    error_response = {"Error": {"Code": "500", "Message": "Something went wrong"}}

    mock_dynamo_service.batch_get_items.side_effect = ClientError(
        error_response, "BatchGetItem"
    )

    with pytest.raises(ClientError):
        mock_service.get_batch_document_references_by_id(document_ids, doc_type)
