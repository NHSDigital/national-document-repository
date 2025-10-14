import logging

from services.migration_dynamodb_segment_service import MigrationDynamoDBSegmentService

logger = logging.getLogger(__name__)

def lambda_handler(event):
    execution_id = event.get('executionId', 'unknown')
    total_segments = event.get('totalSegments', 'unknown')
    
    try:
        if 'executionId' not in event or not isinstance(event['executionId'], str) or event['executionId'].strip() == '':
            raise ValueError("Invalid or missing 'executionId' in event")
        if 'totalSegments' not in event:
            raise ValueError("Missing 'totalSegments' in event")
        try:
            total_segments = int(event['totalSegments'])
            if total_segments <= 0:
                raise ValueError
            if total_segments > 1000:
                raise ValueError("'totalSegments' exceeds maximum allowed value of 1000")
        except (ValueError, TypeError):
            raise ValueError("Invalid 'totalSegments' in event")

        id = event['executionId'].split(':')[-1]
        return MigrationDynamoDBSegmentService().segment(id, total_segments)
    except Exception as e:
        extras = {
            'executionId': execution_id,
            'totalSegments': total_segments,
            'errorType': type(e).__name__
        }
        logger.error(f"Exception in migration_dynamodb_segment_handler: {e}", extra=extras, exc_info=True)
        raise
