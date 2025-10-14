import random
import boto3
import json
import logging
import os

logger = logging.getLogger(__name__)

class MigrationDynamoDBSegmentService:
    def __init__(self):
        self.s3_client = boto3.client("s3")
        self.bucket_name = os.environ["MIGRATION_SEGMENT_BUCKET_NAME"]
        
    def segment(self, id: str, total_segments: int) -> dict:
        try:
            segments = list(range(0, total_segments))
            random.shuffle(segments)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=f"stepfunctionconfig-{id}.json",
                Body=str.encode(json.dumps(segments))
            )
            return {'bucket': self.bucket_name, 'key': f"stepfunctionconfig-{id}.json"}
        except Exception as e:
            extras = {
                'executionId': id,
                'totalSegments': total_segments,
                'bucketName': self.bucket_name,
                'errorType': type(e).__name__
            }
            logger.error(f"Exception in migration_dynamodb_segment_service: {e}", extra=extras, exc_info=True)
            raise