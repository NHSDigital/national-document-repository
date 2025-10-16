import logging
import boto3
from botocore.exceptions import ClientError
from services.dynamodb_migration_service import Dynamodb_migration_service

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def validate_event_input(event):
    required_fields = ["segment", "totalSegments", "tableName", "environment"]
    for field in required_fields:
        if field not in event:
            raise ValueError(f"Missing required field: '{field}' in event")

    try:
        segment = int(event["segment"])
        total_segments = int(event["totalSegments"])
    except (ValueError, TypeError):
        raise ValueError("'segment' and 'totalSegments' must be integers")

    if segment < 0:
        raise ValueError("'segment' must be >= 0")
    if total_segments <= 0:
        raise ValueError("'totalSegments' must be positive")
    if segment >= total_segments:
        raise ValueError("'segment' must be less than 'totalSegments'")

    table_name = str(event["tableName"]).strip()
    environment = str(event["environment"]).strip()
    run_migration = bool(event.get("run_migration", False))

    if not table_name:
        raise ValueError("'tableName' cannot be empty")
    if not environment:
        raise ValueError("'environment' cannot be empty")

    return segment, total_segments, table_name, environment, run_migration


def lambda_handler(event, context):
    """
    Lambda handler responsible for processing a specific DynamoDB segment.
    Input Example:
    {
        "segment": 1,
        "totalSegments": 10,
        "tableName": "UsersTable",
        "environment": "dev",
        "run_migration": true
    }

    Output Example:
    {
        "segmentId": 1,
        "totalSegments": 10,
        "scannedCount": 12345,
        "updatedCount": 500,
        "skippedCount": 200,
        "errorCount": 5,
        "status": "SUCCEEDED"
    }
    """
    dynamodb = boto3.resource("dynamodb")
    scanned_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0

    try:
        # 1️⃣ Validate input
        segment, total_segments, table_name, environment, run_migration = validate_event_input(event)
        table = dynamodb.Table(table_name)

        logger.info(f"Starting migration for segment {segment}/{total_segments} on table '{table_name}'")

        # 2️⃣ Initialize migration service
        migration_service = Dynamodb_migration_service(
            environment=environment,
            table_name=table_name,
            run_migration=run_migration
        )

        # 3️⃣ Configure the scan for this segment
        scan_kwargs = {
            "Segment": segment,
            "TotalSegments": total_segments
        }

        last_evaluated_key = None

        while True:
            if last_evaluated_key:
                scan_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = table.scan(**scan_kwargs)
            items = response.get("Items", [])
            scanned_count += len(items)

            # 4️⃣ Apply migration logic to scanned items
            try:
                migration_service.process_entries(
                    label=f"segment-{segment}",
                    entries=items,
                    update_fn=lambda item: determine_updates(item)  # 👈 see note below
                )
                updated_count += len(items)  # You could make this smarter if `process_entries` tracks updates
            except Exception as process_error:
                error_count += 1
                logger.error(f"Error processing segment {segment}: {process_error}")

            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break

        status = "SUCCEEDED" if error_count == 0 else "COMPLETED_WITH_ERRORS"

        result = {
            "segmentId": segment,
            "totalSegments": total_segments,
            "scannedCount": scanned_count,
            "updatedCount": updated_count,
            "skippedCount": skipped_count,
            "errorCount": error_count,
            "status": status
        }

        logger.info(f"Segment {segment}/{total_segments} completed with status: {status}")
        return result

    except ClientError as aws_error:
        logger.error(f"AWS error while processing segment: {aws_error}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error in dynamodb_migration_handler: {e}", exc_info=True)
        raise


# 🔧 Example update function — replace this with your migration logic
def determine_updates(item: dict) -> dict | None:
    """
    Determine which fields need updating for this item.
    Return a dict of updated fields, or None if no update is needed.
    """
    # Example migration: rename 'oldField' to 'newField'
    if "oldField" in item:
        return {"newField": item["oldField"]}
    return None
