import json
import pytest
from unittest.mock import patch, MagicMock
from services.migration_dynamodb_segment_service import MigrationDynamoDBSegmentService
from botocore.exceptions import ClientError, NoCredentialsError


@pytest.fixture
def mock_env_bucket_name(mocker):
    """Mocks the environment variable for bucket name"""
    return mocker.patch.dict('os.environ', {'MIGRATION_SEGMENT_BUCKET_NAME': 'test-bucket'})


@pytest.fixture
def mock_s3_client(mocker):
    """Mocks the boto3 S3 client"""
    mock_client = mocker.patch("services.migration_dynamodb_segment_service.boto3.client")
    return mock_client.return_value


@pytest.fixture
def service(mock_env_bucket_name, mock_s3_client):
    """Creates an instance of the service for testing"""
    return MigrationDynamoDBSegmentService()


@pytest.fixture
def mock_random_shuffle(mocker):
    """Mocks random.shuffle to make tests predictable"""
    return mocker.patch("services.migration_dynamodb_segment_service.random.shuffle")


# Success test cases
def test_segment_success(service, mock_s3_client, mock_random_shuffle):
    """Test successful segment operation"""
    # Arrange
    test_id = "test-execution-123"
    total_segments = 4
    
    # Mock shuffle to do nothing (keep original order for predictable testing)
    mock_random_shuffle.side_effect = lambda x: None
    
    expected_segments = [0, 1, 2, 3]
    expected_key = "stepfunctionconfig-test-execution-123.json"
    expected_body = json.dumps(expected_segments).encode()
    
    # Act
    result = service.segment(test_id, total_segments)
    
    # Assert
    mock_s3_client.put_object.assert_called_once_with(
        Bucket='test-bucket',
        Key=expected_key,
        Body=expected_body
    )
    
    expected_result = {
        'bucket': 'test-bucket',
        'key': expected_key
    }
    assert result == expected_result


def test_segment_with_single_segment(service, mock_s3_client, mock_random_shuffle):
    """Test with single segment"""
    # Arrange
    test_id = "single-segment"
    total_segments = 1
    
    mock_random_shuffle.side_effect = lambda x: None
    expected_segments = [0]
    
    # Act
    result = service.segment(test_id, total_segments)
    
    # Assert
    expected_body = json.dumps(expected_segments).encode()
    mock_s3_client.put_object.assert_called_once_with(
        Bucket='test-bucket',
        Key="stepfunctionconfig-single-segment.json",
        Body=expected_body
    )
    
    assert result['bucket'] == 'test-bucket'
    assert result['key'] == "stepfunctionconfig-single-segment.json"


def test_segment_with_many_segments(service, mock_s3_client, mock_random_shuffle):
    """Test with large number of segments"""
    # Arrange
    test_id = "large-test"
    total_segments = 100
    
    mock_random_shuffle.side_effect = lambda x: None
    expected_segments = list(range(0, 100))
    
    # Act
    result = service.segment(test_id, total_segments)
    
    # Assert
    expected_body = json.dumps(expected_segments).encode()
    mock_s3_client.put_object.assert_called_once_with(
        Bucket='test-bucket',
        Key="stepfunctionconfig-large-test.json",
        Body=expected_body
    )
    
    assert result['bucket'] == 'test-bucket'
    assert result['key'] == "stepfunctionconfig-large-test.json"


def test_segment_shuffle_is_called(service, mock_s3_client, mock_random_shuffle):
    """Test that random.shuffle is called on the segments"""
    # Arrange
    test_id = "shuffle-test"
    total_segments = 5
    
    # Act
    service.segment(test_id, total_segments)
    
    # Assert - verify shuffle was called with the segments list
    mock_random_shuffle.assert_called_once()
    # Get the argument that was passed to shuffle
    shuffle_arg = mock_random_shuffle.call_args[0][0]
    assert shuffle_arg == [0, 1, 2, 3, 4]


def test_segment_with_special_characters_in_id(service, mock_s3_client, mock_random_shuffle):
    """Test with special characters in execution ID"""
    # Arrange
    test_id = "test-execution_123-abc"
    total_segments = 2
    
    mock_random_shuffle.side_effect = lambda x: None
    
    # Act
    result = service.segment(test_id, total_segments)
    
    # Assert
    expected_key = "stepfunctionconfig-test-execution_123-abc.json"
    assert result['key'] == expected_key
    mock_s3_client.put_object.assert_called_once()


# Error test cases
def test_segment_s3_client_error(service, mock_s3_client, mock_random_shuffle):
    """Test that S3 ClientError is re-raised"""
    # Arrange
    test_id = "error-test"
    total_segments = 3
    
    error = ClientError(
        error_response={'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket does not exist'}},
        operation_name='PutObject'
    )
    mock_s3_client.put_object.side_effect = error
    
    # Act & Assert
    with pytest.raises(ClientError):
        service.segment(test_id, total_segments)


def test_segment_no_credentials_error(service, mock_s3_client, mock_random_shuffle):
    """Test that NoCredentialsError is re-raised"""
    # Arrange
    test_id = "creds-test"
    total_segments = 2
    
    mock_s3_client.put_object.side_effect = NoCredentialsError()
    
    # Act & Assert
    with pytest.raises(NoCredentialsError):
        service.segment(test_id, total_segments)


def test_segment_generic_exception(service, mock_s3_client, mock_random_shuffle):
    """Test that generic exceptions are re-raised"""
    # Arrange
    test_id = "generic-error"
    total_segments = 2
    
    mock_s3_client.put_object.side_effect = Exception("Generic error")
    
    # Act & Assert
    with pytest.raises(Exception, match="Generic error"):
        service.segment(test_id, total_segments)


def test_segment_logging_on_error(service, mock_s3_client, mock_random_shuffle, mocker):
    """Test that errors are properly logged with extras"""
    mock_logger = mocker.patch("services.migration_dynamodb_segment_service.logger")
    
    test_id = "logging-test"
    total_segments = 3
    
    error = ClientError(
        error_response={'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
        operation_name='PutObject'
    )
    mock_s3_client.put_object.side_effect = error
    
    with pytest.raises(ClientError):
        service.segment(test_id, total_segments)
    
    # Verify logging was called with correct extras
    mock_logger.error.assert_called_once()
    call_args = mock_logger.error.call_args
    assert "extra" in call_args.kwargs
    extras = call_args.kwargs["extra"]
    assert extras["executionId"] == "logging-test"
    assert extras["totalSegments"] == 3
    assert extras["bucketName"] == "test-bucket"
    assert extras["errorType"] == "ClientError"
    assert call_args.kwargs.get("exc_info") is True


def test_segment_environment_variable_missing(mocker):
    """Test that missing environment variable raises KeyError"""
    # Don't mock the environment variable
    mock_boto3 = mocker.patch("services.migration_dynamodb_segment_service.boto3.client")
    
    with pytest.raises(KeyError, match="MIGRATION_SEGMENT_BUCKET_NAME"):
        MigrationDynamoDBSegmentService()


def test_segment_with_unicode_id(service, mock_s3_client, mock_random_shuffle):
    """Test with unicode characters in ID"""
    test_id = "test-执行-123"
    total_segments = 2
    
    mock_random_shuffle.side_effect = lambda x: None
    
    result = service.segment(test_id, total_segments)
    
    expected_key = "stepfunctionconfig-test-执行-123.json"
    assert result['key'] == expected_key
    mock_s3_client.put_object.assert_called_once()


def test_segment_body_encoding(service, mock_s3_client, mock_random_shuffle):
    """Test that the body is properly UTF-8 encoded"""
    test_id = "encoding-test"
    total_segments = 2
    
    mock_random_shuffle.side_effect = lambda x: None
    
    service.segment(test_id, total_segments)
    
    call_args = mock_s3_client.put_object.call_args
    body_arg = call_args.kwargs['Body']
    
    # Verify it's bytes and can be decoded as UTF-8
    assert isinstance(body_arg, bytes)
    decoded = body_arg.decode('utf-8')
    parsed = json.loads(decoded)
    assert parsed == [0, 1]


def test_segment_very_large_segments(service, mock_s3_client, mock_random_shuffle):
    """Test with very large number of segments"""
    test_id = "large-segments"
    total_segments = 1000
    
    mock_random_shuffle.side_effect = lambda x: None
    
    result = service.segment(test_id, total_segments)
    
    # Verify the call was made (without checking the entire body)
    mock_s3_client.put_object.assert_called_once()
    call_args = mock_s3_client.put_object.call_args
    
    # Verify the segments list is correct size
    body = call_args.kwargs['Body']
    segments = json.loads(body.decode('utf-8'))
    assert len(segments) == 1000
    assert segments == list(range(1000))


def test_segment_put_object_parameters(service, mock_s3_client, mock_random_shuffle):
    """Test that put_object is called with exactly the right parameters"""
    test_id = "param-test"
    total_segments = 3
    
    mock_random_shuffle.side_effect = lambda x: None
    
    service.segment(test_id, total_segments)
    
    # Verify exact parameters
    call_args = mock_s3_client.put_object.call_args
    assert len(call_args.kwargs) == 3  # Only Bucket, Key, Body
    assert call_args.kwargs['Bucket'] == 'test-bucket'
    assert call_args.kwargs['Key'] == 'stepfunctionconfig-param-test.json'
    assert isinstance(call_args.kwargs['Body'], bytes)


# Test JSON serialization
def test_segment_json_serialization(service, mock_s3_client, mock_random_shuffle):
    """Test that segments are properly JSON serialized"""
    # Arrange
    test_id = "json-test"
    total_segments = 3
    
    # Mock shuffle to reverse the list for predictable testing
    mock_random_shuffle.side_effect = lambda x: x.reverse()
    
    # Act
    service.segment(test_id, total_segments)
    
    # Assert - check the Body parameter is properly encoded JSON
    call_args = mock_s3_client.put_object.call_args
    body_arg = call_args.kwargs['Body']
    
    # Decode and parse the JSON to verify it's valid
    decoded_body = body_arg.decode('utf-8')
    parsed_segments = json.loads(decoded_body)
    
    # Should be [2, 1, 0] after reverse
    assert parsed_segments == [2, 1, 0]


# Test boto3 client creation
def test_segment_creates_s3_client(mock_env_bucket_name, mocker):
    """Test that boto3.client is called to create S3 client"""
    # Arrange
    mock_boto3_client = mocker.patch("services.migration_dynamodb_segment_service.boto3.client")
    mock_s3_client = MagicMock()
    mock_boto3_client.return_value = mock_s3_client
    
    # Create service after mocking
    service = MigrationDynamoDBSegmentService()
    
    test_id = "client-test"
    total_segments = 1
    
    # Act
    service.segment(test_id, total_segments)
    
    # Assert
    mock_boto3_client.assert_called_once_with("s3")


# Edge cases
def test_segment_zero_segments_edge_case(service, mock_s3_client, mock_random_shuffle):
    """Test with zero segments (edge case)"""
    # Note: This might not be a valid business case, but testing the technical behavior
    test_id = "zero-test"
    total_segments = 0
    
    mock_random_shuffle.side_effect = lambda x: None
    
    # Act
    result = service.segment(test_id, total_segments)
    
    # Assert
    expected_segments = []  # range(0, 0) produces empty list
    expected_body = json.dumps(expected_segments).encode()
    
    mock_s3_client.put_object.assert_called_once_with(
        Bucket='test-bucket',
        Key="stepfunctionconfig-zero-test.json",
        Body=expected_body
    )
    
    assert result['bucket'] == 'test-bucket'


def test_segment_empty_id_edge_case(service, mock_s3_client, mock_random_shuffle):
    """Test with empty ID string"""
    test_id = ""
    total_segments = 2
    
    # Act
    result = service.segment(test_id, total_segments)
    
    # Assert
    assert result['key'] == "stepfunctionconfig-.json"


# Integration-style test (without mocking shuffle)
def test_segment_actual_shuffle_behavior(service, mock_s3_client):
    """Test that segments are actually shuffled (without mocking shuffle)"""
    # Arrange
    test_id = "actual-shuffle"
    total_segments = 10
    
    # Act - run multiple times to check randomness
    results = []
    for _ in range(5):
        service.segment(test_id, total_segments)
        # Get the body from the last call
        call_args = mock_s3_client.put_object.call_args
        body = call_args.kwargs['Body']
        segments = json.loads(body.decode('utf-8'))
        results.append(segments)
    
    # Assert - at least one result should be different from sorted order
    # (This is probabilistic, but with 10 elements, it's extremely unlikely all would be sorted)
    sorted_segments = list(range(10))
    assert any(result != sorted_segments for result in results), "Shuffle should produce different orders"