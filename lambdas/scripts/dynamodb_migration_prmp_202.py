import os
import logging
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
# ...existing code...

def main(event, context):
    logger = logging.getLogger(__name__)
    # Error handling for environment variables
    try:
        total_segments_str = os.environ['TotalSegments']
        bucket_name = os.environ['BucketName']
    except KeyError as e:
        logger.error(f"Missing required environment variable: {e}")
        return {"error": f"Missing environment variable: {e}"}

    try:
        total_segments = int(total_segments_str)
    except ValueError:
        logger.error(f"TotalSegments must be an integer, got: {total_segments_str}")
        return {"error": f"TotalSegments must be an integer, got: {total_segments_str}"}

    # Error handling for event['executionId']
    try:
        execution_id = event['executionId']
        segment_id = execution_id.split(":")[1]
    except KeyError:
        logger.error("Missing 'executionId' in event")
        return {"error": "Missing 'executionId' in event"}
    except IndexError:
        logger.error(f"Malformed 'executionId', expected ':' in value: {event.get('executionId')}")
        return {"error": f"Malformed 'executionId', expected ':' in value: {event.get('executionId')}"}

    # ...existing code...

    s3_client = boto3.client('s3')
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=f"migration/{execution_id}/summary.json",
            Body=b"{}"
        )
    except (ClientError, NoCredentialsError, PartialCredentialsError) as e:
        logger.error(f"Failed to put object to S3: {e}")
        return {"error": f"Failed to put object to S3: {str(e)}"}

    # ...existing code...

