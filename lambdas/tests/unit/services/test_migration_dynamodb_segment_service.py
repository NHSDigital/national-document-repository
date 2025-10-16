import json
import pytest
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
def mock_random(mocker):
    """Mocks random.Random to make tests predictable"""
    mock_random_class = mocker.patch("services.migration_dynamodb_segment_service.random.Random")
    mock_instance = mocker.MagicMock()
    mock_random_class.return_value = mock_instance
    return mock_instance


# Success test cases
def test_segment_success(service, mock_s3_client, mock_random):
    """Test successful segment operation"""
    test_id = "test-execution-123"
    total_segments = 4
    
    # Mock shuffle to do nothing (keep original order for predictable testing)
    mock_random.shuffle.side_effect = lambda x: None
    
    expected_segments = [0, 1, 2, 3]
    expected_key = "stepfunctionconfig-test-execution-123.json"
    expected_body = json.dumps(expected_segments)
    
    result = service.segment(test_id, total_segments)
    
    mock_s3_client.put_object.assert_called_once_with(
        Bucket='test-bucket',
        Key=expected_key,
        Body=expected_body,
        ContentType='application/json'
    )
    
    expected_result = {
        'bucket': 'test-bucket',
        'key': expected_key
    }
    assert result == expected_result


@pytest.mark.parametrize("total_segments,expected_segments", [
    (1, [0]),
    (10, list(range(10))),
    (100, list(range(100)))
])
def test_segment_various_sizes(service, mock_s3_client, mock_random, total_segments, expected_segments):
    """Test with various segment sizes"""
    test_id = "size-test"
    mock_random.shuffle.side_effect = lambda x: None
    
    result = service.segment(test_id, total_segments)
    
    expected_body = json.dumps(expected_segments)
    mock_s3_client.put_object.assert_called_once_with(
        Bucket='test-bucket',
        Key="stepfunctionconfig-size-test.json",
        Body=expected_body,
        ContentType='application/json'
    )
    
    assert result['bucket'] == 'test-bucket'
    assert result['key'] == "stepfunctionconfig-size-test.json"


def test_segment_shuffle_is_called(service, mock_s3_client, mock_random):
    """Test that Random.shuffle is called on the segments"""
    test_id = "shuffle-test"
    total_segments = 5
    
    service.segment(test_id, total_segments)
    
    # Verify shuffle was called with the segments list
    mock_random.shuffle.assert_called_once()
    shuffle_arg = mock_random.shuffle.call_args[0][0]
    assert shuffle_arg == [0, 1, 2, 3, 4]


@pytest.mark.parametrize("test_id,expected_key", [
    ("test-execution_123-abc", "stepfunctionconfig-test-execution_123-abc.json"),
    ("test-执行-123", "stepfunctionconfig-test-执行-123.json"),
    ("", "stepfunctionconfig-.json")
])
def test_segment_special_characters_in_id(service, mock_s3_client, mock_random, test_id, expected_key):
    """Test with various special characters in execution ID"""
    total_segments = 2
    mock_random.shuffle.side_effect = lambda x: None
    
    result = service.segment(test_id, total_segments)
    
    assert result['key'] == expected_key
    mock_s3_client.put_object.assert_called_once()


# Error test cases
@pytest.mark.parametrize("exception,exception_type", [
    (ClientError({'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket does not exist'}}, 'PutObject'), ClientError),
    (NoCredentialsError(), NoCredentialsError),
    (Exception("Generic error"), Exception)
])
def test_segment_error_handling(service, mock_s3_client, mock_random, exception, exception_type):
    """Test that various exceptions are re-raised"""
    test_id = "error-test"
    total_segments = 3
    
    mock_s3_client.put_object.side_effect = exception
    
    with pytest.raises(exception_type):
        service.segment(test_id, total_segments)


def test_segment_logging_on_error(service, mock_s3_client, mock_random, mocker):
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
    """Test that missing environment variable raises ValueError"""
    with pytest.raises(ValueError, match="MIGRATION_SEGMENT_BUCKET_NAME environment variable is required"):
        MigrationDynamoDBSegmentService()


def test_segment_body_encoding_and_json(service, mock_s3_client, mock_random):
    """Test that the body is properly JSON formatted"""
    test_id = "encoding-test"
    total_segments = 3
    
    # Mock shuffle to reverse the list for predictable testing
    mock_random.shuffle.side_effect = lambda x: x.reverse()
    
    service.segment(test_id, total_segments)
    
    call_args = mock_s3_client.put_object.call_args
    body_arg = call_args.kwargs['Body']
    
    # Verify it's a string and valid JSON
    assert isinstance(body_arg, str)
    parsed = json.loads(body_arg)
    assert parsed == [2, 1, 0]  # Should be reversed


def test_segment_put_object_parameters(service, mock_s3_client, mock_random):
    """Test that put_object is called with exactly the right parameters"""
    test_id = "param-test"
    total_segments = 3
    
    mock_random.shuffle.side_effect = lambda x: None
    
    service.segment(test_id, total_segments)
    
    # Verify exact parameters
    call_args = mock_s3_client.put_object.call_args
    assert len(call_args.kwargs) == 4  # Bucket, Key, Body, ContentType
    assert call_args.kwargs['Bucket'] == 'test-bucket'
    assert call_args.kwargs['Key'] == 'stepfunctionconfig-param-test.json'
    assert isinstance(call_args.kwargs['Body'], str)
    assert call_args.kwargs['ContentType'] == 'application/json'


def test_segment_creates_s3_client(mock_env_bucket_name, mocker):
    """Test that boto3.client is called to create S3 client"""
    mock_boto3_client = mocker.patch("services.migration_dynamodb_segment_service.boto3.client")
    
    service = MigrationDynamoDBSegmentService()
    service.segment("client-test", 1)
    
    mock_boto3_client.assert_called_once_with("s3")


def test_segment_zero_segments_edge_case(service, mock_s3_client, mock_random):
    """Test with zero segments (edge case)"""
    test_id = "zero-test"
    total_segments = 0
    
    mock_random.shuffle.side_effect = lambda x: None
    
    result = service.segment(test_id, total_segments)
    
    expected_segments = []  # range(0, 0) produces empty list
    expected_body = json.dumps(expected_segments)
    
    mock_s3_client.put_object.assert_called_once_with(
        Bucket='test-bucket',
        Key="stepfunctionconfig-zero-test.json",
        Body=expected_body,
        ContentType='application/json'
    )
    
    assert result['bucket'] == 'test-bucket'


def test_segment_actual_shuffle_behavior(service, mock_s3_client):
    """Test that segments are actually shuffled (without mocking Random)"""
    test_id = "actual-shuffle"
    total_segments = 10
    
    # Run multiple times to check randomness
    results = []
    for _ in range(5):
        service.segment(test_id, total_segments)
        call_args = mock_s3_client.put_object.call_args
        body = call_args.kwargs['Body']
        segments = json.loads(body)  # Body is already a string
        results.append(segments)
    
    # At least one result should be different from sorted order
    sorted_segments = list(range(10))
    assert any(result != sorted_segments for result in results), "Shuffle should produce different orders"