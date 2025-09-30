import importlib
import logging
import sys
import argparse
from enums.snomed_codes import SnomedCodes
from typing import Iterable, Callable

from models.document_reference import DocumentReference
from services.base.dynamo_service import DynamoDBService
from utils.audit_logging_setup import LoggingService


class VersionMigration:
    def __init__(self, environment: str, table_name: str, dry_run: bool = False):
        self.environment = environment
        self.table_name = table_name
        self.dry_run = dry_run
        self.logger = LoggingService("CustodianMigration")
        self.dynamo_service = DynamoDBService()

        self.target_table = f"{self.environment}_{self.table_name}"

    def main(
            self, entries: Iterable[dict]
    ) -> list[tuple[str, Callable[[dict], dict | None]]]:

        """
        Main entry point. Returns a list of update functions with labels.
        Accepts a list of entries for Lambda-based execution, or scans the table if `entries` is None.
        """
        self.logger.info("Starting version migration")
        self.logger.info(f"Target table: {self.target_table}")
        self.logger.info(f"Dry run mode: {self.dry_run}")

        if entries is None:
            self.logger.info("No entries provided — scanning entire table.")
            raise ValueError("Entries must be provided to main().")

        return [
            ("Custodian", self.update_custodian_entry),
            ("Status", self.update_status_entry),
            ("DocumentSnomedCodeType", self.update_document_snomed_code_type_entry),
            ("DocStatus", self.update_doc_status_entry),
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
    def update_custodian_entry(entry: dict) -> dict | None:
        current_gp_ods = entry.get("CurrentGpOds")
        custodian = entry.get("Custodian")

        if current_gp_ods and custodian != current_gp_ods:
            return {"Custodian": current_gp_ods}
        return None

    @staticmethod
    def update_status_entry(entry: dict) -> dict | None:
        if entry.get("Status") != "current":
            return {"Status": "current"}
        return None

    @staticmethod
    def update_document_snomed_code_type_entry(entry: dict) -> dict | None:
        expected_code = SnomedCodes.LLOYD_GEORGE.value.code
        if entry.get("DocumentSnomedCodeType") != expected_code:
            return {"DocumentSnomedCodeType": expected_code}
        return None

    def update_doc_status_entry(self, entry: dict) -> dict | None:
        try:
            document = DocumentReference(**entry)
        except Exception as e:
            self.logger.warning(f"[DocStatus] Skipping invalid item {entry.get('ID')}: {e}")
            return None

        if document.doc_status:
            return None

        inferred_status = document.infer_doc_status()

        if inferred_status:
            return {"DocStatus": inferred_status}

        self.logger.warning(f"[DocStatus] Cannot determine status for item {entry.get('ID')}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="dynamodb_migration.py",
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
