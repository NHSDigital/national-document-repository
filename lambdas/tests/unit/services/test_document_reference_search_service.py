import json
import os

from json import JSONDecodeError
from unittest.mock import MagicMock, call

import pytest
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from enums.dynamo_filter import AttributeOperator
from enums.lambda_error import LambdaError
from enums.metadata_field_names import DocumentReferenceMetadataFields
from enums.mtls import MtlsCommonNames
from enums.snomed_codes import SnomedCodes
from freezegun import freeze_time
from models.document_reference import DocumentReference
from pydantic import ValidationError
from services.document_reference_search_service import DocumentReferenceSearchService
from tests.unit.conftest import APIM_API_URL
from tests.unit.helpers.data.dynamo.dynamo_responses import MOCK_SEARCH_RESPONSE
from utils.common_query_filters import NotDeleted, UploadCompleted
from utils.exceptions import DynamoServiceException
from utils.lambda_exceptions import DocumentRefSearchException
from utils.lambda_header_utils import validate_common_name_in_mtls

MOCK_DOCUMENT_REFERENCE = [
    DocumentReference.model_validate(MOCK_SEARCH_RESPONSE["Items"][0])
]

MOCK_FILE_SIZE = 24000

EXPECTED_RESPONSE = {
    "created": "2024-01-01T12:00:00.000Z",
    "fileName": "document.csv",
    "virusScannerResult": "Clean",
    "id": "3d8683b9-1665-40d2-8499-6e8302d507ff",
    "fileSize": MOCK_FILE_SIZE,
}


@pytest.fixture
def mock_document_service(mocker, set_env):
    service = DocumentReferenceSearchService()
    mock_s3_service = mocker.patch.object(service, "s3_service")
    mocker.patch.object(mock_s3_service, "get_file_size", return_value=MOCK_FILE_SIZE)
    mocker.patch.object(service, "dynamo_service")
    mocker.patch.object(service, "fetch_documents_from_table_with_nhs_number")
    mocker.patch.object(service, "is_upload_in_process", return_value=False)
    return service


@pytest.fixture
def mock_filter_builder(mocker):
    mock_filter = mocker.MagicMock()
    mocker.patch(
        "services.document_reference_search_service.DynamoQueryFilterBuilder",
        return_value=mock_filter,
    )
    return mock_filter


def test_get_document_references_raise_json_error_when_no_table_list(
    mock_document_service, monkeypatch
):
    monkeypatch.setenv("DYNAMODB_TABLE_LIST", "")
    with pytest.raises(JSONDecodeError):
        mock_document_service._get_table_names(None)


def test_search_tables_for_documents_raise_validation_error(
    mock_document_service, validation_error
):
    mock_document_service.fetch_documents_from_table_with_nhs_number.side_effect = (
        validation_error
    )
    with pytest.raises(ValidationError):
        mock_document_service._search_tables_for_documents(
            "1234567890", ["table1", "table2"], return_fhir=True
        )


def test_get_document_references_raise_client_error(mock_document_service):
    mock_document_service.fetch_documents_from_table_with_nhs_number.side_effect = (
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
    with pytest.raises(ClientError):
        mock_document_service._search_tables_for_documents(
            "1234567890", ["table1", "table2"], return_fhir=True
        )


def test_get_document_references_raise_dynamodb_error(mock_document_service):
    mock_document_service.fetch_documents_from_table_with_nhs_number.side_effect = (
        DynamoServiceException()
    )
    with pytest.raises(DynamoServiceException):
        mock_document_service._search_tables_for_documents(
            "1234567890",
            ["table1", "table2"],
            return_fhir=True,
            check_upload_completed=False,
        )


def test_get_document_references_dynamo_return_empty_response(mock_document_service):
    mock_document_service.fetch_documents_from_table_with_nhs_number.return_value = []
    expected_results = None

    actual = mock_document_service._search_tables_for_documents(
        "1234567890", ["table1", "table2"], return_fhir=True
    )

    assert actual == expected_results


def test_get_document_references_dynamo_return_successful_response_single_table(
    mock_document_service, monkeypatch
):
    monkeypatch.setenv("DYNAMODB_TABLE_LIST", json.dumps(["test_table"]))

    mock_document_service.fetch_documents_from_table_with_nhs_number.return_value = (
        MOCK_DOCUMENT_REFERENCE
    )
    expected_results = MOCK_DOCUMENT_REFERENCE
    actual = mock_document_service.fetch_documents_from_table_with_nhs_number(
        "111111111", "test_table", NotDeleted
    )

    assert actual == expected_results


@pytest.mark.parametrize(
    "common_name, expected",
    [
        (
            {
                "x-amzn-mtls-clientcert-subject": "CN=ndrclient.main.dev.pdm.national.nhs.uk"
            },
            ["test_pdm_dynamoDB_table"],
        ),
        ({}, ["test_pdm_dynamoDB_table", "test_lg_dynamoDB_table"]),
    ],
)
def test_get_pdm_table(set_env, mock_document_service, common_name, expected):
    cn = validate_common_name_in_mtls(common_name)
    tables = mock_document_service._get_table_names(cn)
    assert tables == expected


def test_build_document_model_response(mock_document_service, monkeypatch):
    expected_results = [EXPECTED_RESPONSE]
    actual = mock_document_service._process_documents(MOCK_DOCUMENT_REFERENCE, False)

    assert actual == expected_results


def test_get_document_references_dynamo_return_successful_response_multiple_tables(
    mock_document_service, mocker
):
    mock_fetch_documents = mocker.MagicMock(return_value=MOCK_DOCUMENT_REFERENCE)
    mock_document_service.fetch_documents_from_table_with_nhs_number = (
        mock_fetch_documents
    )
    mock_document_service._validate_upload_status = mocker.MagicMock()
    mock_document_service._process_documents = mocker.MagicMock(
        return_value=[EXPECTED_RESPONSE]
    )
    expected_results = [EXPECTED_RESPONSE, EXPECTED_RESPONSE]

    actual = mock_document_service._search_tables_for_documents(
        "1111111111", ["table1", "table2"], False
    )

    assert actual == expected_results


def test_get_document_references_raise_error_when_upload_is_in_process(
    mock_document_service,
):
    mock_document_service.is_upload_in_process.return_value = True

    with pytest.raises(DocumentRefSearchException):
        mock_document_service._validate_upload_status(MOCK_DOCUMENT_REFERENCE)


def test_get_document_references_success(mock_document_service, mocker):
    mock_get_table_names = mocker.MagicMock(return_value=["table1", "table2"])
    mock_document_service._get_table_names = mock_get_table_names
    mock_search_document = mocker.MagicMock(return_value=[{"id": "123"}])
    mock_document_service._search_tables_for_documents = mock_search_document

    result = mock_document_service.get_document_references(
        "1234567890", return_fhir=False
    )

    assert result == [{"id": "123"}]
    mock_get_table_names.assert_called_once()
    mock_search_document.assert_called_once_with(
        "1234567890", ["table1", "table2"], False, None, True
    )


def test_get_document_references_exception(mock_document_service, mocker):
    mock_document_service._get_table_names = mocker.MagicMock(
        side_effect=DynamoServiceException
    )

    with pytest.raises(DocumentRefSearchException) as exc_info:
        mock_document_service.get_document_references("1234567890")

    assert exc_info.value.status_code == 500
    assert exc_info.value.error == LambdaError.DocRefClient


def test_search_tables_for_documents_non_fhir(mock_document_service, mocker):
    mock_fetch_document_method = mocker.MagicMock(return_value=MOCK_DOCUMENT_REFERENCE)
    mock_document_service.fetch_documents_from_table_with_nhs_number = (
        mock_fetch_document_method
    )

    mock_document_id = {"id": "123"}
    mock_process_document_non_fhir = mocker.MagicMock(return_value=[mock_document_id])

    mock_document_service._process_documents = mock_process_document_non_fhir
    result_non_fhir = mock_document_service._search_tables_for_documents(
        "1234567890",
        ["table1", "table2"],
        return_fhir=False,
        check_upload_completed=True,
    )

    assert result_non_fhir == [mock_document_id, mock_document_id]

    mock_process_document_non_fhir.assert_has_calls(
        [
            call(MOCK_DOCUMENT_REFERENCE, return_fhir=False),
            call(MOCK_DOCUMENT_REFERENCE, return_fhir=False),
        ]
    )
    assert mock_fetch_document_method.call_count == 2

    mock_fetch_document_method.assert_has_calls(
        [
            call("1234567890", "table1", query_filter=UploadCompleted),
            call("1234567890", "table2", query_filter=UploadCompleted),
        ]
    )


def test_search_tables_for_documents_fhir(mock_document_service, mocker):
    mock_fetch_document_method = mocker.MagicMock(return_value=MOCK_DOCUMENT_REFERENCE)
    mock_document_service.fetch_documents_from_table_with_nhs_number = (
        mock_fetch_document_method
    )

    mock_fhir_doc = {"resourceType": "DocumentReference", "id": "123"}
    mock_process_document_fhir = mocker.MagicMock(return_value=[mock_fhir_doc])

    mock_document_service._process_documents = mock_process_document_fhir
    result_fhir = mock_document_service._search_tables_for_documents(
        "1234567890",
        ["table1", "table2"],
        return_fhir=True,
        check_upload_completed=True,
    )

    assert result_fhir["resourceType"] == "Bundle"
    assert result_fhir["type"] == "searchset"
    assert result_fhir["total"] == 2
    assert len(result_fhir["entry"]) == 2
    assert result_fhir["entry"][0]["resource"] == mock_fhir_doc
    assert result_fhir["entry"][1]["resource"] == mock_fhir_doc

    mock_fetch_document_method.assert_has_calls(
        [
            call("1234567890", "table1", query_filter=UploadCompleted),
            call("1234567890", "table2", query_filter=UploadCompleted),
        ]
    )
    mock_process_document_fhir.assert_has_calls(
        [
            call(MOCK_DOCUMENT_REFERENCE, return_fhir=True),
            call(MOCK_DOCUMENT_REFERENCE, return_fhir=True),
        ]
    )


def test_validate_upload_status_raises_exception(mock_document_service):
    mock_document_service.is_upload_in_process = MagicMock(return_value=True)

    with pytest.raises(DocumentRefSearchException) as exc_info:
        mock_document_service._validate_upload_status(MOCK_DOCUMENT_REFERENCE)

    assert exc_info.value.status_code == 423
    assert exc_info.value.error == LambdaError.UploadInProgressError


def test_process_documents_return_fhir(mock_document_service):
    mock_document_service.create_document_reference_fhir_response = MagicMock(
        return_value={"fhir": "response"}
    )

    result = mock_document_service._process_documents(
        MOCK_DOCUMENT_REFERENCE, return_fhir=True
    )

    assert result == [{"fhir": "response"}]
    mock_document_service.create_document_reference_fhir_response.assert_called_once()


def test_create_document_reference_fhir_response(mock_document_service, mocker):
    mock_document_reference = mocker.MagicMock()
    mock_document_reference.nhs_number = "9000000009"
    mock_document_reference.file_name = "test_document.pdf"
    mock_document_reference.created = "2023-05-01T12:00:00Z"
    mock_document_reference.document_scan_creation = "2023-05-01"
    mock_document_reference.id = "Y05868-1634567890"
    mock_document_reference.current_gp_ods = "Y12345"

    mock_attachment = mocker.patch(
        "services.document_reference_search_service.Attachment"
    )
    mock_attachment_instance = mocker.MagicMock()
    mock_attachment.return_value = mock_attachment_instance

    mock_doc_ref_info = mocker.patch(
        "services.document_reference_search_service.DocumentReferenceInfo"
    )
    mock_doc_ref_info_instance = mocker.MagicMock()
    mock_doc_ref_info.return_value = mock_doc_ref_info_instance

    mock_fhir_doc_ref = mocker.MagicMock()
    mock_doc_ref_info_instance.create_fhir_document_reference_object.return_value = (
        mock_fhir_doc_ref
    )

    expected_fhir_response = {
        "id": "16521000000101~Y05868-1634567890",
        "resourceType": "DocumentReference",
        "status": "current",
        "docStatus": "final",
        "subject": {
            "identifier": {
                "system": "https://fhir.nhs.uk/Id/nhs-number",
                "value": "9000000009",
            }
        },
        "content": [
            {
                "attachment": {
                    "contentType": "application/pdf",
                    "language": "en-GB",
                    "title": "test_document.pdf",
                    "creation": "2023-05-01",
                    "url": f"{APIM_API_URL}/DocumentReference/123",
                }
            }
        ],
        "author": [
            {
                "identifier": {
                    "system": "https://fhir.nhs.uk/Id/ods-organization-code",
                    "value": "Y05868",
                }
            }
        ],
        "custodian": {
            "identifier": {
                "system": "https://fhir.nhs.uk/Id/ods-organization-code",
                "value": "Y05868",
            }
        },
    }
    mock_fhir_doc_ref.model_dump.return_value = expected_fhir_response

    result = mock_document_service.create_document_reference_fhir_response(
        mock_document_reference
    )

    mock_attachment.assert_called_once_with(
        title=mock_document_reference.file_name,
        creation=mock_document_reference.document_scan_creation,
        url=f"{APIM_API_URL}/DocumentReference/{SnomedCodes.LLOYD_GEORGE.value.code}~{mock_document_reference.id}",
    )

    mock_doc_ref_info.assert_called_once_with(
        nhs_number=mock_document_reference.nhs_number,
        attachment=mock_attachment_instance,
        custodian=mock_document_reference.current_gp_ods,
        snomed_code_doc_type=None,
    )

    mock_doc_ref_info_instance.create_fhir_document_reference_object.assert_called_once()
    mock_fhir_doc_ref.model_dump.assert_called_once_with(exclude_none=True)

    assert result == expected_fhir_response


@freeze_time("2023-05-01T12:00:00Z")
def test_create_document_reference_fhir_response_integration(
    mock_document_service, mocker
):
    mock_document_reference = mocker.MagicMock()
    mock_document_reference.nhs_number = "9000000009"
    mock_document_reference.file_name = "test_document.pdf"
    mock_document_reference.created = "2023-05-01T12:00:00"
    mock_document_reference.document_scan_creation = "2023-05-01"
    mock_document_reference.id = "Y05868-1634567890"
    mock_document_reference.current_gp_ods = "Y12345"
    mock_document_reference.author = "Y12345"
    mock_document_reference.doc_status = "final"
    mock_document_reference.custodian = "Y12345"
    mock_document_reference.document_snomed_code_type = "16521000000101"

    expected_fhir_response = {
        "id": "16521000000101~Y05868-1634567890",
        "resourceType": "DocumentReference",
        "status": "current",
        "docStatus": "final",
        "subject": {
            "identifier": {
                "system": "https://fhir.nhs.uk/Id/nhs-number",
                "value": "9000000009",
            }
        },
        "date": "2023-05-01T12:00:00",
        "content": [
            {
                "attachment": {
                    "contentType": "application/pdf",
                    "language": "en-GB",
                    "title": "test_document.pdf",
                    "creation": "2023-05-01",
                    "url": f"{APIM_API_URL}/DocumentReference/16521000000101~Y05868-1634567890",
                }
            }
        ],
        "author": [
            {
                "identifier": {
                    "system": "https://fhir.nhs.uk/Id/ods-organization-code",
                    "value": "Y12345",
                }
            }
        ],
        "custodian": {
            "identifier": {
                "system": "https://fhir.nhs.uk/Id/ods-organization-code",
                "value": "Y12345",
            }
        },
        "type": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "16521000000101",
                    "display": "Lloyd George record folder",
                }
            ]
        },
    }

    result = mock_document_service.create_document_reference_fhir_response(
        mock_document_reference
    )

    assert isinstance(result, dict)
    assert result == expected_fhir_response


def test_build_filter_expression_custodian(mock_document_service):
    filter_values = {"custodian": "12345"}
    expected_filter = Attr("CurrentGpOds").eq("12345") & (
        Attr("Deleted").eq("") | Attr("Deleted").not_exists()
    )

    actual_filter = mock_document_service._build_filter_expression(filter_values)

    assert expected_filter == actual_filter


def test_build_filter_expression_custodian_mocked(
    mock_document_service, mock_filter_builder
):
    filter_values = {"custodian": "12345"}

    mock_document_service._build_filter_expression(filter_values)

    mock_filter_builder.add_condition.assert_any_call(
        attribute=DocumentReferenceMetadataFields.CURRENT_GP_ODS.value,
        attr_operator=AttributeOperator.EQUAL,
        filter_value="12345",
    )


def test_build_filter_expression_defaults(mock_document_service):
    filter_values = {}
    expected_filter = Attr("Deleted").eq("") | Attr("Deleted").not_exists()

    actual_filter = mock_document_service._build_filter_expression(filter_values)

    assert actual_filter == expected_filter
