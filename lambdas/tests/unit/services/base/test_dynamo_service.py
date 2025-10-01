import copy
from unittest.mock import call

import pytest
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError
from enums.dynamo_filter import AttributeOperator
from enums.metadata_field_names import DocumentReferenceMetadataFields
from services.base.dynamo_service import DynamoDBService
from tests.unit.conftest import MOCK_CLIENT_ERROR, MOCK_TABLE_NAME, TEST_NHS_NUMBER
from tests.unit.helpers.data.dynamo.dynamo_responses import MOCK_SEARCH_RESPONSE
from tests.unit.helpers.data.dynamo.dynamo_scan_response import (
    EXPECTED_ITEMS_FOR_PAGINATED_RESULTS,
    MOCK_PAGINATED_RESPONSE_1,
    MOCK_PAGINATED_RESPONSE_2,
    MOCK_PAGINATED_RESPONSE_3,
    MOCK_RESPONSE,
)
from utils.dynamo_query_filter_builder import DynamoQueryFilterBuilder
from utils.exceptions import DynamoServiceException


@pytest.fixture
def mock_service(set_env, mocker):
    mocker.patch("boto3.resource")
    service = DynamoDBService()
    yield service
    DynamoDBService.instance = None


@pytest.fixture
def mock_dynamo_service(mocker, mock_service):
    dynamo = mocker.patch.object(mock_service, "dynamodb")
    yield dynamo


@pytest.fixture
def mock_table(mocker, mock_service):
    yield mocker.patch.object(mock_service, "get_table")


@pytest.fixture
def mock_scan_method(mock_table):
    table_instance = mock_table.return_value
    scan_method = table_instance.scan
    yield scan_method


@pytest.fixture
def mock_filter_expression():
    filter_builder = DynamoQueryFilterBuilder()
    filter_expression = filter_builder.add_condition(
        attribute=str(DocumentReferenceMetadataFields.DELETED.value),
        attr_operator=AttributeOperator.EQUAL,
        filter_value="",
    ).build()
    yield filter_expression


def mock_scan_implementation(**kwargs):
    key = kwargs.get("ExclusiveStartKey")
    if not key:
        return copy.deepcopy(MOCK_PAGINATED_RESPONSE_1)
    elif key.get("ID") == "id_token_for_page_2":
        return copy.deepcopy(MOCK_PAGINATED_RESPONSE_2)
    elif key.get("ID") == "id_token_for_page_3":
        return copy.deepcopy(MOCK_PAGINATED_RESPONSE_3)
    return None


def test_query_with_requested_fields_returns_items_from_dynamo(
    mock_service, mock_table
):
    search_key_obj = Key("NhsNumber").eq(TEST_NHS_NUMBER)
    expected_projection = "FileName,Created"

    mock_table.return_value.query.return_value = MOCK_SEARCH_RESPONSE
    expected = MOCK_SEARCH_RESPONSE["Items"]

    actual = mock_service.query_table(
        table_name=MOCK_TABLE_NAME,
        index_name="NhsNumberIndex",
        search_key="NhsNumber",
        search_condition=TEST_NHS_NUMBER,
        requested_fields=[
            DocumentReferenceMetadataFields.FILE_NAME.value,
            DocumentReferenceMetadataFields.CREATED.value,
        ],
    )

    mock_table.assert_called_with(MOCK_TABLE_NAME)
    mock_table.return_value.query.assert_called_once_with(
        IndexName="NhsNumberIndex",
        KeyConditionExpression=search_key_obj,
        ProjectionExpression=expected_projection,
    )

    assert expected == actual


def test_query_with_requested_fields_with_filter_returns_items_from_dynamo(
    mock_service, mock_table, mock_filter_expression
):
    search_key_obj = Key("NhsNumber").eq(TEST_NHS_NUMBER)
    expected_projection = "FileName,Created"
    expected_filter = Attr("Deleted").eq("")

    mock_table.return_value.query.return_value = MOCK_SEARCH_RESPONSE
    expected = MOCK_SEARCH_RESPONSE["Items"]

    actual = mock_service.query_table(
        table_name=MOCK_TABLE_NAME,
        index_name="NhsNumberIndex",
        search_key="NhsNumber",
        search_condition=TEST_NHS_NUMBER,
        requested_fields=[
            DocumentReferenceMetadataFields.FILE_NAME.value,
            DocumentReferenceMetadataFields.CREATED.value,
        ],
        query_filter=mock_filter_expression,
    )

    mock_table.assert_called_with(MOCK_TABLE_NAME)
    mock_table.return_value.query.assert_called_once_with(
        IndexName="NhsNumberIndex",
        KeyConditionExpression=search_key_obj,
        ProjectionExpression=expected_projection,
        FilterExpression=expected_filter,
    )

    assert expected == actual


def test_query_by_index_handles_pagination(
    mock_service, mock_table, mock_filter_expression
):
    mock_table.return_value.query.side_effect = [
        MOCK_PAGINATED_RESPONSE_1,
        MOCK_PAGINATED_RESPONSE_2,
        MOCK_PAGINATED_RESPONSE_3,
    ]
    expected_result = EXPECTED_ITEMS_FOR_PAGINATED_RESULTS
    search_key_obj = Key("NhsNumber").eq(TEST_NHS_NUMBER)

    expected_calls = [
        call(
            KeyConditionExpression=search_key_obj,
        ),
        call(
            KeyConditionExpression=search_key_obj,
            ExclusiveStartKey={"ID": "id_token_for_page_2"},
        ),
        call(
            KeyConditionExpression=search_key_obj,
            ExclusiveStartKey={"ID": "id_token_for_page_3"},
        ),
    ]

    actual = mock_service.query_table(
        table_name=MOCK_TABLE_NAME,
        search_key="NhsNumber",
        search_condition=TEST_NHS_NUMBER,
    )
    assert expected_result == actual
    mock_table.assert_called_with(MOCK_TABLE_NAME)
    mock_table.return_value.query.assert_has_calls(expected_calls)


def test_query_with_requested_fields_raises_exception_when_results_are_empty(
    mock_service, mock_table
):
    mock_table.return_value.query.return_value = []

    with pytest.raises(DynamoServiceException):
        mock_service.query_table(
            table_name=MOCK_TABLE_NAME,
            index_name="NhsNumberIndex",
            search_key="NhsNumber",
            search_condition=TEST_NHS_NUMBER,
            requested_fields=[
                DocumentReferenceMetadataFields.FILE_NAME.value,
                DocumentReferenceMetadataFields.CREATED.value,
            ],
        )


def test_query_with_requested_fields_raises_exception_when_fields_requested_is_none(
    mock_service, mock_table
):
    search_key_obj = Key("NhsNumber").eq(TEST_NHS_NUMBER)

    mock_table.return_value.query.return_value = MOCK_SEARCH_RESPONSE
    expected = MOCK_SEARCH_RESPONSE["Items"]

    actual = mock_service.query_table(
        table_name=MOCK_TABLE_NAME,
        index_name="test_index",
        search_key="NhsNumber",
        search_condition=TEST_NHS_NUMBER,
    )
    mock_table.assert_called_with(MOCK_TABLE_NAME)
    mock_table.return_value.query.assert_called_once_with(
        IndexName="test_index",
        KeyConditionExpression=search_key_obj,
    )

    assert expected == actual


def test_query_with_requested_fields_client_error_raises_exception(
    mock_service, mock_table
):
    expected_response = MOCK_CLIENT_ERROR
    mock_table.return_value.query.side_effect = MOCK_CLIENT_ERROR

    with pytest.raises(ClientError) as actual_response:
        mock_service.query_table(
            MOCK_TABLE_NAME,
            "NhsNumberIndex",
            "NhsNumber",
            TEST_NHS_NUMBER,
            [
                DocumentReferenceMetadataFields.FILE_NAME.value,
                DocumentReferenceMetadataFields.CREATED.value,
            ],
        )

    assert expected_response == actual_response.value


def test_query_table_is_called_with_correct_parameters(mock_service, mock_table):
    mock_table.return_value.query.return_value = {
        "Items": [{"id": "fake_test_item"}],
        "Counts": 1,
    }

    mock_service.query_table(MOCK_TABLE_NAME, "test_key_condition", "test_key_value")

    mock_table.assert_called_with(MOCK_TABLE_NAME)
    mock_table.return_value.query.assert_called_once_with(
        KeyConditionExpression=Key("test_key_condition").eq("test_key_value"),
    )


def test_query_table_raises_exception_when_results_are_empty(mock_service, mock_table):
    mock_table.return_value.query.return_value = []

    with pytest.raises(DynamoServiceException):
        mock_service.query_table(
            MOCK_TABLE_NAME, "test_key_condition", "test_key_value"
        )

    mock_table.assert_called_with(MOCK_TABLE_NAME)
    mock_table.return_value.query.assert_called_once_with(
        KeyConditionExpression=Key("test_key_condition").eq("test_key_value")
    )


def test_query_table_client_error_raises_exception(mock_service, mock_table):
    expected_response = MOCK_CLIENT_ERROR
    mock_table.return_value.query.side_effect = MOCK_CLIENT_ERROR

    with pytest.raises(ClientError) as actual_response:
        mock_service.query_table(
            MOCK_TABLE_NAME, "test_key_condition", "test_key_value"
        )

    assert expected_response == actual_response.value


def test_create_item_is_called_with_correct_parameters(mock_service, mock_table):
    mock_service.create_item(MOCK_TABLE_NAME, {"NhsNumber": TEST_NHS_NUMBER})

    mock_table.assert_called_with(MOCK_TABLE_NAME)
    mock_table.return_value.put_item.assert_called_once_with(
        Item={"NhsNumber": TEST_NHS_NUMBER}
    )


def test_create_item_raise_client_error(mock_service, mock_table):
    mock_service.create_item(MOCK_TABLE_NAME, {"NhsNumber": TEST_NHS_NUMBER})
    mock_table.return_value.put_item.side_effect = MOCK_CLIENT_ERROR

    mock_table.assert_called_with(MOCK_TABLE_NAME)
    mock_table.return_value.put_item.assert_called_once_with(
        Item={"NhsNumber": TEST_NHS_NUMBER}
    )

    with pytest.raises(ClientError) as actual_response:
        mock_service.create_item(MOCK_TABLE_NAME, {"NhsNumber": TEST_NHS_NUMBER})

    assert MOCK_CLIENT_ERROR == actual_response.value


def test_delete_item_is_called_with_correct_parameters(mock_service, mock_table):
    mock_service.delete_item(MOCK_TABLE_NAME, {"NhsNumber": TEST_NHS_NUMBER})

    mock_table.assert_called_with(MOCK_TABLE_NAME)
    mock_table.return_value.delete_item.assert_called_once_with(
        Key={"NhsNumber": TEST_NHS_NUMBER}
    )


def test_delete_item_client_error_raises_exception(mock_service, mock_table):
    expected_response = MOCK_CLIENT_ERROR
    mock_table.return_value.delete_item.side_effect = MOCK_CLIENT_ERROR

    with pytest.raises(ClientError) as actual_response:
        mock_service.delete_item(MOCK_TABLE_NAME, {"NhsNumber": TEST_NHS_NUMBER})

    assert expected_response == actual_response.value


def test_get_item_is_called_with_correct_parameters(mock_service, mock_table):
    mock_service.get_item(MOCK_TABLE_NAME, {"NhsNumber": TEST_NHS_NUMBER})

    mock_table.assert_called_with(MOCK_TABLE_NAME)
    mock_table.return_value.get_item.assert_called_once_with(
        Key={"NhsNumber": TEST_NHS_NUMBER}
    )


def test_get_item_client_error_raises_exception(mock_service, mock_table):
    expected_response = MOCK_CLIENT_ERROR
    mock_table.return_value.get_item.side_effect = MOCK_CLIENT_ERROR

    with pytest.raises(ClientError) as actual_response:
        mock_service.get_item(MOCK_TABLE_NAME, {"NhsNumber": TEST_NHS_NUMBER})

    assert expected_response == actual_response.value


def test_batch_get_items_success(mock_service, mock_dynamo_service):
    key_list = ["id1", "id2", "id3"]
    mock_response = {
        "Responses": {
            MOCK_TABLE_NAME: [
                {"ID": "id1", "data": "value1"},
                {"ID": "id2", "data": "value2"},
                {"ID": "id3", "data": "value3"},
            ]
        }
    }
    mock_dynamo_service.batch_get_item.return_value = mock_response

    results = mock_service.batch_get_items(MOCK_TABLE_NAME, key_list)

    expected_request_items = {
        MOCK_TABLE_NAME: {"Keys": [{"ID": "id1"}, {"ID": "id2"}, {"ID": "id3"}]}
    }
    mock_dynamo_service.batch_get_item.assert_called_once_with(
        RequestItems=expected_request_items
    )
    assert len(results) == 3
    assert results[0]["ID"] == "id1"
    assert results[1]["ID"] == "id2"
    assert results[2]["ID"] == "id3"


def test_batch_get_items_with_unprocessed_keys(mock_service, mock_dynamo_service):
    key_list = ["id1", "id2", "id3"]

    first_response = {
        "Responses": {MOCK_TABLE_NAME: [{"ID": "id1", "data": "value1"}]},
        "UnprocessedKeys": {MOCK_TABLE_NAME: {"Keys": [{"ID": "id2"}, {"ID": "id3"}]}},
    }

    second_response = {
        "Responses": {
            MOCK_TABLE_NAME: [
                {"ID": "id2", "data": "value2"},
                {"ID": "id3", "data": "value3"},
            ]
        }
    }

    mock_dynamo_service.batch_get_item.side_effect = [first_response, second_response]

    result = mock_service.batch_get_items(MOCK_TABLE_NAME, key_list)

    assert mock_dynamo_service.batch_get_item.call_count == 2
    assert len(result) == 3
    assert [item["ID"] for item in result] == ["id1", "id2", "id3"]


def test_batch_get_items_with_too_many_keys(mock_service, mock_dynamo_service):
    key_list = [f"id{i}" for i in range(101)]

    result = mock_service.batch_get_items(MOCK_TABLE_NAME, key_list)

    assert isinstance(result, DynamoServiceException)
    assert str(result) == "Cannot fetch more than 100 items at a time"
    mock_dynamo_service.batch_get_item.assert_not_called()


def test_batch_get_items_with_exception(mock_service, mock_dynamo_service):
    key_list = ["id1", "id2"]
    mock_dynamo_service.batch_get_item.side_effect = Exception("Test exception")

    with pytest.raises(Exception) as excinfo:
        mock_service.batch_get_items(MOCK_TABLE_NAME, key_list)

    assert str(excinfo.value) == "Test exception"

    expected_request_items = {MOCK_TABLE_NAME: {"Keys": [{"ID": "id1"}, {"ID": "id2"}]}}
    mock_dynamo_service.batch_get_item.assert_called_once_with(
        RequestItems=expected_request_items
    )


def test_update_item_is_called_with_correct_parameters(mock_service, mock_table):
    update_key = {"ID": "9000000009"}
    expected_update_expression = (
        "SET #FileName_attr = :FileName_val, #Deleted_attr = :Deleted_val"
    )
    expected_expr_attr_names = {
        "#FileName_attr": "FileName",
        "#Deleted_attr": "Deleted",
    }
    expected_expr_attr_values = {
        ":FileName_val": "test-filename",
        ":Deleted_val": "test-delete",
    }

    mock_service.update_item(
        table_name=MOCK_TABLE_NAME,
        key_pair={"ID": TEST_NHS_NUMBER},
        updated_fields={
            DocumentReferenceMetadataFields.FILE_NAME.value: "test-filename",
            DocumentReferenceMetadataFields.DELETED.value: "test-delete",
        },
    )

    mock_table.assert_called_with(MOCK_TABLE_NAME)
    mock_table.return_value.update_item.assert_called_once_with(
        Key=update_key,
        UpdateExpression=expected_update_expression,
        ExpressionAttributeNames=expected_expr_attr_names,
        ExpressionAttributeValues=expected_expr_attr_values,
        ReturnValues="ALL_NEW",
    )


def test_update_item_client_error_raises_exception(mock_service, mock_table):
    expected_response = MOCK_CLIENT_ERROR
    mock_table.return_value.update_item.side_effect = MOCK_CLIENT_ERROR

    with pytest.raises(ClientError) as actual_response:
        mock_service.update_item(
            MOCK_TABLE_NAME,
            {"ID": TEST_NHS_NUMBER},
            {
                DocumentReferenceMetadataFields.FILE_NAME.value: "test-filename",
                DocumentReferenceMetadataFields.DELETED.value: "test-delete",
            },
        )

    assert expected_response == actual_response.value


def test_scan_table_is_called_with_correct_no_args(mock_service, mock_table):
    mock_table.return_value.scan.return_value = []

    mock_service.scan_table(MOCK_TABLE_NAME)
    mock_table.return_value.scan.assert_called_once()


def test_scan_table_is_called_with_with_filter(mock_service, mock_table):
    mock_table.return_value.scan.return_value = []

    mock_service.scan_table(MOCK_TABLE_NAME, filter_expression="filter_test")
    mock_table.return_value.scan.assert_called_once_with(FilterExpression="filter_test")


def test_scan_table_with_is_called_with_start_key(mock_service, mock_table):
    mock_table.return_value.scan.return_value = []

    mock_service.scan_table(
        MOCK_TABLE_NAME, exclusive_start_key={"key": "exclusive_start_key"}
    )
    mock_table.return_value.scan.assert_called_once_with(
        ExclusiveStartKey={"key": "exclusive_start_key"}
    )


def test_scan_table_is_called_correctly_with_start_key_and_filter(
    mock_service, mock_table
):
    mock_table.return_value.scan.return_value = []

    mock_service.scan_table(
        MOCK_TABLE_NAME,
        exclusive_start_key={"key": "exclusive_start_key"},
        filter_expression="filter_test",
    )
    mock_table.return_value.scan.assert_called_once_with(
        ExclusiveStartKey={"key": "exclusive_start_key"},
        FilterExpression="filter_test",
    )


def test_scan_table_client_error_raises_exception(mock_service, mock_table):
    expected_response = MOCK_CLIENT_ERROR
    mock_table.return_value.scan.side_effect = expected_response

    with pytest.raises(ClientError) as actual_response:
        mock_service.scan_table(
            MOCK_TABLE_NAME,
            exclusive_start_key={"key": "exclusive_start_key"},
            filter_expression="filter_test",
        )

    assert expected_response == actual_response.value


def test_scan_whole_table_return_items_in_response(
    mock_service, mock_scan_method, mock_filter_expression
):
    mock_project_expression = "mock_project_expression"
    mock_scan_method.return_value = MOCK_RESPONSE

    expected = MOCK_RESPONSE["Items"]
    actual = mock_service.scan_whole_table(
        table_name=MOCK_TABLE_NAME,
        project_expression=mock_project_expression,
        filter_expression=mock_filter_expression,
    )

    assert expected == actual

    mock_service.get_table.assert_called_with(MOCK_TABLE_NAME)
    mock_scan_method.assert_called_with(
        ProjectionExpression=mock_project_expression,
        FilterExpression=mock_filter_expression,
    )


def test_scan_whole_table_handles_pagination(
    mock_service, mock_scan_method, mock_filter_expression
):
    mock_project_expression = "mock_project_expression"
    mock_scan_method.side_effect = mock_scan_implementation

    expected_result = EXPECTED_ITEMS_FOR_PAGINATED_RESULTS
    expected_calls = [
        call(
            ProjectionExpression=mock_project_expression,
            FilterExpression=mock_filter_expression,
        ),
        call(
            ProjectionExpression=mock_project_expression,
            FilterExpression=mock_filter_expression,
            ExclusiveStartKey={"ID": "id_token_for_page_2"},
        ),
        call(
            ProjectionExpression=mock_project_expression,
            FilterExpression=mock_filter_expression,
            ExclusiveStartKey={"ID": "id_token_for_page_3"},
        ),
    ]

    actual = mock_service.scan_whole_table(
        table_name=MOCK_TABLE_NAME,
        project_expression=mock_project_expression,
        filter_expression=mock_filter_expression,
    )

    assert expected_result == actual

    mock_service.get_table.assert_called_with(MOCK_TABLE_NAME)
    mock_scan_method.assert_has_calls(expected_calls)


def test_scan_whole_table_omit_expression_arguments_if_not_given(
    mock_service, mock_scan_method
):
    mock_service.scan_whole_table(
        table_name=MOCK_TABLE_NAME,
    )

    mock_service.get_table.assert_called_with(MOCK_TABLE_NAME)
    mock_scan_method.assert_called_with()


def test_get_table_when_table_exists_then_table_is_returned_successfully(
    mock_service, mock_dynamo_service
):
    mock_service.get_table(
        MOCK_TABLE_NAME,
    )

    mock_dynamo_service.Table.assert_called_once_with(MOCK_TABLE_NAME)


def test_get_table_when_table_does_not_exists_then_exception_is_raised(
    mock_service, mock_dynamo_service
):
    expected_response = MOCK_CLIENT_ERROR
    mock_dynamo_service.Table.side_effect = expected_response

    with pytest.raises(ClientError) as actual_response:
        mock_service.get_table(
            MOCK_TABLE_NAME,
        )

    assert expected_response == actual_response.value


def test_dynamo_service_singleton_instance(mocker):
    mocker.patch("boto3.resource")

    instance_1 = DynamoDBService()
    instance_2 = DynamoDBService()

    assert instance_1 is instance_2


def test_query_table_with_pagination(mock_service, mock_table):
    mock_table.return_value.query.side_effect = mock_scan_implementation
    expected_result = EXPECTED_ITEMS_FOR_PAGINATED_RESULTS
    search_key_obj = Key("NhsNumber").eq(TEST_NHS_NUMBER)

    expected_calls = [
        call(
            KeyConditionExpression=search_key_obj,
        ),
        call(
            KeyConditionExpression=search_key_obj,
            ExclusiveStartKey={"ID": "id_token_for_page_2"},
        ),
        call(
            KeyConditionExpression=search_key_obj,
            ExclusiveStartKey={"ID": "id_token_for_page_3"},
        ),
    ]

    actual = mock_service.query_table(
        table_name=MOCK_TABLE_NAME,
        search_key="NhsNumber",
        search_condition=TEST_NHS_NUMBER,
    )
    assert expected_result == actual
    mock_table.assert_called_with(MOCK_TABLE_NAME)
    mock_table.return_value.query.assert_has_calls(expected_calls)
