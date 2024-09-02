import pytest
from botocore.exceptions import ClientError
from services.edge_presign_service import EdgePresignService

# Instantiate the service for testing
edge_presign_service = EdgePresignService()

# Global Variables
TABLE_NAME = "CloudFrontEdgeReference"
NHS_DOMAIN = "access-request-fulfilment.patient-deductions.nhs.uk"


@pytest.fixture
def mock_dynamo_service(mocker):
    return mocker.patch.object(edge_presign_service, "dynamo_service", autospec=True)


@pytest.fixture
def mock_s3_service(mocker):
    return mocker.patch.object(edge_presign_service, "s3_service", autospec=True)


@pytest.fixture
def valid_origin_url():
    return f"https://test.{NHS_DOMAIN}"


@pytest.fixture
def invalid_origin_url():
    return f"https://invalid.{NHS_DOMAIN}"


def test_attempt_url_update_success(mock_dynamo_service, valid_origin_url):
    # Setup
    mock_dynamo_service.update_conditional.return_value = None
    uri_hash = "valid_hash"

    # Action
    response = edge_presign_service.attempt_url_update(
        table_name=TABLE_NAME,
        uri_hash=uri_hash,
        origin_url=valid_origin_url,
    )

    # Assert
    assert response is None  # Success scenario returns None
    mock_dynamo_service.update_conditional.assert_called_once_with(
        table_name="test_" + TABLE_NAME,
        key=uri_hash,
        updated_fields={"IsRequested": True},
        condition_expression="attribute_not_exists(IsRequested) OR IsRequested = :false",
        expression_attribute_values={":false": False},
    )


def test_attempt_url_update_client_error(mock_dynamo_service, valid_origin_url):
    # Setup
    mock_dynamo_service.update_conditional.side_effect = ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException"}}, "UpdateItem"
    )
    uri_hash = "valid_hash"

    # Action
    response = edge_presign_service.attempt_url_update(
        table_name=TABLE_NAME,
        uri_hash=uri_hash,
        origin_url=valid_origin_url,
    )

    # Assert
    expected_response = {
        "status": "404",
        "statusDescription": "Not Found",
        "headers": {
            "content-type": [{"key": "Content-Type", "value": "text/plain"}],
            "content-encoding": [{"key": "Content-Encoding", "value": "UTF-8"}],
        },
        "body": "Not Found",
    }
    assert response == expected_response


def test_attempt_url_update_generic_exception(mock_dynamo_service, valid_origin_url):
    # Setup
    mock_dynamo_service.update_conditional.side_effect = Exception("Some generic error")
    uri_hash = "valid_hash"

    # Action
    response = edge_presign_service.attempt_url_update(
        table_name=TABLE_NAME,
        uri_hash=uri_hash,
        origin_url=valid_origin_url,
    )

    # Assert
    expected_response = {
        "status": "500",
        "statusDescription": "Internal Server Error",
        "headers": {
            "content-type": [{"key": "Content-Type", "value": "text/plain"}],
            "content-encoding": [{"key": "Content-Encoding", "value": "UTF-8"}],
        },
        "body": "Internal Server Error",
    }
    assert response == expected_response


def test_extract_environment_from_url():
    # Test with valid NHS domain URL
    url = f"https://test.{NHS_DOMAIN}/path/to/resource"
    expected = "test"
    actual = edge_presign_service.extract_environment_from_url(url)
    assert actual == expected

    # Test with invalid URL (missing the environment part)
    url = f"https://{NHS_DOMAIN}/path/to/resource"
    expected = ""
    actual = edge_presign_service.extract_environment_from_url(url)
    assert actual == expected


def test_extend_table_name():
    # Test with valid environment
    base_table_name = TABLE_NAME
    environment = "test"
    expected = "test_" + base_table_name
    actual = edge_presign_service.extend_table_name(base_table_name, environment)
    assert actual == expected

    # Test with no environment
    environment = ""
    expected = base_table_name
    actual = edge_presign_service.extend_table_name(base_table_name, environment)
    assert actual == expected
