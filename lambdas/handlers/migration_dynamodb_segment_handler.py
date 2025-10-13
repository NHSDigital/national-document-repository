import logging

from services.migration_dynamodb_segment_service import MigrationDynamoDBSegmentService

logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    try:
        if 'executionId' not in event or not isinstance(event['executionId'], str) or event['executionId'].strip() == '':
            raise ValueError("Invalid or missing 'executionId' in event")
        if 'totalSegments' not in event:
            raise ValueError("Missing 'totalSegments' in event")
        try:
            total_segments = int(event['totalSegments'])
            if total_segments <= 0:
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError("Invalid 'totalSegments' in event")
        if 'bucketName' not in event or not isinstance(event['bucketName'], str) or not event['bucketName']:
            raise ValueError("Invalid 'bucketName' in event")

        id = event['executionId'].split(':')[-1]
        bucket_name = event['bucketName']
        return MigrationDynamoDBSegmentService().segment(id, total_segments, bucket_name)
    except Exception as e:
        logger.error(f"Exception in migration_dynamodb_segment_handler: {e}")
        raise




