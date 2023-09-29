import logging
from typing import Dict
from urllib import parse

import boto3
from botocore.client import Config as BotoConfig

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class S3Service:
    def __init__(self):
        config = BotoConfig(retries={"max_attempts": 3, "mode": "standard"})
        self.client = boto3.client("s3", region_name="eu-west-2", config=config)
        self.presigned_url_expiry = 1800

    # S3 Location should be a minimum of a s3_object_key but can also be a directory location in the form of
    # {{directory}}/{{s3_object_key}}
    def create_document_presigned_url_handler(
        self, s3_bucket_name: str, s3_object_location: str
    ):
        return self.client.generate_presigned_post(
            s3_bucket_name,
            s3_object_location,
            Fields=None,
            Conditions=None,
            ExpiresIn=self.presigned_url_expiry,
        )

    def create_download_presigned_url(self, s3_bucket_name: str, file_key: str):
        logger.info("Generating presigned URL for manifest")
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": s3_bucket_name, "Key": file_key},
            ExpiresIn=self.presigned_url_expiry,
        )

    def download_file(self, s3_bucket_name: str, file_key: str, download_path: str):
        return self.client.download_file(s3_bucket_name, file_key, download_path)

    def upload_file(self, file_name: str, s3_bucket_name: str, file_key: str):
        return self.client.upload_file(file_name, s3_bucket_name, file_key)

    def upload_file_with_tags(
        self, file_name: str, s3_bucket_name: str, file_key: str, tags: Dict[str, str]
    ):
        return self.client.upload_file(
            file_name, s3_bucket_name, file_key, {"Tagging": parse.urlencode(tags)}
        )
