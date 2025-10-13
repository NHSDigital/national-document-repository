import pytest
from unittest.mock import patch, MagicMock
from handlers.migration_dynamodb_segment_handler import lambda_handler


# Test fixtures - these are reusable test data/mocks
@pytest.fixture
def valid_event():
    """Creates a valid event for testing successful scenarios"""
    return {
        "executionId": "arn:aws:states:us-east-1:123456789012:execution:MyStateMachine:execution-12345",
        "TotalSegments": 4,
        "BucketName": "test-bucket"
    }


@pytest.fixture
def context():
    """Mock Lambda context object"""
    mock_context = MagicMock()
    mock_context.function_name = "test-function"
    mock_context.aws_request_id = "test-request-id"
    return mock_context


@pytest.fixture
def mock_migration_service(mocker):
    """Mocks the MigrationDynamoDBSegmentService class"""
    mocked_class = mocker.patch("handlers.migration_dynamodb_segment_handler.MigrationDynamoDBSegmentService")
    mocked_instance = mocked_class.return_value
    yield mocked_instance


# Success test cases
def test_lambda_handler_success(valid_event, context, mock_migration_service):
    """Test that lambda_handler works correctly with valid input"""
    expected_result = {"status": "success", "segments": 4}
    mock_migration_service.segment.return_value = expected_result
    
    result = lambda_handler(valid_event, context)
    
    # Verify the service was called with correct parameters
    mock_migration_service.segment.assert_called_once_with("execution-12345", 4, "test-bucket")
    assert result == expected_result


# Error test cases - missing executionId
def test_lambda_handler_missing_execution_id(context, mock_migration_service):
    """Test that missing executionId raises ValueError"""
    event = {
        "TotalSegments": 4,
        "BucketName": "test-bucket"
    }
    
    with pytest.raises(ValueError, match="Invalid or missing 'executionId' in event"):
        lambda_handler(event, context)


def test_lambda_handler_invalid_execution_id_type(context, mock_migration_service):
    """Test that non-string executionId raises ValueError"""
    event = {
        "executionId": 12345,  # Should be string
        "TotalSegments": 4,
        "BucketName": "test-bucket"
    }
    
    with pytest.raises(ValueError, match="Invalid or missing 'executionId' in event"):
        lambda_handler(event, context)


def test_lambda_handler_empty_execution_id(context, mock_migration_service):
    """Test that empty executionId raises ValueError"""
    event = {
        "executionId": "",
        "TotalSegments": 4,
        "BucketName": "test-bucket"
    }
    
    with pytest.raises(ValueError, match="Invalid or missing 'executionId' in event"):
        lambda_handler(event, context)


# Error test cases - missing TotalSegments
def test_lambda_handler_missing_total_segments(context, mock_migration_service):
    """Test that missing TotalSegments raises ValueError"""
    event = {
        "executionId": "test-execution-id",
        "BucketName": "test-bucket"
    }
    
    with pytest.raises(ValueError, match="Missing 'TotalSegments' in event"):
        lambda_handler(event, context)


def test_lambda_handler_invalid_total_segments_type(context, mock_migration_service):
    """Test that non-numeric TotalSegments raises ValueError"""
    event = {
        "executionId": "test-execution-id",
        "TotalSegments": "invalid",
        "BucketName": "test-bucket"
    }
    
    with pytest.raises(ValueError, match="Invalid 'TotalSegments' in event"):
        lambda_handler(event, context)


def test_lambda_handler_zero_total_segments(context, mock_migration_service):
    """Test that zero TotalSegments raises ValueError"""
    event = {
        "executionId": "test-execution-id",
        "TotalSegments": 0,
        "BucketName": "test-bucket"
    }
    
    with pytest.raises(ValueError, match="Invalid 'TotalSegments' in event"):
        lambda_handler(event, context)


def test_lambda_handler_negative_total_segments(context, mock_migration_service):
    """Test that negative TotalSegments raises ValueError"""
    event = {
        "executionId": "test-execution-id",
        "TotalSegments": -1,
        "BucketName": "test-bucket"
    }
    
    with pytest.raises(ValueError, match="Invalid 'TotalSegments' in event"):
        lambda_handler(event, context)


# Error test cases - BucketName validation
def test_lambda_handler_missing_bucket_name(context, mock_migration_service):
    """Test that missing BucketName raises ValueError"""
    event = {
        "executionId": "test-execution-id",
        "TotalSegments": 4
    }
    
    with pytest.raises(ValueError, match="Invalid 'BucketName' in event"):
        lambda_handler(event, context)


def test_lambda_handler_invalid_bucket_name_type(context, mock_migration_service):
    """Test that non-string BucketName raises ValueError"""
    event = {
        "executionId": "test-execution-id",
        "TotalSegments": 4,
        "BucketName": 123
    }
    
    with pytest.raises(ValueError, match="Invalid 'BucketName' in event"):
        lambda_handler(event, context)


def test_lambda_handler_empty_bucket_name(context, mock_migration_service):
    """Test that empty BucketName raises ValueError"""
    event = {
        "executionId": "test-execution-id",
        "TotalSegments": 4,
        "BucketName": ""
    }
    
    with pytest.raises(ValueError, match="Invalid 'BucketName' in event"):
        lambda_handler(event, context)


# Test executionId parsing
def test_lambda_handler_execution_id_parsing(context, mock_migration_service):
    """Test that executionId is correctly parsed (takes last part after colon)"""
    event = {
        "executionId": "arn:aws:states:region:account:execution:machine:my-execution-name",
        "TotalSegments": 2,
        "BucketName": "test-bucket"
    }
    
    expected_result = {"status": "processed"}
    mock_migration_service.segment.return_value = expected_result
    
    lambda_handler(event, context)
    
    # Verify the ID was correctly extracted
    mock_migration_service.segment.assert_called_once_with("my-execution-name", 2, "test-bucket")


# Test service exception handling
def test_lambda_handler_service_exception(valid_event, context, mock_migration_service):
    """Test that exceptions from the service are re-raised"""
    mock_migration_service.segment.side_effect = Exception("Service error")
    
    with pytest.raises(Exception, match="Service error"):
        lambda_handler(valid_event, context)


# Edge cases
def test_lambda_handler_execution_id_no_colon(context, mock_migration_service):
    """Test executionId without colon separator"""
    event = {
        "executionId": "simple-execution-id",
        "TotalSegments": 1,
        "BucketName": "test-bucket"
    }
    
    expected_result = {"processed": True}
    mock_migration_service.segment.return_value = expected_result
    
    result = lambda_handler(event, context)
    
    # Should use the entire string as ID
    mock_migration_service.segment.assert_called_once_with("simple-execution-id", 1, "test-bucket")
    assert result == expected_result


def test_lambda_handler_large_total_segments(context, mock_migration_service):
    """Test with large TotalSegments value"""
    event = {
        "executionId": "test-execution-id",
        "TotalSegments": 1000,
        "BucketName": "test-bucket"
    }
    
    expected_result = {"segments": 1000}
    mock_migration_service.segment.return_value = expected_result
    
    result = lambda_handler(event, context)
    
    mock_migration_service.segment.assert_called_once_with("test-execution-id", 1000, "test-bucket")
    assert result == expected_result