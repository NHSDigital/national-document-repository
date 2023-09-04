import json
import os
from dataclasses import dataclass
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError
from handlers.document_reference_search_handler import lambda_handler
from services.dynamo_query_service import DynamoQueryService
from tests.unit.helpers.dynamo_responses import (EXPECTED_RESPONSE,
                                                 MOCK_EMPTY_RESPONSE,
                                                 MOCK_RESPONSE,
                                                 UNEXPECTED_RESPONSE)
from utils.exceptions import InvalidResourceIdException
from utils.lambda_response import ApiGatewayResponse

PATCH_ENV_VAR = {
    "DOCUMENT_STORE_DYNAMODB_NAME": "a_real_table",
    "LLOYD_GEORGE_DYNAMODB_NAME": "another_real_table",
}


@pytest.fixture
def context():
    @dataclass
    class LambdaContext:
        function_name: str = "test"
        aws_request_id: str = "88888888-4444-4444-4444-121212121212"
        invoked_function_arn: str = (
            "arn:aws:lambda:eu-west-1:123456789101:function:test"
        )

    return LambdaContext()


def test_lambda_handler_returns_items_from_dynamo(event_valid_id, context):
    with patch.dict(os.environ, PATCH_ENV_VAR):
        with patch.object(DynamoQueryService, "__call__", return_value=MOCK_RESPONSE):
            expected = ApiGatewayResponse(
                200, json.dumps(EXPECTED_RESPONSE), "GET"
            ).create_api_gateway_response()
            actual = lambda_handler(event_valid_id, context)
            assert expected == actual


def test_lambda_handler_returns_204_empty_list_when_dynamo_returns_no_records(
    event_valid_id, context
):
    with patch.dict(os.environ, PATCH_ENV_VAR):
        with patch.object(
            DynamoQueryService, "__call__", return_value=MOCK_EMPTY_RESPONSE
        ):
            expected = ApiGatewayResponse(204, [], "GET").create_api_gateway_response()
            actual = lambda_handler(event_valid_id, context)
            assert expected == actual


def test_lambda_handler_returns_500_when_dynamo_has_unexpected_response(
    event_valid_id, context
):
    with patch.dict(os.environ, PATCH_ENV_VAR):
        with patch.object(
            DynamoQueryService, "__call__", return_value=UNEXPECTED_RESPONSE
        ):
            expected = ApiGatewayResponse(
                500,
                "Unrecognised response when searching for available documents",
                "GET",
            ).create_api_gateway_response()
            actual = lambda_handler(event_valid_id, context)
            assert expected == actual


def test_lambda_handler_returns_400_when_id_not_valid(invalid_nhs_id_event, context):
    with patch.dict(os.environ, PATCH_ENV_VAR):
        expected = ApiGatewayResponse(
            400, "Invalid NHS number", "GET"
        ).create_api_gateway_response()
        actual = lambda_handler(invalid_nhs_id_event, context)
        assert expected == actual


def test_lambda_handler_returns_400_when_id_not_supplied(empty_nhs_id_event, context):
    with patch.dict(os.environ, PATCH_ENV_VAR):
        expected = ApiGatewayResponse(
            400, "Please supply an NHS number", "GET"
        ).create_api_gateway_response()
        actual = lambda_handler(empty_nhs_id_event, context)
        assert expected == actual


def test_lambda_handler_returns_500_when_client_error_thrown(event_valid_id, context):
    error = {"Error": {"Code": 500, "Message": "DynamoDB is down"}}

    exception = ClientError(error, "Query")
    with patch.dict(os.environ, PATCH_ENV_VAR):
        with patch.object(DynamoQueryService, "__call__", side_effect=exception):
            expected = ApiGatewayResponse(
                500, "An error occurred searching for available documents", "GET"
            ).create_api_gateway_response()
            actual = lambda_handler(event_valid_id, context)
            assert expected == actual


def test_lambda_handler_returns_500_when_no_fields_requested(event_valid_id, context):
    exception = InvalidResourceIdException
    with patch.dict(os.environ, PATCH_ENV_VAR):
        with patch.object(DynamoQueryService, "__call__", side_effect=exception):
            expected = ApiGatewayResponse(
                500, "No data was requested to be returned in query", "GET"
            ).create_api_gateway_response()
            actual = lambda_handler(event_valid_id, context)
            assert expected == actual
