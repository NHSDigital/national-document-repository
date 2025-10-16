import logging
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from services.migration_dynamodb_segment_service import MigrationDynamoDBSegmentService

logger = logging.getLogger(__name__)

# Initialize boto3 client outside handler with explicit timeout
config = Config(
    connect_timeout=5,
    read_timeout=10,
    retries={'max_attempts': 3}
)

# Initialize DynamoDB clients dictionary for reuse across invocations
# Using a dictionary (initialized at module level) to satisfy SonarCube requirement that AWS clients be initialized outside the Lambda handler
dynamodb_clients = {}

def get_dynamodb_client(region):
    """Get or create a DynamoDB client for the specified region"""
    if region not in dynamodb_clients:
        dynamodb_clients[region] = boto3.client('dynamodb', region_name=region, config=config)
    return dynamodb_clients[region]

def validate_execution_id(event):
    """Validate and extract execution_id from event"""
    if 'executionId' not in event:
        raise ValueError("Invalid or missing 'executionId' in event")
    
    execution_id = event['executionId']
    if not isinstance(execution_id, str) or execution_id.strip() == "":
        raise ValueError("Invalid or missing 'executionId' in event")
    
    # Extract just the ID part
    return execution_id.split(':')[-1]

def validate_total_segments(event):
    """Validate and extract total_segments from event"""
    if 'totalSegments' not in event:
        raise ValueError("Invalid 'totalSegments' in event - must be a valid integer")
        
    try:
        total_segments = int(event['totalSegments'])
    except (ValueError, TypeError):
        raise ValueError("Invalid 'totalSegments' in event - must be a valid integer")
        
    if total_segments <= 0:
        raise ValueError("'totalSegments' must be positive")
    if total_segments > 1000:
        raise ValueError("'totalSegments' exceeds maximum allowed value of 1000")
    
    return total_segments

def validate_table_arn(event):
    """Validate and extract table information from DynamoDB table ARN"""
    if 'tableArn' not in event:
        raise ValueError("Invalid or missing 'tableArn' in event")
    
    table_arn = event['tableArn']
    if not isinstance(table_arn, str) or table_arn.strip() == "":
        raise ValueError("Invalid or missing 'tableArn' in event")
    
    # Validate ARN format: arn:aws:dynamodb:region:account-id:table/table-name
    if not table_arn.startswith('arn:aws:dynamodb:'):
        raise ValueError("Invalid DynamoDB table ARN format - must start with 'arn:aws:dynamodb:'")
    
    if ':table/' not in table_arn:
        raise ValueError("Invalid DynamoDB table ARN format - missing ':table/' component")
    
    try:
        table_name = table_arn.split(':table/')[-1]
        if not table_name:
            raise ValueError("Invalid DynamoDB table ARN format - table name is empty")
        
        # Extract region for validation
        arn_parts = table_arn.split(':')
        if len(arn_parts) < 6:
            raise ValueError("Invalid DynamoDB table ARN format - insufficient components")
        
        region = arn_parts[3]
        if not region:
            raise ValueError("Invalid DynamoDB table ARN format - region is empty")
            
        return table_name, region
        
    except (IndexError, ValueError) as e:
        raise ValueError(f"Invalid DynamoDB table ARN format: {e}")

def validate_table_exists(table_name, region):
    """Validate that the DynamoDB table exists and is accessible"""
    try:
        client = get_dynamodb_client(region)
        response = client.describe_table(TableName=table_name)
        table_status = response['Table']['TableStatus']
        
        if table_status not in ['ACTIVE', 'UPDATING']:
            raise ValueError(f"DynamoDB table '{table_name}' is not in ACTIVE status. Current status: {table_status}")
        
        return True
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == 'ResourceNotFoundException':
            raise ValueError(f"DynamoDB table '{table_name}' does not exist in region '{region}'")
        elif error_code == 'AccessDeniedException':
            raise ValueError(f"Access denied to DynamoDB table '{table_name}'. Check IAM permissions")
        else:
            raise ValueError(f"Failed to validate DynamoDB table '{table_name}': {e}")

def lambda_handler(event, context):
    total_segments = None
    execution_id = None
    
    try:
        table_name, region = validate_table_arn(event)
        validate_table_exists(table_name, region)
        execution_id = validate_execution_id(event)
        total_segments = validate_total_segments(event)

        return MigrationDynamoDBSegmentService().segment(execution_id, total_segments)
        
    except Exception as e:
        extras = {
            'executionId': execution_id if execution_id is not None else event.get('executionId'),
            'totalSegments': total_segments if total_segments is not None else event.get('totalSegments'),
            'errorType': type(e).__name__
        }
        logger.error(f"Exception in migration_dynamodb_segment_handler: {e}", extra=extras, exc_info=True)
        raise
