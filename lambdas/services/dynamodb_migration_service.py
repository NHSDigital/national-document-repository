from typing import Callable, Iterable

from services.base.dynamo_service import DynamoDBService
from utils.audit_logging_setup import LoggingService

logger = LoggingService(__name__)


class Dynamodb_migration_service:
    def __init__(self, environment: str, table_name: str, run_migration: bool = False):
        self.environment = environment
        self.table_name = table_name
        self.run_migration = run_migration
        self.logger = LoggingService("DynamoDB Migration Service")
        self.dynamo_service = DynamoDBService()
        self.target_table = f"{self.environment}_{self.table_name}"

    def process_entries(self, label: str, entries: Iterable[dict], update_fn: Callable[[dict], dict | None]):
        self.logger.info(f"Running {label} migration")

        for index, entry in enumerate(entries, start=1):
            item_id = entry.get("ID")
            self.logger.info(f"[{label}] Processing item {index} (ID: {item_id})")

            updated_fields = update_fn(entry)
            if not updated_fields:
                self.logger.debug(f"[{label}] Item {item_id} does not require update, skipping.")
                continue

            if self.run_migration:
                self.logger.info(f"Updating item {item_id} with {updated_fields}")
                try:
                    self.dynamo_service.update_item(
                        table_name=self.target_table,
                        key_pair={"ID": item_id},
                        updated_fields=updated_fields,
                    )
                except Exception as e:
                    self.logger.error(f"Failed to update item {item_id}: {str(e)}")
                    continue
            else:
                self.logger.info(f"[Dry Run] Would update item {item_id} with {updated_fields}")

        self.logger.info(f"{label} migration completed.")
