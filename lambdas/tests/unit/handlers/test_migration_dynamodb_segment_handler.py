import pytest
from unittest.mock import patch, MagicMock
from handlers.migration_dynamodb_segment_handler import lambda_handler


# Test fixtures - these are reusable test data/mocks
@pytest.fixture
def valid_event():
    """Creates a valid event for testing successful scenarios"""
    return {
        "executionId": "arn:aws:states:us-east-1:123456789012:execution:MyStateMachine:execution-12345",
        "totalSegments": 4
    }


@pytest.fixture
def mock_migration_service(mocker):
    """Mocks the MigrationDynamoDBSegmentService class"""
    mocked_class = mocker.patch("handlers.migration_dynamodb_segment_handler.MigrationDynamoDBSegmentService")
    mocked_instance = mocked_class.return_value
    yield mocked_instance


# Success test cases
def test_lambda_handler_success(valid_event, mock_migration_service):
    """Test that lambda_handler works correctly with valid input"""
    expected_result = {"status": "success", "segments": 4}
    mock_migration_service.segment.return_value = expected_result
    
    result = lambda_handler(valid_event)
    
    # Verify the service was called with correct parameters
    mock_migration_service.segment.assert_called_once_with("execution-12345", 4)
    assert result == expected_result


# Error test cases - missing executionId
def test_lambda_handler_missing_execution_id(mock_migration_service):
    """Test that missing executionId raises ValueError"""
    event = {
        "totalSegments": 4
    }
    
    with pytest.raises(ValueError, match="Invalid or missing 'executionId' in event"):
        lambda_handler(event)


def test_lambda_handler_invalid_execution_id_type(mock_migration_service):
    """Test that non-string executionId raises ValueError"""
    event = {
        "executionId": 12345,  # Should be string
        "totalSegments": 4
    }
    
    with pytest.raises(ValueError, match="Invalid or missing 'executionId' in event"):
        lambda_handler(event)


def test_lambda_handler_empty_execution_id(mock_migration_service):
    """Test that empty executionId raises ValueError"""
    event = {
        "executionId": "",
        "totalSegments": 4
    }
    
    with pytest.raises(ValueError, match="Invalid or missing 'executionId' in event"):
        lambda_handler(event)


# Error test cases - missing totalSegments
def test_lambda_handler_missing_total_segments(mock_migration_service):
    """Test that missing totalSegments raises ValueError"""
    event = {
        "executionId": "test-execution-id"
    }

    with pytest.raises(ValueError, match="Missing 'totalSegments' in event"):
        lambda_handler(event)


def test_lambda_handler_invalid_total_segments_type(mock_migration_service):
    """Test that non-numeric totalSegments raises ValueError"""
    event = {
        "executionId": "test-execution-id",
        "totalSegments": "invalid"
    }

    with pytest.raises(ValueError, match="Invalid 'totalSegments' in event"):
        lambda_handler(event)


def test_lambda_handler_zero_total_segments(mock_migration_service):
    """Test that zero totalSegments raises ValueError"""
    event = {
        "executionId": "test-execution-id",
        "totalSegments": 0
    }

    with pytest.raises(ValueError, match="Invalid 'totalSegments' in event"):
        lambda_handler(event)


def test_lambda_handler_negative_total_segments(mock_migration_service):
    """Test that negative totalSegments raises ValueError"""
    event = {
        "executionId": "test-execution-id",
        "totalSegments": -1
    }

    with pytest.raises(ValueError, match="Invalid 'totalSegments' in event"):
        lambda_handler(event)


def test_lambda_handler_max_total_segments_exceeded(mock_migration_service):
    """Test that totalSegments exceeding 1000 raises ValueError"""
    event = {
        "executionId": "test-execution-id",
        "totalSegments": 1001
    }

    with pytest.raises(ValueError, match="Invalid 'totalSegments' in event"):
        lambda_handler(event)


def test_lambda_handler_whitespace_execution_id(mock_migration_service):
    """Test that whitespace-only executionId raises ValueError"""
    event = {
        "executionId": "   ",
        "totalSegments": 4
    }
    
    with pytest.raises(ValueError, match="Invalid or missing 'executionId' in event"):
        lambda_handler(event)


def test_lambda_handler_float_total_segments(mock_migration_service):
    """Test that float totalSegments is converted to int"""
    event = {
        "executionId": "test-execution-id",
        "totalSegments": 4.0
    }
    
    expected_result = {"segments": 4}
    mock_migration_service.segment.return_value = expected_result
    
    result = lambda_handler(event)
    
    mock_migration_service.segment.assert_called_once_with("test-execution-id", 4)
    assert result == expected_result


def test_lambda_handler_none_values(mock_migration_service):
    """Test that None values raise appropriate errors"""
    event = {
        "executionId": None,
        "totalSegments": None
    }
    
    with pytest.raises(ValueError, match="Invalid or missing 'executionId' in event"):
        lambda_handler(event)


def test_lambda_handler_logging_on_validation_error(mock_migration_service, mocker):
    """Test that validation errors are properly logged"""
    mock_logger = mocker.patch("handlers.migration_dynamodb_segment_handler.logger")
    
    event = {
        "executionId": "",
        "totalSegments": 4
    }
    
    with pytest.raises(ValueError):
        lambda_handler(event)
    
    # Verify logging was called with correct extras
    mock_logger.error.assert_called_once()
    call_args = mock_logger.error.call_args
    assert "extra" in call_args.kwargs
    extras = call_args.kwargs["extra"]
    assert extras["executionId"] == ""
    assert extras["totalSegments"] == 4
    assert extras["errorType"] == "ValueError"
    assert call_args.kwargs.get("exc_info") is True


def test_lambda_handler_logging_on_service_error(valid_event, mock_migration_service, mocker):
    """Test that service errors are properly logged"""
    mock_logger = mocker.patch("handlers.migration_dynamodb_segment_handler.logger")
    mock_migration_service.segment.side_effect = RuntimeError("S3 connection failed")
    
    with pytest.raises(RuntimeError):
        lambda_handler(valid_event)
    
    # Verify logging was called with correct extras
    mock_logger.error.assert_called_once()
    call_args = mock_logger.error.call_args
    extras = call_args.kwargs["extra"]
    assert extras["executionId"] == "execution-12345"
    assert extras["totalSegments"] == 4
    assert extras["errorType"] == "RuntimeError"