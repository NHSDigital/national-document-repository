import copy
import json
from unittest.mock import Mock

import pytest
from handlers.edge_presign_handler import lambda_handler
from tests.unit.enums.test_edge_presign_values import (
    EXPECTED_DOMAIN,
    EXPECTED_EDGE_MALFORMED_HEADER_ERROR_CODE,
    EXPECTED_EDGE_MALFORMED_HEADER_MESSAGE,
    EXPECTED_EDGE_MALFORMED_QUERY_ERROR_CODE,
    EXPECTED_EDGE_MALFORMED_QUERY_MESSAGE,
    EXPECTED_EDGE_NO_ORIGIN_ERROR_CODE,
    EXPECTED_EDGE_NO_ORIGIN_ERROR_MESSAGE,
    EXPECTED_EDGE_NO_QUERY_ERROR_CODE,
    EXPECTED_EDGE_NO_QUERY_MESSAGE,
    VALID_EVENT_MODEL,
)


def mock_context():
    context = Mock()
    context.aws_request_id = "fake_request_id"
    return context


@pytest.fixture
def valid_event():
    return copy.deepcopy(VALID_EVENT_MODEL)


@pytest.fixture
def mock_edge_presign_service(mocker):
    # Mock the EdgePresignService class
    mock_edge_presign_service = mocker.patch(
        "services.edge_presign_service.EdgePresignService"
    )
    mock_service_instance = mock_edge_presign_service.return_value

    # Mock the methods in the EdgePresignService class
    mock_service_instance.extract_request_values.return_value = {
        "uri": "/some/path",
        "querystring": "X-Amz-Algorithm=algo&X-Amz-Credential=cred&X-Amz-Date=date"
        "&X-Amz-Expires=3600&X-Amz-SignedHeaders=signed"
        "&X-Amz-Signature=sig&X-Amz-Security-Token=token",
        "headers": {"host": [{"key": "Host", "value": "example.gov.uk"}]},
        "domain_name": EXPECTED_DOMAIN,
    }
    mock_service_instance.presign_request.return_value = None
    mock_service_instance.prepare_s3_response.return_value = {
        "headers": {
            "host": [{"key": "Host", "value": EXPECTED_DOMAIN}],
        }
    }
    return mock_service_instance


def test_lambda_handler_success(valid_event, mock_edge_presign_service):
    context = mock_context()

    # Update event to include required headers and querystring
    valid_event["Records"][0]["cf"]["request"]["headers"][
        "cloudfront-viewer-country"
    ] = [{"key": "CloudFront-Viewer-Country", "value": "US"}]
    valid_event["Records"][0]["cf"]["request"]["headers"]["x-forwarded-for"] = [
        {"key": "X-Forwarded-For", "value": "1.2.3.4"}
    ]
    valid_event["Records"][0]["cf"]["request"]["querystring"] = (
        "?X-Amz-Algorithm=algo&X-Amz-Credential=cred&X-Amz-Date=date"
        "&X-Amz-Expires=3600&X-Amz-SignedHeaders=signed"
        "&X-Amz-Signature=sig&X-Amz-Security-Token=token"
    )

    # Call the Lambda handler
    response = lambda_handler(valid_event, context)

    # Verify that the mock methods were called as expected
    mock_edge_presign_service.extract_request_values.assert_called_once()
    mock_edge_presign_service.presign_request.assert_called_once_with(
        mock_edge_presign_service.extract_request_values.return_value
    )
    mock_edge_presign_service.prepare_s3_response.assert_called_once_with(
        valid_event["Records"][0]["cf"]["request"],
        mock_edge_presign_service.extract_request_values.return_value,
    )

    # Validate the response content
    assert response["headers"]["host"][0]["value"] == EXPECTED_DOMAIN
    assert "authorization" not in response["headers"]


def test_lambda_handler_no_query_params(valid_event, mock_edge_presign_service):
    context = mock_context()
    event = copy.deepcopy(valid_event)
    event["Records"][0]["cf"]["request"]["querystring"] = ""

    response = lambda_handler(event, context)

    actual_status = response["status"]
    actual_response = json.loads(response["body"])

    assert actual_status == 500
    assert actual_response["message"] == EXPECTED_EDGE_NO_QUERY_MESSAGE
    assert actual_response["err_code"] == EXPECTED_EDGE_NO_QUERY_ERROR_CODE


def test_lambda_handler_missing_query_params(valid_event, mock_edge_presign_service):
    context = mock_context()
    event = copy.deepcopy(valid_event)
    event["Records"][0]["cf"]["request"]["querystring"] = (
        "?X-Amz-Algorithm=algo&X-Amz-Credential=cred&X-Amz-Date=date"
        "&X-Amz-Expires=3600"
    )

    response = lambda_handler(event, context)

    actual_status = response["status"]
    actual_response = json.loads(response["body"])

    assert actual_status == 500
    assert actual_response["message"] == EXPECTED_EDGE_MALFORMED_QUERY_MESSAGE
    assert actual_response["err_code"] == EXPECTED_EDGE_MALFORMED_QUERY_ERROR_CODE


def test_lambda_handler_missing_headers(valid_event, mock_edge_presign_service):
    context = mock_context()
    event = copy.deepcopy(valid_event)
    event["Records"][0]["cf"]["request"]["headers"] = {}
    event["Records"][0]["cf"]["request"]["querystring"] = (
        "?X-Amz-Algorithm=algo&X-Amz-Credential=cred&X-Amz-Date=date"
        "&X-Amz-Expires=3600&X-Amz-SignedHeaders=signed"
        "&X-Amz-Signature=sig&X-Amz-Security-Token=token"
    )

    response = lambda_handler(event, context)

    actual_status = response["status"]
    actual_response = json.loads(response["body"])

    assert actual_status == 500
    assert actual_response["message"] == EXPECTED_EDGE_MALFORMED_HEADER_MESSAGE
    assert actual_response["err_code"] == EXPECTED_EDGE_MALFORMED_HEADER_ERROR_CODE


def test_lambda_handler_missing_origin(valid_event, mock_edge_presign_service):
    context = mock_context()
    event = copy.deepcopy(valid_event)
    event["Records"][0]["cf"]["request"]["origin"] = {}
    event["Records"][0]["cf"]["request"]["querystring"] = (
        "?X-Amz-Algorithm=algo&X-Amz-Credential=cred&X-Amz-Date=date"
        "&X-Amz-Expires=3600&X-Amz-SignedHeaders=signed"
        "&X-Amz-Signature=sig&X-Amz-Security-Token=token"
    )

    response = lambda_handler(event, context)

    actual_status = response["status"]
    actual_response = json.loads(response["body"])

    assert actual_status == 500
    assert actual_response["message"] == EXPECTED_EDGE_NO_ORIGIN_ERROR_MESSAGE
    assert actual_response["err_code"] == EXPECTED_EDGE_NO_ORIGIN_ERROR_CODE
