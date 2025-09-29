import importlib
import logging
import sys

from services.base.dynamo_service import DynamoDBService


class VersionMigration:
    def __init__(self, environment: str, table_name: str, dry_run: bool = False):
        self.environment = environment
        self.table_name = table_name
        self.dynamo_service = DynamoDBService()
        self.dry_run = dry_run
        self.logger = logging.getLogger("VersionMigration")

        self.target_table = f"{self.environment}_{self.table_name}"
        self.bulk_upload_table = f"{self.environment}_BulkUploadReport"

    def main(self):
        self.logger.info("Starting version migration")
        self.logger.info(f"Target table: {self.target_table}")
        self.logger.info(f"Dry run mode: {self.dry_run}")

        try:
            all_entries = self.dynamo_service.scan_whole_table(
                table_name=self.target_table
            )
            total_count = len(all_entries)

            # self.run_version_migration(all_entries=all_entries, total_count=total_count)
            self.run_author_migration(all_entries=all_entries, total_count=total_count)
            # self.run_deleted_cleanup_migration(
            #     all_entries=all_entries, total_count=total_count
            # )
            # self.run_custodian_migration(
            #     all_entries=all_entries, total_count=total_count
            # )
            # self.run_document_snomed_code_type_migration(
            #     all_entries=all_entries, total_count=total_count
            # )
            # self.run_status_migration(all_entries=all_entries, total_count=total_count)
        except Exception as e:
            self.logger.error("Migration failed", exc_info=e)
            raise

    def process_entries(
        self, label: str, all_entries: list[dict], total_count: int, update_fn
    ):
        self.logger.info(f"Running {label} migration")

        for index, entry in enumerate(all_entries, start=1):
            item_id = entry.get("ID")
            self.logger.info(
                f"[{label}] Processing item {index} of {total_count} (ID: {item_id})"
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

    def run_author_migration(self, all_entries: list[dict], total_count: int) -> None:
        self.logger.info("Running author migration")

        bulk_reports = self.dynamo_service.scan_whole_table(self.bulk_upload_table)

        bulk_upload_report_lookup: dict[str, dict] = {}

        for row in bulk_reports:
            nhs = row.get("NhsNumber")
            status = row.get("UploadStatus")
            timestamp = row.get("Timestamp")

            if not nhs or status != "complete" or not timestamp:
                continue

            stored_report = bulk_upload_report_lookup.get(nhs)
            if not stored_report:
                   bulk_upload_report_lookup[nhs] = row
            elif int(timestamp) > int(stored_report.get("Timestamp", 0)):
                   bulk_upload_report_lookup[nhs] = row

        def author_update(entry: dict) -> dict | None:
            current_author = entry.get("Author")
            nhs_number = entry.get("NhsNumber")

            if current_author:
                return None

            bulk_upload_row = bulk_upload_report_lookup.get(nhs_number)
            if not bulk_upload_row:
                self.logger.warning(
                    f"No matching completed bulk upload found for NHS {nhs_number}"
                )
                return None

            new_author = bulk_upload_row.get("UploaderOdsCode")
            if not new_author:
                self.logger.warning(f"No uploader ODS code found for NHS {nhs_number}")
                return None

            return {"Author": new_author}

        self.process_entries("Author", all_entries, total_count, author_update)


def setup_logging():
    importlib.reload(logging)
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


if __name__ == "__main__":
    import argparse

    setup_logging()

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
    VersionMigration(
        environment=args.environment, table_name=args.table_name, dry_run=args.dry_run
    ).main()
