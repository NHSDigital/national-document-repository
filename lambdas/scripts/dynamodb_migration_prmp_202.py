import importlib
import logging
import sys
import argparse
from typing import Iterable, Callable, Optional
import boto3
from botocore.exceptions import ClientError
from services.base.s3_service import S3Service

from services.base.dynamo_service import DynamoDBService


class FileSizeMigration:
    def __init__(self, environment: str, table_name: str, dry_run: bool = False):
        self.environment = environment
        self.table_name = table_name
        self.dry_run = dry_run
        self.logger = logging.getLogger("FileSizeMigration")
        self.dynamo_service = DynamoDBService()
        self.s3_service = S3Service()

        self.target_table = f"{self.environment}_{self.table_name}"

    def main(
            self, entries: Iterable[dict]
    ) -> list[tuple[str, Callable[[dict], dict | None]]]:

        """
        Main entry point. Returns a list of update functions with labels.
        Accepts a list of entries for Lambda-based execution, or scans the table if `entries` is None.
        """
        self.logger.info("Starting file size migration")
        self.logger.info(f"Target table: {self.target_table}")
        self.logger.info(f"Dry run mode: {self.dry_run}")

        if entries is None:
            self.logger.info("No entries provided — scanning entire table.")
            raise ValueError("Entries must be provided to main().")

        # Return list of (label, update_fn) pairs
        return [
            ("S3Metadata", self.update_s3_metadata_entry),
        ]

    def process_entries(
        self,
        label: str,
        entries: Iterable[dict],
        update_fn: Callable[[dict], dict | None],
    ):
        self.logger.info(f"Running {label} migration")

        for index, entry in enumerate(entries, start=1):
            item_id = entry.get("ID")
            self.logger.info(
                f"[{label}] Processing item {index} (ID: {item_id})"
            )

            updated_fields = update_fn(entry)
            if not updated_fields:
                self.logger.debug(
                    f"[{label}] Item {item_id} does not require update, skipping."
                )
                continue

            if self.dry_run:
                self.logger.info(
                    f"[Dry Run] Would update item {item_id} with {updated_fields}"
                )
            else:
                self.logger.info(f"Updating item {item_id} with {updated_fields}")
                self.dynamo_service.update_item(
                    table_name=self.target_table,
                    key_pair={"ID": item_id},
                    updated_fields=updated_fields,
                )

        self.logger.info(f"{label} migration completed.")

    def get_s3_values(self, bucket: str, key: str) -> dict:
        """Retrieve object metadata from S3"""
        try:
            return {
                'ContentLength': self.s3_service.get_file_size(
                    s3_bucket_name=bucket, object_key=key
                ),
                'VersionId': self.s3_service.get_version_id(
                    s3_bucket_name=bucket, object_key=key
                )
            }
        except ClientError as e:
            self.logger.error(f"Error retrieving S3 metadata for {bucket}/{key}: {e}")
            return {}

    def update_s3_metadata_entry(self, entry: dict) -> dict | None:
        """Update entry with S3 metadata (FileSize, S3Key, S3VersionID)"""
        # Cancel if any of the fields already exist
        if any(field in entry for field in ("FileSize", "S3Key", "S3VersionID")):
            return None

        s3_bucket_path = entry.get("FileLocation")

        if not s3_bucket_path or not s3_bucket_path.startswith("s3://"):
            self.logger.warning(f"Invalid S3 path: {s3_bucket_path}")
            return None

        path = s3_bucket_path[5:]  # Remove "s3://"
        parts = path.split("/", 1)

        if len(parts) != 2:
            self.logger.warning(f"Invalid S3 path format: {s3_bucket_path}")
            return None

        s3_bucket = parts[0]
        s3_key = parts[1]

        if not s3_bucket or not s3_key:
            self.logger.warning(f"Item missing S3 bucket or key information")
            return None

        # Get metadata from S3
        s3_values = self.get_s3_values(s3_bucket, s3_key)

        if not s3_values or not s3_values.get('ContentLength'):
            self.logger.warning(f"Could not retrieve S3 metadata for item {s3_key}")
            return None

        updated_fields = {
            'FileSize': s3_values.get('ContentLength'),
            'S3Key': s3_key,
            'S3VersionID': s3_values.get('VersionId')
        }

        return updated_fields


def setup_logging():
    importlib.reload(logging)
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


if __name__ == "__main__":
    setup_logging()

    parser = argparse.ArgumentParser(
        prog="dynamodb_migration.py",
        description="Migrate DynamoDB table file size metadata",
    )
    parser.add_argument("environment", help="Environment prefix for DynamoDB table")
    parser.add_argument("table_name", help="DynamoDB table name to migrate")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run migration in dry-run mode (no writes)",
    )
    args = parser.parse_args()

    migration = FileSizeMigration(
        environment=args.environment,
        table_name=args.table_name,
        dry_run=args.dry_run,
    )

    entries_to_process = list(
        migration.dynamo_service.stream_whole_table(migration.target_table)
    )

    update_functions = migration.main(entries=entries_to_process)

    for label, fn in update_functions:
        migration.process_entries(label=label, entries=entries_to_process, update_fn=fn)