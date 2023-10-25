import logging
from typing import Optional

import boto3
from botocore.client import Config as BotoConfig

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class SQSService:
    def __init__(self):
        config = BotoConfig(retries={"max_attempts": 3, "mode": "standard"})
        self.client = boto3.client("sqs", config=config)

    def send_message_with_nhs_number_attr(
        self,
        queue_url: str,
        message_body: str,
        nhs_number: str,
        delay_second: int = 0,
    ):
        self.client.send_message(
            QueueUrl=queue_url,
            MessageAttributes={
                "NhsNumber": {"DataType": "String", "StringValue": nhs_number},
            },
            MessageBody=message_body,
            DelaySeconds=delay_second,
        )
