import pytest
from handlers.migration_dynamodb_segment_handler import lambda_handler, validate_execution_id, validate_total_segments


# Test fixtures - these are reusable test data/mocks
@pytest.fixture
def valid_event():
    """Creates a valid event for testing successful scenarios"""
    return {
        "executionId": "arn:aws:states:us-east-1:123456789012:execution:MyStateMachine:execution-12345",
        "totalSegments": 4
    }

#test comment 


@pytest.fixture
def mock_migration_service(mocker):
    """Mocks the MigrationDynamoDBSegmentService class"""
    mocked_class = mocker.patch("handlers.migration_dynamodb_segment_handler.MigrationDynamoDBSegmentService")
    mocked_instance = mocked_class.return_value
    yield mocked_instance
 

# Tests for validate_execution_id function
class TestValidateExecutionId:
    """Test cases for the validate_execution_id function"""
    
    def test_validate_execution_id_success_with_arn(self):
        """Test that ARN format execution ID is correctly parsed"""
        event = {"executionId": "arn:aws:states:region:account:execution:machine:my-execution-name"}
        result = validate_execution_id(event)
        assert result == "my-execution-name"
    
    def test_validate_execution_id_success_simple_id(self):
        """Test that simple execution ID is returned as-is"""
        event = {"executionId": "simple-execution-id"}
        result = validate_execution_id(event)
        assert result == "simple-execution-id"
    
    def test_validate_execution_id_success_colon_separated(self):
        """Test that colon-separated ID returns last part"""
        event = {"executionId": "part1:part2:part3:final-execution-id"}
        result = validate_execution_id(event)
        assert result == "final-execution-id"
    
    @pytest.mark.parametrize("execution_id", [None, "", "   ", 12345])
    def test_validate_execution_id_invalid_values(self, execution_id):
        """Test that invalid executionId values raise ValueError"""
        event = {"executionId": execution_id}
        with pytest.raises(ValueError, match="Invalid or missing 'executionId' in event"):
            validate_execution_id(event)
    
    def test_validate_execution_id_missing_key(self):
        """Test that missing executionId key raises ValueError"""
        event = {}
        with pytest.raises(ValueError, match="Invalid or missing 'executionId' in event"):
            validate_execution_id(event)


# Tests for validate_total_segments function
class TestValidateTotalSegments:
    """Test cases for the validate_total_segments function"""
    
    @pytest.mark.parametrize("total_segments,expected", [
        (4, 4),
        (1, 1),
        (1000, 1000),
        (4.0, 4),
        ("42", 42)
    ])
    def test_validate_total_segments_success(self, total_segments, expected):
        """Test that valid totalSegments values are correctly converted"""
        event = {"totalSegments": total_segments}
        result = validate_total_segments(event)
        assert result == expected
    
    @pytest.mark.parametrize("total_segments", [None, "invalid", "4.5", []])
    def test_validate_total_segments_invalid_type(self, total_segments):
        """Test that invalid totalSegments types raise ValueError"""
        event = {"totalSegments": total_segments}
        with pytest.raises(ValueError, match="Invalid 'totalSegments' in event - must be a valid integer"):
            validate_total_segments(event)
    
    @pytest.mark.parametrize("total_segments", [0, -1, -10])
    def test_validate_total_segments_non_positive(self, total_segments):
        """Test that non-positive totalSegments raise ValueError"""
        event = {"totalSegments": total_segments}
        with pytest.raises(ValueError, match="'totalSegments' must be positive"):
            validate_total_segments(event)
    
    def test_validate_total_segments_exceeds_maximum(self):
        """Test that totalSegments > 1000 raises ValueError"""
        event = {"totalSegments": 1001}
        with pytest.raises(ValueError, match="'totalSegments' exceeds maximum allowed value of 1000"):
            validate_total_segments(event)
    
    def test_validate_total_segments_missing_key(self):
        """Test that missing totalSegments key raises ValueError"""
        event = {}
        with pytest.raises(ValueError, match="Invalid 'totalSegments' in event - must be a valid integer"):
            validate_total_segments(event)


# Tests for lambda_handler function
class TestLambdaHandler:
    """Test cases for the lambda_handler function"""
    
    def test_lambda_handler_success(self, valid_event, mock_migration_service):
        """Test that lambda_handler works correctly with valid input"""
        expected_result = {'bucket': 'migration-bucket', 'key': 'stepfunctionconfig-execution-12345.json'}
        mock_migration_service.segment.return_value = expected_result
        
        result = lambda_handler(valid_event, None)
        
        mock_migration_service.segment.assert_called_once_with("execution-12345", 4)
        assert result == expected_result
    
    def test_lambda_handler_validation_error_execution_id(self, mock_migration_service):
        """Test that validation errors for executionId are properly handled"""
        event = {"executionId": "", "totalSegments": 4}
        
        with pytest.raises(ValueError, match="Invalid or missing 'executionId' in event"):
            lambda_handler(event, None)
        
        # Service should not be called
        mock_migration_service.segment.assert_not_called()
    
    def test_lambda_handler_validation_error_total_segments(self, mock_migration_service):
        """Test that validation errors for totalSegments are properly handled"""
        event = {"executionId": "test-execution-id", "totalSegments": 0}
        
        with pytest.raises(ValueError, match="'totalSegments' must be positive"):
            lambda_handler(event, None)
        
        # Service should not be called
        mock_migration_service.segment.assert_not_called()
    
    def test_lambda_handler_service_exception(self, valid_event, mock_migration_service):
        """Test that exceptions from the service are re-raised"""
        mock_migration_service.segment.side_effect = RuntimeError("Service error")
        
        with pytest.raises(RuntimeError, match="Service error"):
            lambda_handler(valid_event, None)
    
    def test_lambda_handler_logging_on_validation_error(self, mocker):
        """Test that validation errors are properly logged with original values"""
        mock_logger = mocker.patch("handlers.migration_dynamodb_segment_handler.logger")
        
        event = {"executionId": "", "totalSegments": 4}
        
        with pytest.raises(ValueError):
            lambda_handler(event, None)
        
        # Verify logging was called with correct extras
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        extras = call_args.kwargs["extra"]
        assert extras["executionId"] == ""  # Original value from event
        assert extras["totalSegments"] == 4  # Original value from event
        assert extras["errorType"] == "ValueError"
        assert call_args.kwargs.get("exc_info") is True
    
    def test_lambda_handler_logging_on_service_error(self, valid_event, mock_migration_service, mocker):
        """Test that service errors are properly logged with processed values"""
        mock_logger = mocker.patch("handlers.migration_dynamodb_segment_handler.logger")
        mock_migration_service.segment.side_effect = RuntimeError("S3 connection failed")
        
        with pytest.raises(RuntimeError):
            lambda_handler(valid_event, None)
        
        # Verify logging was called with correct extras
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        extras = call_args.kwargs["extra"]
        assert extras["executionId"] == "execution-12345"  # Processed value
        assert extras["totalSegments"] == 4  # Processed value
        assert extras["errorType"] == "RuntimeError"
    
    def test_lambda_handler_logging_partial_validation_failure(self, mocker):
        """Test logging when validation fails after one field is processed"""
        mock_logger = mocker.patch("handlers.migration_dynamodb_segment_handler.logger")
        
        # Valid executionId but invalid totalSegments
        event = {"executionId": "test-execution-id", "totalSegments": -1}
        
        with pytest.raises(ValueError):
            lambda_handler(event, None)
        
        call_args = mock_logger.error.call_args
        extras = call_args.kwargs["extra"]
        assert extras["executionId"] == "test-execution-id"  # Processed value
        assert extras["totalSegments"] == -1  # Original value (validation failed)
        assert extras["errorType"] == "ValueError"


# Integration tests
class TestIntegration:
    """Integration test cases"""
    
    @pytest.mark.parametrize("execution_id,total_segments,expected_parsed_id,expected_total", [
        ("arn:aws:states:region:account:execution:machine:my-exec", 4.0, "my-exec", 4),
        ("simple-id", "10", "simple-id", 10),
        ("part1:part2:final", 1000, "final", 1000)
    ])
    def test_lambda_handler_full_flow(self, execution_id, total_segments, expected_parsed_id, expected_total, mock_migration_service):
        """Test complete flow with various input formats"""
        event = {"executionId": execution_id, "totalSegments": total_segments}
        expected_result = {'bucket': 'migration-bucket', 'key': f'stepfunctionconfig-{expected_parsed_id}.json'}
        mock_migration_service.segment.return_value = expected_result
        
        result = lambda_handler(event, None)
        
        mock_migration_service.segment.assert_called_once_with(expected_parsed_id, expected_total)
        assert result == expected_result