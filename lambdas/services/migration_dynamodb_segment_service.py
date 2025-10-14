import random
import boto3
import json
import logging
import os
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class MigrationDynamoDBSegmentService:
    def __init__(self):
        self.s3_client = boto3.client("s3")
        self.bucket_name = os.environ.get("MIGRATION_SEGMENT_BUCKET_NAME")
        if not self.bucket_name:
            raise ValueError("MIGRATION_SEGMENT_BUCKET_NAME environment variable is required")
        
    def segment(self, id: str, total_segments: int) -> dict:
        try:
            segments = list(range(0, total_segments))
            random.shuffle(segments)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=f"stepfunctionconfig-{id}.json",
                Body=json.dumps(segments),            
                ContentType='application/json')
            return {'bucket': self.bucket_name, 'key': f"stepfunctionconfig-{id}.json"}
        except ClientError as aws_error:
            extras = {
                'executionId': id,
                'totalSegments': total_segments,
                'bucketName': self.bucket_name,
                'errorType': type(aws_error).__name__,
                'awsErrorCode': aws_error.response.get('Error', {}).get('Code', 'Unknown')
            }
            logger.error(f"AWS error in migration_dynamodb_segment_service: {aws_error}", extra=extras, exc_info=True)
            raise
        except Exception as e:
            extras = {
                'executionId': id,
                'totalSegments': total_segments,
                'bucketName': self.bucket_name,
                'errorType': type(e).__name__
            }
            logger.error(f"Exception in migration_dynamodb_segment_service: {e}", extra=extras, exc_info=True)
            raise