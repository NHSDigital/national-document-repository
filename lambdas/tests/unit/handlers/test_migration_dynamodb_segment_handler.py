import pytest
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
    expected_result = {'bucket': 'migration-bucket', 'key': 'stepfunctionconfig-execution-12345.json'}
    mock_migration_service.segment.return_value = expected_result
    
    result = lambda_handler(valid_event)
    
    # Verify the service was called with correct parameters
    mock_migration_service.segment.assert_called_once_with("execution-12345", 4)
    assert result == expected_result


# Error test cases - executionId validation
@pytest.mark.parametrize("execution_id,description", [
    (None, "None executionId"),
    ("", "empty executionId"),
    ("   ", "whitespace-only executionId"),
    (12345, "non-string executionId")
])
def test_lambda_handler_invalid_execution_id(execution_id, description):
    """Test that invalid executionId values raise ValueError"""
    event = {
        "executionId": execution_id,
        "totalSegments": 4
    }
    
    with pytest.raises(ValueError, match="Invalid or missing 'executionId' in event"):
        lambda_handler(event)


def test_lambda_handler_missing_execution_id():
    """Test that missing executionId raises ValueError"""
    event = {
        "totalSegments": 4
    }
    
    with pytest.raises(ValueError, match="Invalid or missing 'executionId' in event"):
        lambda_handler(event)


# Error test cases - totalSegments validation
@pytest.mark.parametrize("total_segments,expected_error", [
    (None, "Invalid 'totalSegments' in event - must be a valid integer"),
    ("invalid", "Invalid 'totalSegments' in event - must be a valid integer"),
    (0, "'totalSegments' must be positive"),
    (-1, "'totalSegments' must be positive"),
    (1001, "'totalSegments' exceeds maximum allowed value of 1000")
])
def test_lambda_handler_invalid_total_segments(total_segments, expected_error):
    """Test that invalid totalSegments values raise appropriate ValueError"""
    event = {
        "executionId": "test-execution-id",
        "totalSegments": total_segments
    }

    with pytest.raises(ValueError, match=expected_error):
        lambda_handler(event)


def test_lambda_handler_missing_total_segments():
    """Test that missing totalSegments raises ValueError"""
    event = {
        "executionId": "test-execution-id"
    }

    with pytest.raises(ValueError, match="Invalid 'totalSegments' in event - must be a valid integer"):
        lambda_handler(event)


# Type conversion tests
@pytest.mark.parametrize("total_segments,expected_int", [
    (4.0, 4),
    ("42", 42),
    (1000, 1000)
])
def test_lambda_handler_total_segments_conversion(total_segments, expected_int, mock_migration_service):
    """Test that totalSegments is properly converted to int"""
    event = {
        "executionId": "test-execution-id",
        "totalSegments": total_segments
    }
    
    expected_result = {'bucket': 'migration-bucket', 'key': 'stepfunctionconfig-test-execution-id.json'}
    mock_migration_service.segment.return_value = expected_result
    
    result = lambda_handler(event)
    
    mock_migration_service.segment.assert_called_once_with("test-execution-id", expected_int)
    assert result == expected_result


# Logging tests
def test_lambda_handler_logging_on_validation_error(mocker):
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


# ExecutionId parsing tests
@pytest.mark.parametrize("execution_id,expected_parsed", [
    ("arn:aws:states:region:account:execution:machine:my-execution-name", "my-execution-name"),
    ("simple-execution-id", "simple-execution-id"),
    ("part1:part2:part3:final-execution-id", "final-execution-id")
])
def test_lambda_handler_execution_id_parsing(execution_id, expected_parsed, mock_migration_service):
    """Test that executionId is correctly parsed (takes last part after colon)"""
    event = {
        "executionId": execution_id,
        "totalSegments": 2
    }
    
    expected_result = {'bucket': 'migration-bucket', 'key': f'stepfunctionconfig-{expected_parsed}.json'}
    mock_migration_service.segment.return_value = expected_result
    
    result = lambda_handler(event)
    
    # Verify the ID was correctly extracted
    mock_migration_service.segment.assert_called_once_with(expected_parsed, 2)
    assert result == expected_result


# Service exception handling
def test_lambda_handler_service_exception(valid_event, mock_migration_service):
    """Test that exceptions from the service are re-raised"""
    mock_migration_service.segment.side_effect = Exception("Service error")
    
    with pytest.raises(Exception, match="Service error"):
        lambda_handler(valid_event)


# Boundary testing
def test_lambda_handler_boundary_values(mock_migration_service):
    """Test with boundary values for totalSegments"""
    event = {
        "executionId": "test-execution-id",
        "totalSegments": 1  # minimum valid value
    }
    
    expected_result = {'bucket': 'migration-bucket', 'key': 'stepfunctionconfig-test-execution-id.json'}
    mock_migration_service.segment.return_value = expected_result
    
    result = lambda_handler(event)
    
    mock_migration_service.segment.assert_called_once_with("test-execution-id", 1)
    assert result == expected_result


def test_lambda_handler_maximum_boundary_value(mock_migration_service):
    """Test with maximum allowed totalSegments value"""
    event = {
        "executionId": "test-execution-id",
        "totalSegments": 1000  # maximum valid value
    }
    
    expected_result = {'bucket': 'migration-bucket', 'key': 'stepfunctionconfig-test-execution-id.json'}
    mock_migration_service.segment.return_value = expected_result
    
    result = lambda_handler(event)
    
    mock_migration_service.segment.assert_called_once_with("test-execution-id", 1000)
    assert result == expected_result