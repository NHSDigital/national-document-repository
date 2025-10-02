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
            self.logger.info("No entries provided")
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

    @staticmethod
    def parse_s3_path(s3_path: str) -> tuple[str, str] | None:
        """Parse S3 path into bucket and key components"""
        if not s3_path or not s3_path.startswith("s3://"):
            return None

        path = s3_path[5:]
        parts = path.split("/", 1)

        if len(parts) != 2 or not parts[0] or not parts[1]:
            return None

        return parts[0], parts[1]

    def update_s3_metadata_entry(self, entry: dict) -> dict | None:
        """Update entry with S3 metadata (FileSize, S3Key, S3VersionID)"""

        # TODO make idempotent
        # Cancel if any of the fields already exist
        # if any(field in entry for field in ( "S3Key", "S3VersionID")):
        #   return None

        file_location = entry.get("FileLocation")
        if not file_location:
            self.logger.warning(f"Missing FileLocation for entry: {entry.get('ID')}")
            return None

        s3_bucket_path_parts = FileSizeMigration.parse_s3_path(file_location)

        if not s3_bucket_path_parts:
            self.logger.warning(f"Invalid S3 path: {file_location}")
            return None

        s3_bucket, s3_key = s3_bucket_path_parts

        # Get metadata from S3
        s3_head = self.s3_service.get_head_object(s3_bucket, s3_key)

        if not s3_head:
            self.logger.warning(f"Could not retrieve S3 metadata for item {s3_key}")
            return None

        content_length = s3_head.get('ContentLength')
        version_id = s3_head.get('VersionId')

        updated_fields = {}

        if 'FileSize' not in entry:
            if content_length is None:
                raise ValueError(f"FileSize missing in both DynamoDB and S3 for item {s3_key}")
            updated_fields['FileSize'] = content_length

        if 'S3Key' not in entry:
            updated_fields['S3Key'] = s3_key

        if 'S3VersionID' not in entry:
            if version_id is None:
                raise ValueError(f"S3VersionID missing in both DynamoDB and S3 for item {s3_key}")
            updated_fields['S3VersionID'] = version_id

        return updated_fields if updated_fields else None

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
        migration.dynamo_service.scan_table(migration.target_table)
    )

    update_functions = migration.main(entries=entries_to_process)

    for label, fn in update_functions:
        migration.process_entries(label=label, entries=entries_to_process, update_fn=fn)