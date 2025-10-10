import random
import boto3
import json
import logging

logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    try:
        id = event['executionId'].split(':')[-1]
        segments = list(range(0, int(event['TotalSegments'])))
        random.shuffle(segments)
        boto3.client("s3").put_object(
            Bucket=event['BucketName'],
            Key=f"stepfunctionconfig-{id}.json",
            Body=str.encode(json.dumps(segments))
        )
        return {'bucket': event['BucketName'], 'key': f"stepfunctionconfig-{id}.json"}
    except Exception as e:
        logger.error(f"Exception in migration_dynamodb_segment_handler: {e}")
        raise
