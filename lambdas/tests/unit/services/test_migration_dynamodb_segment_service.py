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
def mock_secrets_randbelow(mocker):
    """Mocks secrets.randbelow to make tests predictable"""
    return mocker.patch("services.migration_dynamodb_segment_service.secrets.randbelow")


# Success test cases
def test_segment_success(service, mock_s3_client, mock_secrets_randbelow):
    """Test successful segment operation"""
    test_id = "test-execution-123"
    total_segments = 4
    
    # Mock randbelow to return predictable values (always 0)
    # Fisher-Yates with j=0: rotates array left, moving first element to end
    mock_secrets_randbelow.side_effect = lambda x: 0
    
    expected_segments = [1, 2, 3, 0]  # Rotation when always swapping with index 0
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
    (10, list(range(1, 10)) + [0]),  # Rotation: [1,2,3,4,5,6,7,8,9,0]
    (100, list(range(1, 100)) + [0])  # Rotation: [1,2,...,99,0]
])
def test_segment_various_sizes(service, mock_s3_client, mock_secrets_randbelow, total_segments, expected_segments):
    """Test with various segment sizes"""
    test_id = "size-test"
    mock_secrets_randbelow.side_effect = lambda x: 0
    
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


def test_segment_shuffle_is_called(service, mock_s3_client, mock_secrets_randbelow):
    """Test that secure_shuffle is called via secrets.randbelow"""
    test_id = "shuffle-test"
    total_segments = 5
    
    mock_secrets_randbelow.side_effect = lambda x: 0
    
    service.segment(test_id, total_segments)
    
    # Verify randbelow was called during shuffle (once per element except the last)
    assert mock_secrets_randbelow.call_count == total_segments - 1


@pytest.mark.parametrize("test_id,expected_key", [
    ("test-execution_123-abc", "stepfunctionconfig-test-execution_123-abc.json"),
    ("test-执行-123", "stepfunctionconfig-test-执行-123.json"),
    ("", "stepfunctionconfig-.json")
])
def test_segment_special_characters_in_id(service, mock_s3_client, mock_secrets_randbelow, test_id, expected_key):
    """Test with various special characters in execution ID"""
    total_segments = 2
    mock_secrets_randbelow.side_effect = lambda x: 0
    
    result = service.segment(test_id, total_segments)
    
    assert result['key'] == expected_key
    mock_s3_client.put_object.assert_called_once()


# Error test cases
@pytest.mark.parametrize("exception,exception_type", [
    (ClientError({'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket does not exist'}}, 'PutObject'), ClientError),
    (NoCredentialsError(), NoCredentialsError),
    (Exception("Generic error"), Exception)
])
def test_segment_error_handling(service, mock_s3_client, mock_secrets_randbelow, exception, exception_type):
    """Test that various exceptions are re-raised"""
    test_id = "error-test"
    total_segments = 3
    
    mock_s3_client.put_object.side_effect = exception
    
    with pytest.raises(exception_type):
        service.segment(test_id, total_segments)


def test_segment_logging_on_error(service, mock_s3_client, mock_secrets_randbelow, mocker):
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


def test_segment_body_encoding_and_json(service, mock_s3_client, mock_secrets_randbelow):
    """Test that the body is properly JSON formatted"""
    test_id = "encoding-test"
    total_segments = 3
    
    # Mock randbelow to always return 0
    # Start [0,1,2]
    # i=2: j=0, swap seq[2] with seq[0] -> [2,1,0]
    # i=1: j=0, swap seq[1] with seq[0] -> [1,2,0]
    mock_secrets_randbelow.side_effect = lambda x: 0
    
    service.segment(test_id, total_segments)
    
    call_args = mock_s3_client.put_object.call_args
    body_arg = call_args.kwargs['Body']
    
    # Verify it's a string and valid JSON
    assert isinstance(body_arg, str)
    parsed = json.loads(body_arg)
    assert parsed == [1, 2, 0]  # Result when always swapping with index 0


def test_segment_put_object_parameters(service, mock_s3_client, mock_secrets_randbelow):
    """Test that put_object is called with exactly the right parameters"""
    test_id = "param-test"
    total_segments = 3
    
    mock_secrets_randbelow.side_effect = lambda x: 0
    
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


def test_segment_zero_segments_edge_case(service, mock_s3_client, mock_secrets_randbelow):
    """Test with zero segments (edge case)"""
    test_id = "zero-test"
    total_segments = 0
    
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
    # secrets.randbelow should not be called for empty list
    mock_secrets_randbelow.assert_not_called()


def test_segment_actual_shuffle_behavior(service, mock_s3_client):
    """Test that segments are actually shuffled (without mocking secrets)"""
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


def test_secure_shuffle_method(service):
    """Test the _secure_shuffle method directly"""
    input_list = [0, 1, 2, 3, 4]
    result = service._secure_shuffle(input_list)
    
    # Should return a list
    assert isinstance(result, list)
    # Should contain same elements
    assert sorted(result) == sorted(input_list)
    # Should be same length
    assert len(result) == len(input_list)


def test_secure_shuffle_does_not_modify_original(service):
    """Test that _secure_shuffle doesn't modify the original list"""
    original = [0, 1, 2, 3, 4]
    original_copy = original.copy()
    
    service._secure_shuffle(original)
    
    # Original should be unchanged
    assert original == original_copy