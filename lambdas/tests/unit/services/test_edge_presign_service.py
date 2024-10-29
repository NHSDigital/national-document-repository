import hashlib
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError
from services.edge_presign_service import EdgePresignService
from tests.unit.conftest import (
    MOCK_TABLE_NAME,
    MOCKED_LG_BUCKET_ENV,
    MOCKED_LG_BUCKET_URL,
)
from tests.unit.enums.test_edge_presign_values import (
    EXPECTED_EDGE_NO_CLIENT_ERROR_CODE,
    EXPECTED_EDGE_NO_CLIENT_ERROR_MESSAGE,
    EXPECTED_EDGE_NO_ORIGIN_ERROR_CODE,
    EXPECTED_EDGE_NO_ORIGIN_ERROR_MESSAGE,
    MOCKED_AUTH_QUERY,
)
from utils.lambda_exceptions import CloudFrontEdgeException


@pytest.fixture
@patch("services.edge_presign_service.SSMService")
@patch("services.edge_presign_service.DynamoDBService")
def edge_presign_service(mock_dynamo_service, mock_ssm_service):
    mock_ssm_service.get_ssm_parameter.return_value = MOCK_TABLE_NAME
    mock_dynamo_service.update_item.return_value = None
    return EdgePresignService()


@pytest.fixture
def request_values():
    return {
        "uri": "/some/path",
        "querystring": MOCKED_AUTH_QUERY,
        "domain_name": MOCKED_LG_BUCKET_URL,
    }


def test_use_presign(edge_presign_service, request_values):
    with patch.object(
        edge_presign_service, "attempt_presign_ingestion"
    ) as mock_attempt_presign_ingestion:
        edge_presign_service.use_presign(request_values)

        expected_hash = hashlib.md5(
            f"{request_values['uri']}?{request_values['querystring']}".encode("utf-8")
        ).hexdigest()
        mock_attempt_presign_ingestion.assert_called_once_with(
            uri_hash=expected_hash, domain_name=MOCKED_LG_BUCKET_URL
        )


def test_attempt_presign_ingestion_success(edge_presign_service):
    edge_presign_service.attempt_presign_ingestion("hashed_uri", MOCKED_LG_BUCKET_URL)


def test_attempt_presign_ingestion_client_error(edge_presign_service):
    client_error = ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException"}}, "UpdateItem"
    )
    edge_presign_service.dynamo_service.update_item.side_effect = client_error

    with pytest.raises(CloudFrontEdgeException) as exc_info:
        edge_presign_service.attempt_presign_ingestion(
            "hashed_uri", MOCKED_LG_BUCKET_URL
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.err_code == EXPECTED_EDGE_NO_CLIENT_ERROR_CODE
    assert exc_info.value.message == EXPECTED_EDGE_NO_CLIENT_ERROR_MESSAGE


def test_update_s3_headers(edge_presign_service, request_values):
    request = {
        "headers": {
            "host": [{"key": "Host", "value": MOCKED_LG_BUCKET_URL}],
        }
    }

    response = edge_presign_service.update_s3_headers(request, request_values)
    assert "authorization" not in response["headers"]
    assert response["headers"]["host"][0]["value"] == MOCKED_LG_BUCKET_URL


def test_filter_request_values_success(edge_presign_service):
    request = {
        "uri": "/test/uri",
        "querystring": MOCKED_AUTH_QUERY,
        "headers": {"host": [{"key": "Host", "value": MOCKED_LG_BUCKET_URL}]},
        "origin": {"s3": {"domainName": MOCKED_LG_BUCKET_URL}},
    }
    result = edge_presign_service.filter_request_values(request)
    assert result["uri"] == "/test/uri"
    assert result["querystring"] == MOCKED_AUTH_QUERY
    assert result["domain_name"] == MOCKED_LG_BUCKET_URL


def test_filter_request_values_missing_component(edge_presign_service):
    request = {
        "uri": "/test/uri",
        "querystring": MOCKED_AUTH_QUERY,
        "headers": {"host": [{"key": "Host", "value": MOCKED_LG_BUCKET_URL}]},
    }
    with pytest.raises(CloudFrontEdgeException) as exc_info:
        edge_presign_service.filter_request_values(request)

    assert exc_info.value.status_code == 500
    assert exc_info.value.err_code == EXPECTED_EDGE_NO_ORIGIN_ERROR_CODE
    assert exc_info.value.message == EXPECTED_EDGE_NO_ORIGIN_ERROR_MESSAGE


def test_filter_domain_for_env(edge_presign_service):
    # Environments
    assert (
        edge_presign_service.filter_domain_for_env("ndra-lloyd-test-test.com") == "ndra"
    )
    assert (
        edge_presign_service.filter_domain_for_env("pre-prod-lloyd-test-test.com")
        == "pre-prod"
    )
    # Production
    assert edge_presign_service.filter_domain_for_env("lloyd-test-test.com") == ""
    assert edge_presign_service.filter_domain_for_env("invalid.com") == ""


def test_extend_table_name(edge_presign_service):
    # Environments
    assert (
        edge_presign_service.extend_table_name(MOCK_TABLE_NAME, MOCKED_LG_BUCKET_ENV)
        == f"{MOCKED_LG_BUCKET_ENV}_{MOCK_TABLE_NAME}"
    )
    # Production
    assert (
        edge_presign_service.extend_table_name(MOCK_TABLE_NAME, "") == MOCK_TABLE_NAME
    )
