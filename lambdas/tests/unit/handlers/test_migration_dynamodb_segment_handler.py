import pytest
from botocore.exceptions import ClientError
from handlers.migration_dynamodb_segment_handler import lambda_handler, validate_execution_id, validate_total_segments, validate_table_arn, validate_table_exists, get_dynamodb_client


# Test fixtures - these are reusable test data/mocks
@pytest.fixture
def valid_event():
    """Creates a valid event for testing successful scenarios"""
    return {
        "executionId": "arn:aws:states:us-east-1:123456789012:execution:MyStateMachine:execution-12345",
        "totalSegments": 4,
        "tableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/MyTable"
    }

@pytest.fixture
def mock_migration_service(mocker):
    """Mocks the MigrationDynamoDBSegmentService class"""
    mocked_class = mocker.patch("handlers.migration_dynamodb_segment_handler.MigrationDynamoDBSegmentService")
    mocked_instance = mocked_class.return_value
    yield mocked_instance


@pytest.fixture
def mock_dynamodb_client(mocker):
    """Mocks the get_dynamodb_client function to return a mock client"""
    mock_client = mocker.MagicMock()
    mocker.patch("handlers.migration_dynamodb_segment_handler.get_dynamodb_client", return_value=mock_client)
    return mock_client
 

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


# Tests for validate_table_arn function
class TestValidateTableArn:
    """Test cases for the validate_table_arn function"""
    
    def test_validate_table_arn_success(self):
        """Test that valid table ARN is correctly parsed"""
        event = {"tableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/MyTable"}
        table_name, region = validate_table_arn(event)
        assert table_name == "MyTable"
        assert region == "us-east-1"
    
    def test_validate_table_arn_with_hyphenated_table_name(self):
        """Test that table names with hyphens are correctly parsed"""
        event = {"tableArn": "arn:aws:dynamodb:eu-west-2:123456789012:table/my-table-name"}
        table_name, region = validate_table_arn(event)
        assert table_name == "my-table-name"
        assert region == "eu-west-2"
    
    @pytest.mark.parametrize("table_arn", [None, "", "   ", 12345, []])
    def test_validate_table_arn_invalid_values(self, table_arn):
        """Test that invalid tableArn values raise ValueError"""
        event = {"tableArn": table_arn}
        with pytest.raises(ValueError, match="Invalid or missing 'tableArn' in event"):
            validate_table_arn(event)
    
    def test_validate_table_arn_missing_key(self):
        """Test that missing tableArn key raises ValueError"""
        event = {}
        with pytest.raises(ValueError, match="Invalid or missing 'tableArn' in event"):
            validate_table_arn(event)
    
    def test_validate_table_arn_wrong_service(self):
        """Test that non-DynamoDB ARN raises ValueError"""
        event = {"tableArn": "arn:aws:s3:::my-bucket"}
        with pytest.raises(ValueError, match="must start with 'arn:aws:dynamodb:'"):
            validate_table_arn(event)
    
    def test_validate_table_arn_missing_table_component(self):
        """Test that ARN without :table/ component raises ValueError"""
        event = {"tableArn": "arn:aws:dynamodb:us-east-1:123456789012:MyTable"}
        with pytest.raises(ValueError, match="missing ':table/' component"):
            validate_table_arn(event)
    
    def test_validate_table_arn_empty_table_name(self):
        """Test that ARN with empty table name raises ValueError"""
        event = {"tableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/"}
        with pytest.raises(ValueError, match="table name is empty"):
            validate_table_arn(event)
    
    def test_validate_table_arn_empty_region(self):
        """Test that ARN with empty region raises ValueError"""
        event = {"tableArn": "arn:aws:dynamodb::123456789012:table/MyTable"}
        with pytest.raises(ValueError, match="region is empty"):
            validate_table_arn(event)
    
    def test_validate_table_arn_insufficient_components(self):
        """Test that malformed ARN with insufficient components raises ValueError"""
        event = {"tableArn": "arn:aws:dynamodb:us-east-1:table/MyTable"}
        with pytest.raises(ValueError, match="insufficient components"):
            validate_table_arn(event)


# Tests for validate_table_exists function
class TestValidateTableExists:
    """Test cases for the validate_table_exists function"""
    
    def test_validate_table_exists_active(self, mock_dynamodb_client):
        """Test that ACTIVE table passes validation"""
        mock_dynamodb_client.describe_table.return_value = {
            'Table': {'TableStatus': 'ACTIVE'}
        }
        
        result = validate_table_exists("MyTable", "us-east-1")
        assert result is True
        mock_dynamodb_client.describe_table.assert_called_once_with(TableName="MyTable")
    
    def test_validate_table_exists_updating(self, mock_dynamodb_client):
        """Test that UPDATING table passes validation"""
        mock_dynamodb_client.describe_table.return_value = {
            'Table': {'TableStatus': 'UPDATING'}
        }
        
        result = validate_table_exists("MyTable", "us-east-1")
        assert result is True
    
    @pytest.mark.parametrize("status", ["CREATING", "DELETING", "ARCHIVED"])
    def test_validate_table_exists_invalid_status(self, status, mock_dynamodb_client):
        """Test that tables in invalid status raise ValueError"""
        mock_dynamodb_client.describe_table.return_value = {
            'Table': {'TableStatus': status}
        }
        
        with pytest.raises(ValueError, match=f"is not in ACTIVE status. Current status: {status}"):
            validate_table_exists("MyTable", "us-east-1")
    
    def test_validate_table_exists_not_found(self, mock_dynamodb_client):
        """Test that non-existent table raises ValueError"""
        error_response = {'Error': {'Code': 'ResourceNotFoundException'}}
        mock_dynamodb_client.describe_table.side_effect = ClientError(error_response, 'DescribeTable')
        
        with pytest.raises(ValueError, match="does not exist in region 'us-east-1'"):
            validate_table_exists("MyTable", "us-east-1")
    
    def test_validate_table_exists_access_denied(self, mock_dynamodb_client):
        """Test that access denied raises ValueError with appropriate message"""
        error_response = {'Error': {'Code': 'AccessDeniedException'}}
        mock_dynamodb_client.describe_table.side_effect = ClientError(error_response, 'DescribeTable')
        
        with pytest.raises(ValueError, match="Access denied to DynamoDB table 'MyTable'. Check IAM permissions"):
            validate_table_exists("MyTable", "us-east-1")
    
    def test_validate_table_exists_other_client_error(self, mock_dynamodb_client):
        """Test that other ClientErrors are handled appropriately"""
        error_response = {'Error': {'Code': 'UnknownError'}}
        mock_dynamodb_client.describe_table.side_effect = ClientError(error_response, 'DescribeTable')
        
        with pytest.raises(ValueError, match="Failed to validate DynamoDB table 'MyTable'"):
            validate_table_exists("MyTable", "us-east-1")


# Tests for lambda_handler function
class TestLambdaHandler:
    """Test cases for the lambda_handler function"""
    
    def test_lambda_handler_success(self, valid_event, mock_migration_service, mock_dynamodb_client):
        """Test that lambda_handler works correctly with valid input"""
        mock_dynamodb_client.describe_table.return_value = {
            'Table': {'TableStatus': 'ACTIVE'}
        }
        expected_result = {'bucket': 'migration-bucket', 'key': 'stepfunctionconfig-execution-12345.json'}
        mock_migration_service.segment.return_value = expected_result
        
        result = lambda_handler(valid_event, None)
        
        mock_dynamodb_client.describe_table.assert_called_once_with(TableName="MyTable")
        mock_migration_service.segment.assert_called_once_with("execution-12345", 4)
        assert result == expected_result
    
    def test_lambda_handler_validation_error_execution_id(self, mock_migration_service, mock_dynamodb_client):
        """Test that validation errors for executionId are properly handled"""
        mock_dynamodb_client.describe_table.return_value = {
            'Table': {'TableStatus': 'ACTIVE'}
        }
        event = {"executionId": "", "totalSegments": 4, "tableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/MyTable"}
        
        with pytest.raises(ValueError, match="Invalid or missing 'executionId' in event"):
            lambda_handler(event, None)
        
        # Service should not be called
        mock_migration_service.segment.assert_not_called()
    
    def test_lambda_handler_validation_error_total_segments(self, mock_migration_service, mock_dynamodb_client):
        """Test that validation errors for totalSegments are properly handled"""
        mock_dynamodb_client.describe_table.return_value = {
            'Table': {'TableStatus': 'ACTIVE'}
        }
        event = {"executionId": "test-execution-id", "totalSegments": 0, "tableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/MyTable"}
        
        with pytest.raises(ValueError, match="'totalSegments' must be positive"):
            lambda_handler(event, None)
        
        # Service should not be called
        mock_migration_service.segment.assert_not_called()
    
    def test_lambda_handler_validation_error_table_arn(self, mock_migration_service, mock_dynamodb_client):
        """Test that validation errors for tableArn are properly handled"""
        event = {"executionId": "test-execution-id", "totalSegments": 4, "tableArn": "invalid-arn"}
        
        with pytest.raises(ValueError, match="Invalid DynamoDB table ARN format"):
            lambda_handler(event, None)
        
        # Service should not be called
        mock_migration_service.segment.assert_not_called()
        mock_dynamodb_client.describe_table.assert_not_called()
    
    def test_lambda_handler_table_not_found(self, mock_migration_service, mock_dynamodb_client):
        """Test that non-existent table raises appropriate error"""
        error_response = {'Error': {'Code': 'ResourceNotFoundException'}}
        mock_dynamodb_client.describe_table.side_effect = ClientError(error_response, 'DescribeTable')
        
        event = {
            "executionId": "test-execution-id",
            "totalSegments": 4,
            "tableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/NonExistentTable"
        }
        
        with pytest.raises(ValueError, match="does not exist in region"):
            lambda_handler(event, None)
        
        mock_migration_service.segment.assert_not_called()
    
    def test_lambda_handler_service_exception(self, valid_event, mock_migration_service, mock_dynamodb_client):
        """Test that exceptions from the service are re-raised"""
        mock_dynamodb_client.describe_table.return_value = {
            'Table': {'TableStatus': 'ACTIVE'}
        }
        mock_migration_service.segment.side_effect = RuntimeError("Service error")
        
        with pytest.raises(RuntimeError, match="Service error"):
            lambda_handler(valid_event, None)
    
    def test_lambda_handler_logging_on_validation_error(self, mocker, mock_dynamodb_client):
        """Test that validation errors are properly logged with original values"""
        mock_logger = mocker.patch("handlers.migration_dynamodb_segment_handler.logger")
        mock_dynamodb_client.describe_table.return_value = {
            'Table': {'TableStatus': 'ACTIVE'}
        }
        
        event = {"executionId": "", "totalSegments": 4, "tableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/MyTable"}
        
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
    
    def test_lambda_handler_logging_on_service_error(self, valid_event, mock_migration_service, mocker, mock_dynamodb_client):
        """Test that service errors are properly logged with processed values"""
        mock_logger = mocker.patch("handlers.migration_dynamodb_segment_handler.logger")
        mock_dynamodb_client.describe_table.return_value = {
            'Table': {'TableStatus': 'ACTIVE'}
        }
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
    
    def test_lambda_handler_logging_partial_validation_failure(self, mocker, mock_dynamodb_client):
        """Test logging when validation fails after one field is processed"""
        mock_logger = mocker.patch("handlers.migration_dynamodb_segment_handler.logger")
        mock_dynamodb_client.describe_table.return_value = {
            'Table': {'TableStatus': 'ACTIVE'}
        }
        
        # Valid executionId but invalid totalSegments
        event = {"executionId": "test-execution-id", "totalSegments": -1, "tableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/MyTable"}
        
        with pytest.raises(ValueError):
            lambda_handler(event, None)
        
        call_args = mock_logger.error.call_args
        extras = call_args.kwargs["extra"]
        assert extras["executionId"] == "test-execution-id"  # Processed value
        assert extras["totalSegments"] == -1  # Original value (validation failed)
        assert extras["errorType"] == "ValueError"


# Tests for get_dynamodb_client function
class TestGetDynamoDBClient:
    """Test cases for the get_dynamodb_client function"""
    
    def test_get_dynamodb_client_creates_new_client(self, mocker):
        """Test that a new client is created when none exists"""
        mock_boto_client = mocker.patch("handlers.migration_dynamodb_segment_handler.boto3.client")
        mock_client = mocker.MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Clear the cached client
        import handlers.migration_dynamodb_segment_handler
        handlers.migration_dynamodb_segment_handler.dynamodb_client = None
        
        result = get_dynamodb_client("us-east-1")
        
        assert result == mock_client
        mock_boto_client.assert_called_once_with('dynamodb', region_name='us-east-1', config=mocker.ANY)
    
    def test_get_dynamodb_client_returns_cached_client(self, mocker):
        """Test that cached client is returned on subsequent calls"""
        mock_boto_client = mocker.patch("handlers.migration_dynamodb_segment_handler.boto3.client")
        mock_client = mocker.MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Clear the cached client
        import handlers.migration_dynamodb_segment_handler
        handlers.migration_dynamodb_segment_handler.dynamodb_client = None
        
        # First call creates the client
        result1 = get_dynamodb_client("us-east-1")
        # Second call should return cached client
        result2 = get_dynamodb_client("us-west-2")
        
        assert result1 == result2
        # boto3.client should only be called once
        mock_boto_client.assert_called_once()

# Integration tests
class TestIntegration:
    """Integration test cases"""
    
    @pytest.mark.parametrize("execution_id,total_segments,expected_parsed_id,expected_total", [
        ("arn:aws:states:region:account:execution:machine:my-exec", 4.0, "my-exec", 4),
        ("simple-id", "10", "simple-id", 10),
        ("part1:part2:final", 1000, "final", 1000)
    ])
    def test_lambda_handler_full_flow(self, execution_id, total_segments, expected_parsed_id, expected_total, mock_migration_service, mock_dynamodb_client):
        """Test complete flow with various input formats"""
        mock_dynamodb_client.describe_table.return_value = {
            'Table': {'TableStatus': 'ACTIVE'}
        }
        event = {
            "executionId": execution_id,
            "totalSegments": total_segments,
            "tableArn": "arn:aws:dynamodb:us-east-1:123456789012:table/MyTable"
        }
        expected_result = {'bucket': 'migration-bucket', 'key': f'stepfunctionconfig-{expected_parsed_id}.json'}
        mock_migration_service.segment.return_value = expected_result
        
        result = lambda_handler(event, None)
        
        mock_dynamodb_client.describe_table.assert_called_once_with(TableName="MyTable")
        mock_migration_service.segment.assert_called_once_with(expected_parsed_id, expected_total)
        assert result == expected_result