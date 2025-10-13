import logging

from services.migration_dynamodb_segment_service import MigrationDynamoDBSegmentService

logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    try:
        if 'executionId' not in event or not isinstance(event['executionId'], str) or event['executionId'].strip() == '':
            raise ValueError("Invalid or missing 'executionId' in event")
        if 'TotalSegments' not in event:
            raise ValueError("Missing 'TotalSegments' in event'")
        try:
            total_segments = int(event['TotalSegments'])
            if total_segments <= 0:
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError("Invalid 'TotalSegments' in event")
        if 'BucketName' not in event or not isinstance(event['BucketName'], str) or not event['BucketName']:
            raise ValueError("Invalid 'BucketName' in event")

        id = event['executionId'].split(':')[-1]
        bucket_name = event['BucketName']
        return MigrationDynamoDBSegmentService().segment(id, total_segments, bucket_name)
    except Exception as e:
        logger.error(f"Exception in migration_dynamodb_segment_handler: {e}")
        raise




