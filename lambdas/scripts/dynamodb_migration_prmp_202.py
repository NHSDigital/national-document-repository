import argparse
from typing import Iterable, Callable

from enums.snomed_codes import SnomedCodes
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
        Main entry point for the migration.
        Returns a list of (label, update function) tuples.
        Accepts a list of entries for Lambda-based execution, or scans the table if `entries` is None.
        """
        self.logger.info("Starting version migration")
        self.logger.info(f"Target table: {self.target_table}")
        self.logger.info(f"Dry run mode: {self.dry_run}")

        if entries is None:
            self.logger.info("No entries provided — scanning entire table.")
            raise ValueError("Entries must be provided to main().")

        return [
            ("LGTableValues", self.update_entry)
        ]

    def process_entries(
            self,
            label: str,
            entries: Iterable[dict],
            update_fn: Callable[[dict], dict | None],
    ):
        """
        Processes a list of entries, applying the update function to each.
        Logs progress and handles dry-run mode.
        """
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
        self.logger.info(f"{label} migration completed.")  # Moved outside the loop

    def update_entry(self, entry: dict ) -> dict | None:
        """
        Aggregates updates from all update methods for a single entry.
        Returns a dict of fields to update, or None if no update is needed.
        """
        updates = {}

        custodian_update = self.update_custodian_entry(entry)
        if custodian_update:
            updates.update(custodian_update)

        status_update = self.update_status_entry(entry)
        if status_update:
            updates.update(status_update)

        snomed_code_update = self.update_document_snomed_code_type_entry(entry)
        if snomed_code_update:
            updates.update(snomed_code_update)

        doc_status_update = self.update_doc_status_entry(entry)
        if doc_status_update:
            updates.update(doc_status_update)

        return updates if updates else None

    def update_custodian_entry(self, entry: dict) -> dict | None:
        """
        Updates the 'Custodian' field if it does not match 'CurrentGpOds'.
        Returns a dict with the update or None.
        """
        current_gp_ods = entry.get("CurrentGpOds")
        custodian = entry.get("Custodian")

        if current_gp_ods is None:
            self.logger.warning(f"[Custodian] CurrentGpOds is missing for item {entry.get('ID')}")
            return None
        if current_gp_ods is None or current_gp_ods != custodian:
            return {"Custodian": current_gp_ods}

        return None

    @staticmethod
    def update_status_entry(entry: dict) -> dict | None:
        """
        Ensures the 'Status' field is set to 'current'.
        Returns a dict with the update or None.
        """
        if entry.get("Status") != "current":
            return {"Status": "current"}
        return None

    @staticmethod
    def update_document_snomed_code_type_entry(entry: dict) -> dict | None:
        """
        Ensures the 'DocumentSnomedCodeType' field matches the expected SNOMED code.
        Returns a dict with the update or None.
        """
        expected_code = SnomedCodes.LLOYD_GEORGE.value.code
        if entry.get("DocumentSnomedCodeType") != expected_code:
            return {"DocumentSnomedCodeType": expected_code}
        return None

    def update_doc_status_entry(self, entry: dict) -> dict | None:
        """
        Infers and updates the 'DocStatus' field if missing.
        Returns a dict with the update or None.
        """
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
