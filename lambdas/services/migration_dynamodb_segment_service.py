import random
import boto3
import json
import logging

logger = logging.getLogger(__name__)

class MigrationDynamoDBSegmentService:
    def segment(self, id: str, total_segments: int, bucket_name: str) -> dict:
        try:
            segments = list(range(0, total_segments))
            random.shuffle(segments)
            boto3.client("s3").put_object(
                Bucket=bucket_name,
                Key=f"stepfunctionconfig-{id}.json",
                Body=str.encode(json.dumps(segments))
            )
            return {'bucket': bucket_name, 'key': f"stepfunctionconfig-{id}.json"}
        except Exception as e:
            logger.error(f"Exception in migration_dynamodb_segment_service: {e}")
            raise