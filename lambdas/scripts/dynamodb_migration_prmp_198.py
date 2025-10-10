from typing import Callable, Iterable

from services.base.dynamo_service import DynamoDBService
from utils.audit_logging_setup import LoggingService


class VersionMigration:
    def __init__(self, environment: str, table_name: str, dry_run: bool = False):
        self.bulk_upload_lookup: dict[str, dict] | None = None
        self.environment = environment
        self.table_name = table_name
        self.dynamo_service = DynamoDBService()
        self.dry_run = dry_run
        self.logger = LoggingService("AuthorMigration")

        self.target_table = f"{self.environment}_{self.table_name}"
        self.bulk_upload_table = f"{self.environment}_BulkUploadReport"

    def main(
        self, entries: Iterable[dict]
    ) -> list[tuple[str, Callable[[dict], dict | None]]]:
        """
        Main entry point for the migration.
        Returns a list of (label, update function) tuples.
        """
        self.logger.info("Starting Author field migration")
        self.logger.info(f"Target table: {self.target_table}")
        self.logger.info(f"Dry run mode: {self.dry_run}")

        if entries is None:
            self.logger.error("No entries provided — expected a list of table items.")
            raise ValueError("Entries must be provided to main().")

        return [("Author", self.get_update_author_items)]

    def get_update_author_items(self, entry: dict) -> dict | None:
        """
        Determines whether the 'Author' field should be updated.
        Returns a dict with the update or None if no update is needed.
        """
        current_author = entry.get("Author")
        deleted_value = entry.get("Deleted")
        nhs_number = entry.get("NhsNumber")

        if current_author:
            return None

        if deleted_value not in (None, ""):
            self.logger.debug(
                f"[Author] Skipping {nhs_number}: Deleted field not empty ({deleted_value})."
            )
            return None

        if self.bulk_upload_lookup is None:
            self.bulk_upload_lookup = self.build_bulk_upload_lookup()

        bulk_upload_row = self.bulk_upload_lookup.get(nhs_number)
        if not bulk_upload_row:
            self.logger.warning(f"No completed bulk upload found for NHS {nhs_number}")
            return None

        new_author = bulk_upload_row.get("UploaderOdsCode")
        if not new_author:
            self.logger.warning(f"No uploader ODS code found for NHS {nhs_number}")
            return None

        return {"Author": new_author}

    def build_bulk_upload_lookup(self) -> dict[str, dict]:
        """
        Creates a lookup of the most recent completed bulk upload reports by NHS number.
        """
        self.logger.info("Building bulk upload lookup from BulkUploadReport table...")
        bulk_reports = self.dynamo_service.scan_whole_table(self.bulk_upload_table)
        lookup: dict[str, dict] = {}

        for row in bulk_reports:
            nhs = row.get("NhsNumber")
            status = row.get("UploadStatus")
            timestamp = row.get("Timestamp")

            if not nhs or status != "complete" or not timestamp:
                continue

            stored = lookup.get(nhs)
            if not stored or int(timestamp) > int(stored.get("Timestamp", 0)):
                lookup[nhs] = row

        self.logger.info(f"Loaded {len(lookup)} completed bulk upload entries.")
        return lookup

    def process_entries(
        self,
        label: str,
        entries: Iterable[dict],
        update_fn: Callable[[dict], dict | None],
    ):
        """Process a list of entries and apply an update function to each one."""
        self.logger.info(f"Running {label} migration")

        for index, entry in enumerate(entries, start=1):
            item_id = entry.get("ID")
            self.logger.info(f"[{label}] Processing item {index} (ID: {item_id})")

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
                try:
                    self.dynamo_service.update_item(
                        table_name=self.target_table,
                        key_pair={"ID": item_id},
                        updated_fields=updated_fields,
                    )
                except Exception as e:
                    self.logger.error(f"Failed to update {item_id}: {e}")

        self.logger.info(f"{label} migration completed.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        prog="dynamodb_migration_20250731.py",
        description="Migrate DynamoDB table columns",
    )
    parser.add_argument("environment", help="Environment prefix for DynamoDB table")
    parser.add_argument("table_name", help="DynamoDB table name to migrate")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run migration in dry-run mode (no writes)",
    )
    args = parser.parse_args()

    migration = VersionMigration(
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
