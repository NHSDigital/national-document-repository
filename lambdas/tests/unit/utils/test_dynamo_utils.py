import json

import pytest
from enums.lambda_error import LambdaError
from enums.metadata_field_names import DocumentReferenceMetadataFields
from tests.unit.conftest import (
    MOCK_LG_TABLE_NAME,
    MOCK_PDM_TABLE_NAME,
    TEST_CURRENT_GP_ODS,
    TEST_DOCUMENT_LOCATION,
    TEST_FILE_KEY,
    TEST_NHS_NUMBER,
    TEST_UUID,
)
from tests.unit.helpers.data.dynamo.dynamo_stream import (
    MOCK_OLD_IMAGE_EVENT,
    MOCK_OLD_IMAGE_MODEL,
)
from utils.dynamo_utils import (
    DocTypeTableRouter,
    create_expression_attribute_placeholder,
    create_expression_attribute_values,
    create_expression_value_placeholder,
    create_expressions,
    create_update_expression,
    parse_dynamo_record,
)
from utils.lambda_exceptions import CreateDocumentRefException, InvalidDocTypeException

from lambdas.enums.snomed_codes import SnomedCodes


def test_create_expressions_correctly_creates_an_expression_of_one_field():
    expected_projection = "#VirusScannerResult_attr"
    expected_expr_attr_names = {"#VirusScannerResult_attr": "VirusScannerResult"}

    fields_requested = [DocumentReferenceMetadataFields.VIRUS_SCANNER_RESULT.value]

    actual_projection, actual_expr_attr_names = create_expressions(fields_requested)

    assert actual_projection == expected_projection
    assert actual_expr_attr_names == expected_expr_attr_names


def test_create_expressions_correctly_creates_an_expression_of_multiple_fields():
    expected_projection = "#NhsNumber_attr,#FileLocation_attr,#ContentType_attr"
    expected_expr_attr_names = {
        "#NhsNumber_attr": "NhsNumber",
        "#FileLocation_attr": "FileLocation",
        "#ContentType_attr": "ContentType",
    }

    fields_requested = [
        DocumentReferenceMetadataFields.NHS_NUMBER.value,
        DocumentReferenceMetadataFields.FILE_LOCATION.value,
        DocumentReferenceMetadataFields.CONTENT_TYPE.value,
    ]

    actual_projection, actual_expr_attr_names = create_expressions(fields_requested)

    assert actual_projection == expected_projection
    assert actual_expr_attr_names == expected_expr_attr_names


def test_create_expression_attribute_values():
    attribute_field_values = {
        DocumentReferenceMetadataFields.DELETED.value: "True",
        DocumentReferenceMetadataFields.VIRUS_SCANNER_RESULT.value: "Scanned",
    }
    expected = {":Deleted_val": "True", ":VirusScannerResult_val": "Scanned"}

    actual = create_expression_attribute_values(attribute_field_values)

    assert actual == expected


def test_create_update_expression_multiple_values():
    field_names = ["Deleted", "VirusScannerResult"]
    expected = "SET #Deleted_attr = :Deleted_val, #VirusScannerResult_attr = :VirusScannerResult_val"

    actual = create_update_expression(field_names)

    assert actual == expected


def test_create_update_expression_singular_value():
    field_names = ["Deleted"]
    expected = "SET #Deleted_attr = :Deleted_val"

    actual = create_update_expression(field_names)

    assert actual == expected


def test_create_expression_value_placeholder_capital_camel_case():
    test_value = "VirusScannerResult"
    expected = ":VirusScannerResult_val"

    actual = create_expression_value_placeholder(test_value)

    assert actual == expected


def test_create_expression_value_placeholder_camel_case():
    test_value = "virusScannerResult"
    expected = ":VirusScannerResult_val"

    actual = create_expression_value_placeholder(test_value)

    assert actual == expected


def test_create_expression_attribute_placeholder_capital_camel_case():
    test_value = "VirusScannerResult"
    expected = "#VirusScannerResult_attr"

    actual = create_expression_attribute_placeholder(test_value)

    assert actual == expected


def test_create_expression_attribute_placeholder_camel_case():
    test_value = "virusScannerResult"
    expected = "#VirusScannerResult_attr"

    actual = create_expression_attribute_placeholder(test_value)

    assert actual == expected


def test_parse_dynamo_record_parses_correctly():
    test_data = MOCK_OLD_IMAGE_EVENT
    test_image = MOCK_OLD_IMAGE_MODEL

    expected = {
        "ContentType": test_image.content_type,
        "FileName": TEST_FILE_KEY,
        "Uploading": test_image.uploading,
        "TTL": test_image.ttl,
        "Created": test_image.created,
        "Uploaded": test_image.uploaded,
        "FileLocation": TEST_DOCUMENT_LOCATION,
        "CurrentGpOds": TEST_CURRENT_GP_ODS,
        "VirusScannerResult": test_image.virus_scanner_result,
        "Deleted": test_image.deleted,
        "ID": TEST_UUID,
        "LastUpdated": test_image.last_updated,
        "NhsNumber": TEST_NHS_NUMBER,
    }

    actual = parse_dynamo_record(test_data)

    assert actual == expected


@pytest.mark.parametrize(
    "test_json_string",
    [
        '{"Test": {"BOOL": "Not Bool"}}',
        '{"Test": {"N": "Not Integer"}}',
    ],
)
def test_parse_dynamo_record_raises_value_error(test_json_string):
    test_object = json.loads(test_json_string)

    with pytest.raises(ValueError):
        parse_dynamo_record(test_object)


@pytest.mark.parametrize(
    "doc_type, expected_table",
    [
        (SnomedCodes.LLOYD_GEORGE.value, MOCK_LG_TABLE_NAME),
        (SnomedCodes.PATIENT_DATA.value, MOCK_PDM_TABLE_NAME),
    ],
)
def test_dynamo_table_mapping(set_env, doc_type, expected_table):
    table_router = DocTypeTableRouter()
    table = table_router.resolve(doc_type)
    assert table == expected_table


@pytest.mark.parametrize(
    "doc_type",
    [
        SnomedCodes.GENERAL_MEDICAL_PRACTICE.value,
    ],
)
def test_dynamo_table_mapping_fails(set_env, doc_type):
    table_router = DocTypeTableRouter()
    with pytest.raises(InvalidDocTypeException) as excinfo:
        table_router.resolve(doc_type)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.DocTypeDB
