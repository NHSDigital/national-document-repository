import json
import pytest
from unittest.mock import patch, MagicMock
from services.migration_dynamodb_segment_service import MigrationDynamoDBSegmentService
from botocore.exceptions import ClientError, NoCredentialsError


@pytest.fixture
def service():
    """Creates an instance of the service for testing"""
    return MigrationDynamoDBSegmentService()


@pytest.fixture
def mock_s3_client(mocker):
    """Mocks the boto3 S3 client"""
    mock_client = mocker.patch("services.migration_dynamodb_segment_service.boto3.client")
    return mock_client.return_value


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
    bucket_name = "test-bucket"
    
    # Mock shuffle to do nothing (keep original order for predictable testing)
    mock_random_shuffle.side_effect = lambda x: None
    
    expected_segments = [0, 1, 2, 3]
    expected_key = "stepfunctionconfig-test-execution-123.json"
    expected_body = json.dumps(expected_segments).encode()
    
    # Act
    result = service.segment(test_id, total_segments, bucket_name)
    
    # Assert
    mock_s3_client.put_object.assert_called_once_with(
        Bucket=bucket_name,
        Key=expected_key,
        Body=expected_body
    )
    
    expected_result = {
        'bucket': bucket_name,
        'key': expected_key
    }
    assert result == expected_result


def test_segment_with_single_segment(service, mock_s3_client, mock_random_shuffle):
    """Test with single segment"""
    # Arrange
    test_id = "single-segment"
    total_segments = 1
    bucket_name = "single-bucket"
    
    mock_random_shuffle.side_effect = lambda x: None
    expected_segments = [0]
    
    # Act
    result = service.segment(test_id, total_segments, bucket_name)
    
    # Assert
    expected_body = json.dumps(expected_segments).encode()
    mock_s3_client.put_object.assert_called_once_with(
        Bucket=bucket_name,
        Key="stepfunctionconfig-single-segment.json",
        Body=expected_body
    )
    
    assert result['bucket'] == bucket_name
    assert result['key'] == "stepfunctionconfig-single-segment.json"


def test_segment_with_many_segments(service, mock_s3_client, mock_random_shuffle):
    """Test with large number of segments"""
    # Arrange
    test_id = "large-test"
    total_segments = 100
    bucket_name = "large-bucket"
    
    mock_random_shuffle.side_effect = lambda x: None
    expected_segments = list(range(0, 100))
    
    # Act
    result = service.segment(test_id, total_segments, bucket_name)
    
    # Assert
    expected_body = json.dumps(expected_segments).encode()
    mock_s3_client.put_object.assert_called_once_with(
        Bucket=bucket_name,
        Key="stepfunctionconfig-large-test.json",
        Body=expected_body
    )
    
    assert result['bucket'] == bucket_name
    assert result['key'] == "stepfunctionconfig-large-test.json"


def test_segment_shuffle_is_called(service, mock_s3_client, mock_random_shuffle):
    """Test that random.shuffle is called on the segments"""
    # Arrange
    test_id = "shuffle-test"
    total_segments = 5
    bucket_name = "shuffle-bucket"
    
    # Act
    service.segment(test_id, total_segments, bucket_name)
    
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
    bucket_name = "special-bucket"
    
    mock_random_shuffle.side_effect = lambda x: None
    
    # Act
    result = service.segment(test_id, total_segments, bucket_name)
    
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
    bucket_name = "error-bucket"
    
    error = ClientError(
        error_response={'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket does not exist'}},
        operation_name='PutObject'
    )
    mock_s3_client.put_object.side_effect = error
    
    # Act & Assert
    with pytest.raises(ClientError):
        service.segment(test_id, total_segments, bucket_name)


def test_segment_no_credentials_error(service, mock_s3_client, mock_random_shuffle):
    """Test that NoCredentialsError is re-raised"""
    # Arrange
    test_id = "creds-test"
    total_segments = 2
    bucket_name = "creds-bucket"
    
    mock_s3_client.put_object.side_effect = NoCredentialsError()
    
    # Act & Assert
    with pytest.raises(NoCredentialsError):
        service.segment(test_id, total_segments, bucket_name)


def test_segment_generic_exception(service, mock_s3_client, mock_random_shuffle):
    """Test that generic exceptions are re-raised"""
    # Arrange
    test_id = "generic-error"
    total_segments = 2
    bucket_name = "generic-bucket"
    
    mock_s3_client.put_object.side_effect = Exception("Generic error")
    
    # Act & Assert
    with pytest.raises(Exception, match="Generic error"):
        service.segment(test_id, total_segments, bucket_name)


# Test JSON serialization
def test_segment_json_serialization(service, mock_s3_client, mock_random_shuffle):
    """Test that segments are properly JSON serialized"""
    # Arrange
    test_id = "json-test"
    total_segments = 3
    bucket_name = "json-bucket"
    
    # Mock shuffle to reverse the list for predictable testing
    mock_random_shuffle.side_effect = lambda x: x.reverse()
    
    # Act
    service.segment(test_id, total_segments, bucket_name)
    
    # Assert - check the Body parameter is properly encoded JSON
    call_args = mock_s3_client.put_object.call_args
    body_arg = call_args.kwargs['Body']
    
    # Decode and parse the JSON to verify it's valid
    decoded_body = body_arg.decode('utf-8')
    parsed_segments = json.loads(decoded_body)
    
    # Should be [2, 1, 0] after reverse
    assert parsed_segments == [2, 1, 0]


# Test boto3 client creation
def test_segment_creates_s3_client(service, mocker):
    """Test that boto3.client is called to create S3 client"""
    # Arrange
    mock_boto3_client = mocker.patch("services.migration_dynamodb_segment_service.boto3.client")
    mock_s3_client = MagicMock()
    mock_boto3_client.return_value = mock_s3_client
    
    test_id = "client-test"
    total_segments = 1
    bucket_name = "client-bucket"
    
    # Act
    service.segment(test_id, total_segments, bucket_name)
    
    # Assert
    mock_boto3_client.assert_called_once_with("s3")


# Edge cases
def test_segment_zero_segments_edge_case(service, mock_s3_client, mock_random_shuffle):
    """Test with zero segments (edge case)"""
    # Note: This might not be a valid business case, but testing the technical behavior
    test_id = "zero-test"
    total_segments = 0
    bucket_name = "zero-bucket"
    
    mock_random_shuffle.side_effect = lambda x: None
    
    # Act
    result = service.segment(test_id, total_segments, bucket_name)
    
    # Assert
    expected_segments = []  # range(0, 0) produces empty list
    expected_body = json.dumps(expected_segments).encode()
    
    mock_s3_client.put_object.assert_called_once_with(
        Bucket=bucket_name,
        Key="stepfunctionconfig-zero-test.json",
        Body=expected_body
    )
    
    assert result['bucket'] == bucket_name


def test_segment_empty_id_edge_case(service, mock_s3_client, mock_random_shuffle):
    """Test with empty ID string"""
    test_id = ""
    total_segments = 2
    bucket_name = "empty-id-bucket"
    
    # Act
    result = service.segment(test_id, total_segments, bucket_name)
    
    # Assert
    assert result['key'] == "stepfunctionconfig-.json"


# Integration-style test (without mocking shuffle)
def test_segment_actual_shuffle_behavior(service, mock_s3_client):
    """Test that segments are actually shuffled (without mocking shuffle)"""
    # Arrange
    test_id = "actual-shuffle"
    total_segments = 10
    bucket_name = "shuffle-bucket"
    
    # Act - run multiple times to check randomness
    results = []
    for _ in range(5):
        service.segment(test_id, total_segments, bucket_name)
        # Get the body from the last call
        call_args = mock_s3_client.put_object.call_args
        body = call_args.kwargs['Body']
        segments = json.loads(body.decode('utf-8'))
        results.append(segments)
    
    # Assert - at least one result should be different from sorted order
    # (This is probabilistic, but with 10 elements, it's extremely unlikely all would be sorted)
    sorted_segments = list(range(10))
    assert any(result != sorted_segments for result in results), "Shuffle should produce different orders"