from datetime import datetime
from typing import Any, Dict

import inflection
from enums.dynamo_filter import AttributeOperator
from enums.lambda_error import LambdaError
from enums.snomed_codes import SnomedCode, SnomedCodes
from utils.audit_logging_setup import LoggingService
from utils.common_query_filters import get_not_deleted_filter
from utils.dynamo_query_filter_builder import DynamoQueryFilterBuilder
from utils.lambda_exceptions import CreateDocumentRefException

logger = LoggingService(__name__)


def create_expressions(requested_fields: list) -> tuple[str, dict]:
    """
    Creates expression components for a dynamo query
        :param requested_fields: List of enum fields names

    example usage:
        requested_fields = ["ID", "Created", "FileName"]
        projection_expression, expression_attribute_names = create_expressions(requested_fields)

    result:
        [
            "#ID_attr,#Created_attr,#FileName_attr",
            {"#ID_attr": "ID", "#Created_attr": "Created", "#FileName_attr": "FileName"}
        ]
    """
    projection_expression = ""
    expression_attribute_names = {}

    for field_definition in requested_fields:
        field_placeholder = create_expression_attribute_placeholder(field_definition)
        if len(projection_expression) > 0:
            projection_expression = f"{projection_expression},{field_placeholder}"
        else:
            projection_expression = field_placeholder

        expression_attribute_names[field_placeholder] = field_definition
    return projection_expression, expression_attribute_names


def create_update_expression(field_names: list) -> str:
    """
    Creates an expression for dynamodb queries to SET a new value for an item
        :param field_names: List of fields to update

    example usage:
        field_names = ["Name", "Age"...]
        fields_filter = create_update_expression(field_names)

    result:
        "SET #Name_attr = :Name_val, #Age_attr = :Age_val"

    """
    update_expression = "SET"
    for field in field_names:
        expression = f" {create_expression_attribute_placeholder(field)} = {create_expression_value_placeholder(field)}"
        if update_expression == "SET":
            update_expression += expression
        else:
            update_expression += f",{expression}"

    return update_expression


def create_expression_attribute_values(attribute_field_values: dict) -> dict:
    """
    Maps a dict of expression names and expression values to create a dictionary to pass into query
        :param attribute_field_values: Dictionary of attribute field names and values

    example usage:
        attribute_field_values = {
                DocumentReferenceMetadataFields.DELETED.value: "",
                DocumentReferenceMetadataFields.FILENAME.value: "Test Filename"
            }
        expression_attribute_values = create_expression_attribute_values(attribute_field_values)

    result:
        {
            ":Deleted_val" : ""
            ":FileName_val" : "Test Filename"
        }
    """
    expression_attribute_values = {}
    for field_name, field_value in attribute_field_values.items():
        expression_attribute_values[
            f"{create_expression_value_placeholder(field_name)}"
        ] = field_value

    return expression_attribute_values


def create_expression_value_placeholder(value: str) -> str:
    """
    Creates a placeholder value for an expression attribute name
        :param value: Value to change into a placeholder

    example usage:
        placeholder = create_expression_value_placeholder("VirusScanResult")

    result:
        ":VirusScanResult_val"
    """
    return f":{inflection.camelize(value, uppercase_first_letter=True)}_val"


def create_expression_attribute_placeholder(value: str) -> str:
    """
    Creates a placeholder value for a projection attribute name
        :param value: Value to change into a placeholder

    example usage:
        placeholder = create_expression_attribute_placeholder("VirusScanResult")

    result:
        "#VirusScanResult_attr"
    """
    return f"#{inflection.camelize(value, uppercase_first_letter=True)}_attr"


def filter_uploaded_docs_and_recently_uploading_docs():
    filter_builder = DynamoQueryFilterBuilder()
    time_limit = int(datetime.now().timestamp() - (60 * 3))

    delete_filter_expression = get_not_deleted_filter(filter_builder)

    filter_builder.add_condition("Uploaded", AttributeOperator.EQUAL, True)
    uploaded_filter_expression = filter_builder.build()

    filter_builder.add_condition(
        "Uploading", AttributeOperator.EQUAL, True
    ).add_condition("LastUpdated", AttributeOperator.GREATER_OR_EQUAL, time_limit)
    uploading_filter_expression = filter_builder.build()

    return delete_filter_expression & (
        uploaded_filter_expression | uploading_filter_expression
    )


def parse_dynamo_record(dynamodb_record: Dict[str, Any]) -> Dict[str, Any]:
    result = {}
    for key, value in dynamodb_record.items():
        match value:
            case {"S": str(s)}:
                result[key] = s
            case {"N": str(n)}:
                result[key] = int(n)
            case {"BOOL": bool(b)}:
                result[key] = b
            case _:
                raise ValueError(f"Unsupported DynamoDB type for key {key}: {value}")
    return result


class DocTypeTableRouter:
    def __init__(self, lg_dynamo_table: str, pdm_dynamo_table: str):
        self.mapping = {
            SnomedCodes.LLOYD_GEORGE.value.code: lg_dynamo_table,
            SnomedCodes.UNSTRUCTURED.value.code: pdm_dynamo_table,
        }

    def resolve(self, doc_type: SnomedCode) -> str:
        try:
            return self.mapping[doc_type.code]
        except KeyError:
            logger.error(
                f"SNOMED code {doc_type.code} - {doc_type.display_name} is not supported"
            )
            raise CreateDocumentRefException(400, LambdaError.CreateDocInvalidType)
