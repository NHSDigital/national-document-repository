import logging

from services.migration_dynamodb_segment_service import MigrationDynamoDBSegmentService

logger = logging.getLogger(__name__)

def lambda_handler(event):
    total_segments = None
    execution_id = None
    
    try:
        if 'executionId' not in event or not isinstance(event['executionId'], str) or event['executionId'].strip() == '':
            raise ValueError("Invalid or missing 'executionId' in event")
        
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

        execution_id = event['executionId'].split(':')[-1]
        return MigrationDynamoDBSegmentService().segment(execution_id, total_segments)
    except Exception as e:
        extras = {
            'executionId': execution_id if execution_id is not None else event.get('executionId'),
            'totalSegments': total_segments if total_segments is not None else event.get('totalSegments'),
            'errorType': type(e).__name__
        }
        logger.error(f"Exception in migration_dynamodb_segment_handler: {e}", extra=extras, exc_info=True)
        raise
