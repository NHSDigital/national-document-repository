from datetime import datetime, timedelta
from unittest.mock import call, ANY

import pytest
import json
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
from enums.snomed_codes import SnomedCode, SnomedCodes
from models.fhir.R4.fhir_document_reference import (
    DocumentReference as FhirDocumentReference,
)
from models.fhir.R4.base_models import Identifier, Reference
from models.fhir.R4.fhir_document_reference import DocumentReferenceContent
from models.fhir.R4.fhir_document_reference import Attachment
from tests.unit.conftest import (
    EXPECTED_PARSED_PATIENT_BASE_CASE as mock_pds_patient_details,
)
from tests.unit.helpers.data.bulk_upload.test_data import TEST_DOCUMENT_REFERENCE
from utils.exceptions import (
    DocumentServiceException,
    FileUploadInProgress,
    NoAvailableDocument,
    InvalidResourceIdException,
    PatientNotFoundException,
    PdsErrorException,
)

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


@pytest.fixture
def valid_nhs_number():
    return "9000000009"


@pytest.fixture
def valid_fhir_doc_json(valid_nhs_number):
    return json.dumps(
        {
            "resourceType": "DocumentReference",
            "docStatus": "final",
            "status": "current",
            "subject": {
                "identifier": {
                    "system": "https://fhir.nhs.uk/Id/nhs-number",
                    "value": valid_nhs_number,
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
def mock_pds_service_fetch(mocker):
    mock_service_object = mocker.MagicMock()
    mocker.patch(
        "services.put_fhir_document_reference_service.get_pds_service",
        return_value=mock_service_object,
    )
    mock_service_object.fetch_patient_details.return_value = mock_pds_patient_details


def test_fetch_available_document_references_by_type_lg_returns_list_of_doc_references(
    mock_service, mock_dynamo_service, mock_filter_expression
):
    mock_dynamo_service.query_table_by_index.return_value = MOCK_SEARCH_RESPONSE

    results = mock_service.fetch_available_document_references_by_type(
        TEST_NHS_NUMBER, SupportedDocumentTypes.LG, mock_filter_expression
    )

    assert len(results) == 3
    for result in results:
        assert isinstance(result, DocumentReference)

    mock_dynamo_service.query_table_by_index.assert_called_once_with(
        table_name=MOCK_LG_TABLE_NAME,
        index_name="NhsNumberIndex",
        search_key="NhsNumber",
        search_condition=TEST_NHS_NUMBER,
        query_filter=mock_filter_expression,
        exclusive_start_key=None,
    )


def test_fetch_available_document_references_by_type_arf_returns_list_of_doc_references(
    mock_service, mock_dynamo_service, mock_filter_expression
):
    mock_dynamo_service.query_table_by_index.return_value = MOCK_SEARCH_RESPONSE

    results = mock_service.fetch_available_document_references_by_type(
        TEST_NHS_NUMBER, SupportedDocumentTypes.ARF, mock_filter_expression
    )

    assert len(results) == 3
    for result in results:
        assert isinstance(result, DocumentReference)

    mock_dynamo_service.query_table_by_index.assert_called_once_with(
        table_name=MOCK_ARF_TABLE_NAME,
        index_name="NhsNumberIndex",
        search_key="NhsNumber",
        search_condition=TEST_NHS_NUMBER,
        query_filter=mock_filter_expression,
        exclusive_start_key=None,
    )


def test_fetch_available_document_references_by_type_lg_returns_empty_list_of_doc_references(
    mock_service, mock_dynamo_service, mock_filter_expression
):
    mock_dynamo_service.query_table_by_index.return_value = MOCK_EMPTY_RESPONSE

    result = mock_service.fetch_available_document_references_by_type(
        TEST_NHS_NUMBER, SupportedDocumentTypes.LG, mock_filter_expression
    )
    assert len(result) == 0
    mock_dynamo_service.query_table_by_index.assert_called_once_with(
        table_name=MOCK_LG_TABLE_NAME,
        index_name="NhsNumberIndex",
        search_key="NhsNumber",
        search_condition=TEST_NHS_NUMBER,
        query_filter=mock_filter_expression,
        exclusive_start_key=None,
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
            exclusive_start_key=None,
        )
    ]

    mock_dynamo_service.query_table_by_index.return_value = MOCK_SEARCH_RESPONSE

    results = mock_service.fetch_documents_from_table_with_nhs_number(
        nhs_number=TEST_NHS_NUMBER,
        table=MOCK_LG_TABLE_NAME,
        query_filter=mock_filter_expression,
    )

    assert len(results) == 3
    for result in results:
        assert isinstance(result, DocumentReference)

    mock_dynamo_service.query_table_by_index.assert_has_calls(
        expected_calls, any_order=True
    )


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
            exclusive_start_key=None,
        )
    ]
    mock_dynamo_service.query_table_by_index.return_value = MOCK_EMPTY_RESPONSE

    results = mock_service.fetch_documents_from_table_with_nhs_number(
        nhs_number=TEST_NHS_NUMBER,
        table=MOCK_LG_TABLE_NAME,
        query_filter=mock_filter_expression,
    )

    assert len(results) == 0

    mock_dynamo_service.query_table_by_index.assert_has_calls(
        expected_calls, any_order=True
    )


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

def test_store_binary_in_s3(mock_service, mock_dynamo_service):
    pass

@pytest.mark.parametrize(
    "modify_doc",
    [
        # Missing NHS number (wrong system)
        lambda doc: {
            **doc,
            "type": {"coding": [{"system": "wrong-system", "code": "9000000009"}]},
        },
        # Invalid document type
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
        # Missing document type
        lambda doc: {**doc, "type": {"coding": []}},
    ],
)
def test_document_validation_errors(
    mock_service, valid_fhir_doc_json, modify_doc
):
    """Test validation error scenarios."""
    doc = json.loads(valid_fhir_doc_json)
    modified_doc = FhirDocumentReference(**modify_doc(doc))

    with pytest.raises(DocumentServiceException) as e:
        mock_service.determine_document_type(modified_doc)


def test_dynamo_error(mock_service, mocker):
    """Test handling of DynamoDB error."""
    mock_service.dynamo_service.create_item.side_effect = ClientError(
        {"Error": {"Code": "InternalServerError", "Message": "Test error"}},
        "CreateItem",
    )

    mock_document = mocker.MagicMock()

    with pytest.raises(DocumentServiceException) as excinfo:
        mock_service.save_document_reference_to_dynamo("", mock_document)


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

    with pytest.raises(DocumentServiceException) as excinfo:
        mock_service.save_document_reference_to_dynamo("test-table", document_ref)

    mock_service.dynamo_service.create_item.assert_called_once()


def test_check_nhs_number_with_pds_raise_error(mock_service, mocker):
    """Test handling of PDS error."""
    mock_service_object = mocker.MagicMock()
    mocker.patch(
        "services.document_service.get_pds_service",
        return_value=mock_service_object,
    )
    mock_service_object.fetch_patient_details.side_effect = PatientNotFoundException(
        "test test"
    )
    with pytest.raises(DocumentServiceException) as excinfo:
        mock_service.check_nhs_number_with_pds("9000000009")


def test_extract_nhs_number_from_fhir_with_invalid_system(mock_service, mocker):
    """Test _extract_nhs_number_from_fhir method with an invalid NHS number system."""

    fhir_doc = mocker.MagicMock(spec=FhirDocumentReference)
    fhir_doc.subject = Reference(
        identifier=Identifier(system="invalid-system", value="9000000009")
    )

    with pytest.raises(DocumentServiceException) as excinfo:
        mock_service.extract_nhs_number_from_fhir(fhir_doc)


def test_get_dynamo_table_for_non_lloyd_george_doc_type(mock_service):
    """Test _get_dynamo_table_for_doc_type method with a non-Lloyd George document type."""

    non_lg_code = SnomedCode(code="non-lg-code", display_name="Non Lloyd George")

    result = mock_service.get_dynamo_table_for_doc_type(non_lg_code)

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

    result = mock_service.create_document_reference(
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
    assert result.version == "2"


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

    result = mock_service.create_document_reference(
        nhs_number="9000000009",
        doc_type=doc_type,
        fhir_doc=fhir_doc,
        current_gp_ods=current_gp_ods,
        version="2",
    )

    assert (
        result.custodian == current_gp_ods
    )  # Custodian should default to current_gp_ods


def test_extract_nhs_number_from_fhir_with_missing_identifier(mock_service, mocker):
    """Test _extract_nhs_number_from_fhir method when identifier is missing."""
    fhir_doc = mocker.MagicMock(spec=FhirDocumentReference)
    fhir_doc.subject = Reference(identifier=None)

    with pytest.raises(DocumentServiceException) as excinfo:
        mock_service.extract_nhs_number_from_fhir(fhir_doc)


def test_determine_document_type_with_missing_type(mock_service, mocker):
    """Test _determine_document_type method when type is missing entirely."""
    fhir_doc = mocker.MagicMock(spec=FhirDocumentReference)
    fhir_doc.type = None

    with pytest.raises(DocumentServiceException) as excinfo:
        mock_service.determine_document_type(fhir_doc)


def test_determine_document_type_with_missing_coding(mock_service, mocker):
    """Test _determine_document_type method when coding is missing."""
    fhir_doc = mocker.MagicMock(spec=FhirDocumentReference)
    fhir_doc.type = mocker.MagicMock()
    fhir_doc.type.coding = None

    with pytest.raises(DocumentServiceException) as excinfo:
        mock_service.determine_document_type(fhir_doc)


def test_get_dynamo_table_for_lloyd_george_doc_type(mock_service):
    """Test _get_dynamo_table_for_doc_type method with Lloyd George document type."""
    lg_code = SnomedCodes.LLOYD_GEORGE.value

    result = mock_service.get_dynamo_table_for_doc_type(lg_code)

    assert result == mock_service.lg_dynamo_table


def test_check_nhs_number_with_pds_success(mock_service, mocker):
    """Test successful NHS number validation with PDS."""
    mock_service_object = mocker.MagicMock()
    mocker.patch(
        "services.document_service.get_pds_service",
        return_value=mock_service_object,
    )
    mock_service_object.fetch_patient_details.return_value = mock_pds_patient_details

    # This should not raise an exception
    result = mock_service.check_nhs_number_with_pds("9000000009")

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
        version="2"
    )

    mock_service.save_document_reference_to_dynamo("test-table", document_ref)

    mock_service.dynamo_service.create_item.assert_called()


def test_store_binary_in_s3_success(mock_service, mocker):
    """Test successful binary storage in S3."""
    binary_data = b"SGVsbG8gV29ybGQ="  # Base64 encoded "Hello World"

    mock_service.s3_service.upload_file_obj.return_value = None

    mock_service.store_binary_in_s3(TEST_DOCUMENT_REFERENCE, binary_data)

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

    with pytest.raises(DocumentServiceException) as excinfo:
        mock_service.store_binary_in_s3(TEST_DOCUMENT_REFERENCE, binary_data)


def test_store_binary_in_s3_with_large_binary_data(mock_service):
    """Test _store_binary_in_s3 method with large binary data."""
    # Create a large binary data (8MB)
    binary_data = b"A" * (8 * 1024 * 1024)

    mock_service.store_binary_in_s3(TEST_DOCUMENT_REFERENCE, binary_data)

    mock_service.s3_service.upload_file_obj.assert_called_once()


def test_process_fhir_document_reference_with_invalid_base64_data(mock_service):
    """Test process_fhir_document_reference with invalid base64 data."""
    with pytest.raises(DocumentServiceException):
        mock_service.store_binary_in_s3(
            TEST_DOCUMENT_REFERENCE, b"invalid-base64-data!!!"
        )


def test_determine_document_type_returns_lloyd_george_type(mock_service, valid_fhir_doc_object):
    """Test that determine_document_type returns the lloyd george type for
       a lloyd george document"""
    result = mock_service.determine_document_type(valid_fhir_doc_object)

    assert result == SnomedCodes.LLOYD_GEORGE.value


def test_extract_nhs_number_from_fhir_returns_nhs_number(mock_service, valid_fhir_doc_object, valid_nhs_number):
    """Test that extract_nhs_number_from_fhir returns the correct nhs number"""
    result = mock_service.extract_nhs_number_from_fhir(valid_fhir_doc_object)

    assert result == valid_nhs_number


def test_get_document_reference_no_documents_found(mocker, mock_service):
    """Test that get_document_reference raises an error when there are no document results"""
    mock_service.fetch_documents_from_table = mocker.patch("services.document_service.DocumentService.fetch_documents_from_table", return_value=[])

    with pytest.raises(DocumentServiceException) as e:
        mock_service.get_document_reference("", "")


def test_get_document_reference_returns_document_reference(mocker, mock_service):
    """Test that get_document_reference returns the first document reference from the results"""
    documents = create_test_lloyd_george_doc_store_refs()

    mock_service.fetch_documents_from_table = mocker.patch("services.document_service.DocumentService.fetch_documents_from_table", return_value=documents)

    result = mock_service.get_document_reference("", "")

    assert result == documents[0]


def test_create_s3_presigned_url_error(mock_service):
    """Test that create_s3_presigned_url raises a DocumentServiceException on AWS S3 ClientError"""
    mock_service.s3_service.create_put_presigned_url.side_effect = ClientError({"Error": {}}, "")
    document = create_test_lloyd_george_doc_store_refs()[0]

    with pytest.raises(DocumentServiceException) as e:
        mock_service.create_s3_presigned_url(document)


def test_create_s3_presigned_url_returns_url(mock_service):
    """Test that create_s3_presigned_url returns a url"""
    mock_presigned_url_response = "https://test-bucket.s3.amazonaws.com/"
    mock_service.s3_service.create_put_presigned_url.return_value = mock_presigned_url_response
    document = create_test_lloyd_george_doc_store_refs()[0]

    result = mock_service.create_s3_presigned_url(document)

    assert result == mock_presigned_url_response


def test_store_binary_in_s3_on_memory_error(mock_service):
    """Test that store_binary_in_s3 raises DocumentServiceException when MemoryError is raised"""
    mock_service.s3_service.upload_file_obj.side_effect = MemoryError()
    document = create_test_lloyd_george_doc_store_refs()[0]

    with pytest.raises(DocumentServiceException) as e:
        mock_service.store_binary_in_s3(document, bytes())


def test_store_binary_in_s3_on_oserror(mock_service):
    """Test that store_binary_in_s3 raises DocumentServiceException when OSError is raised"""
    mock_service.s3_service.upload_file_obj.side_effect = OSError()
    document = create_test_lloyd_george_doc_store_refs()[0]

    with pytest.raises(DocumentServiceException) as e:
        mock_service.store_binary_in_s3(document, bytes())


def test_store_binary_in_s3_on_ioerror(mock_service):
    """Test that store_binary_in_s3 raises DocumentServiceException when IOError is raised"""
    mock_service.s3_service.upload_file_obj.side_effect = IOError()
    document = create_test_lloyd_george_doc_store_refs()[0]

    with pytest.raises(DocumentServiceException) as e:
        mock_service.store_binary_in_s3(document, bytes())

def test_get_available_lloyd_george_record_for_patient_return_docs(mocker, mock_service, valid_nhs_number):
    """Test that get_available_lloyd_george_record_for_patient returns correctly"""
    documents = create_test_lloyd_george_doc_store_refs()
    mock_service.fetch_available_document_references_by_type = mocker.patch(
    "services.document_service.DocumentService.fetch_available_document_references_by_type",
    return_value = documents
    )

    result = mock_service.get_available_lloyd_george_record_for_patient(valid_nhs_number)

    assert result == documents

def test_get_available_lloyd_george_record_for_patient_no_available_docs_error(mocker, mock_service, valid_nhs_number):
    """Test that get_available_lloyd_george_record_for_patient raises
       NoAvailableDocs when no documents are found"""
    mock_service.fetch_available_document_references_by_type = mocker.patch(
        "services.document_service.DocumentService.fetch_available_document_references_by_type",
        return_value = None
    )

    with pytest.raises(NoAvailableDocument) as e:
        mock_service.get_available_lloyd_george_record_for_patient(valid_nhs_number)


def test_get_available_lloyd_george_record_for_patient_file_upload_in_progress(mocker, mock_service, valid_nhs_number):
    """Test that get_available_lloyd_george_record_for_patient returns raises
       FileUploadInProgress when the document is in the process of being
       uploaded"""
    documents = create_test_lloyd_george_doc_store_refs()
    documents[0].uploading = True
    documents[0].uploaded = False
    mock_service.fetch_available_document_references_by_type = mocker.patch(
    "services.document_service.DocumentService.fetch_available_document_references_by_type",
    return_value = documents
    )

    with pytest.raises(FileUploadInProgress) as e:
        mock_service.get_available_lloyd_george_record_for_patient(valid_nhs_number)


def test_delete_document_object_error_on_nonexistant_file(mock_service):
    """Test that delete_document_object raises DocumentServiceException
       when the file doesn't exist"""
    mock_service.s3_service.file_exist_on_s3.return_value = None

    with pytest.raises(DocumentServiceException) as e:
        mock_service.delete_document_object("", "")


def test_fetch_documents_from_table_validation_error(mock_service):
    """Test that fetch_documents_from_table handles validation errors"""
    documents = create_test_lloyd_george_doc_store_refs()
    invalid_doc_reference = "Invalid document reference"

    documents.append(invalid_doc_reference)

    mock_response = {
        "Items": documents
    }

    mock_service.dynamo_service.query_table_by_index.return_value = mock_response

    response = mock_service.fetch_documents_from_table("", "", "")

    assert invalid_doc_reference not in response


def test_fetch_documents_from_table_pagination(mock_service):
    """Test that fetch_documents_from_table handles validation errors"""
    documents = create_test_lloyd_george_doc_store_refs()
    mock_exclusive_start_key = "exclusive start key"

    first_mock_response = {
        "Items": documents,
        "LastEvaluatedKey": mock_exclusive_start_key
    }
    
    second_mock_response = {
        "Items": documents
    }

    mock_service.dynamo_service.query_table_by_index.side_effect = [first_mock_response, second_mock_response]

    response = mock_service.fetch_documents_from_table("", "", "")

    mock_service.dynamo_service.query_table_by_index.assert_any_call(
        table_name=ANY,
        index_name=ANY,
        search_key=ANY,
        search_condition=ANY,
        query_filter=ANY,
        exclusive_start_key=mock_exclusive_start_key
    )