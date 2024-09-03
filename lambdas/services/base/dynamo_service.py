from typing import Optional

import boto3
from boto3.dynamodb.conditions import Attr, ConditionBase, Key
from botocore.exceptions import ClientError
from utils.audit_logging_setup import LoggingService
from utils.dynamo_utils import (
    create_expression_attribute_values,
    create_expressions,
    create_update_expression,
)
from utils.exceptions import DynamoServiceException

logger = LoggingService(__name__)


class DynamoDBService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialised = False
        return cls._instance

    def __init__(self):
        if not self.initialised:
            self.dynamodb = boto3.resource("dynamodb", region_name="eu-west-2")
            self.initialised = True

    def get_table(self, table_name):
        try:
            return self.dynamodb.Table(table_name)
        except ClientError as e:
            logger.error(str(e), {"Result": "Unable to connect to DB"})
            raise e

    def query_with_requested_fields(
        self,
        table_name,
        index_name,
        search_key,
        search_condition: str,
        requested_fields: list[str] = None,
        query_filter: Attr | ConditionBase = None,
    ):
        try:
            table = self.get_table(table_name)

            if requested_fields is None or len(requested_fields) == 0:
                logger.error("Unable to query DynamoDB with empty requested fields")
                raise DynamoServiceException(
                    "Unable to query DynamoDB with empty requested fields"
                )

            projection_expression = ",".join(requested_fields)

            if not query_filter:
                results = table.query(
                    IndexName=index_name,
                    KeyConditionExpression=Key(search_key).eq(search_condition),
                    ProjectionExpression=projection_expression,
                )
            else:
                results = table.query(
                    IndexName=index_name,
                    KeyConditionExpression=Key(search_key).eq(search_condition),
                    FilterExpression=query_filter,
                    ProjectionExpression=projection_expression,
                )

            if results is None or "Items" not in results:
                logger.error(f"Unusable results in DynamoDB: {results!r}")
                raise DynamoServiceException("Unrecognised response from DynamoDB")

            return results
        except ClientError as e:
            logger.error(str(e), {"Result": f"Unable to query table: {table_name}"})
            raise e

    def query_all_fields(self, table_name: str, search_key: str, search_condition: str):
        """
        Allow querying dynamodb table without explicitly defining the fields to retrieve.
        """
        try:
            table = self.get_table(table_name)
            results = table.query(
                KeyConditionExpression=Key(search_key).eq(search_condition)
            )
            if results is None or "Items" not in results:
                logger.error(f"Unusable results in DynamoDB: {results!r}")
                raise DynamoServiceException("Unrecognised response from DynamoDB")
            return results
        except ClientError as e:
            logger.error(str(e), {"Result": f"Unable to query table: {table_name}"})
            raise e

    def create_item(self, table_name, item):
        try:
            table = self.get_table(table_name)
            logger.info(f"Writing item to table: {table_name}")
            table.put_item(Item=item)
        except ClientError as e:
            logger.error(
                str(e), {"Result": f"Unable to write item to table: {table_name}"}
            )
            raise e

    def update_item(self, table_name: str, key: str, updated_fields: dict):
        table = self.get_table(table_name)

        updated_field_names = list(updated_fields.keys())

        update_expression = create_update_expression(updated_field_names)
        _, expression_attribute_names = create_expressions(updated_field_names)
        expression_attribute_values = create_expression_attribute_values(updated_fields)

        table.update_item(
            Key={"ID": key},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
        )

    def remove_attribute_from_item(self, table_name: str, key: str, attribute: str):
        table = self.get_table(table_name)

        table.update_item(
            Key={"ID": key},
            AttributeUpdates={attribute: {"Action": "DELETE"}},
        )

    def delete_item(self, table_name: str, key: dict):
        try:
            table = self.get_table(table_name)
            table.delete_item(Key=key)
            logger.info(f"Deleting item in table: {table_name}")
        except ClientError as e:
            logger.error(
                str(e), {"Result": f"Unable to delete item in table: {table_name}"}
            )
            raise e

    def scan_table(
        self,
        table_name: str,
        exclusive_start_key: dict = None,
        filter_expression: str = None,
    ):
        try:
            table = self.get_table(table_name)
            if not filter_expression and not exclusive_start_key:
                return table.scan()
            if filter_expression is None:
                return table.scan(ExclusiveStartKey=exclusive_start_key)
            if exclusive_start_key is None:
                return table.scan(FilterExpression=filter_expression)
            return table.scan(
                FilterExpression=filter_expression,
                ExclusiveStartKey=exclusive_start_key,
            )
        except ClientError as e:
            logger.error(str(e), {"Result": f"Unable to scan table: {table_name}"})
            raise e

    def scan_whole_table(
        self,
        table_name: str,
        project_expression: Optional[str] = None,
        filter_expression: Optional[str] = None,
    ) -> list[dict]:
        try:
            table = self.get_table(table_name)
            scan_arguments = {}
            if project_expression:
                scan_arguments["ProjectionExpression"] = project_expression
            if filter_expression:
                scan_arguments["FilterExpression"] = filter_expression

            paginated_result = table.scan(**scan_arguments)
            dynamodb_scan_result = paginated_result.get("Items", [])
            while "LastEvaluatedKey" in paginated_result:
                start_key_for_next_page = paginated_result["LastEvaluatedKey"]
                paginated_result = table.scan(
                    **scan_arguments,
                    ExclusiveStartKey=start_key_for_next_page,
                )
                dynamodb_scan_result += paginated_result["Items"]
            return dynamodb_scan_result

        except ClientError as e:
            logger.error(str(e), {"Result": f"Unable to scan table: {table_name}"})
            raise e

    def batch_writing(self, table_name: str, item_list: list[dict]):
        try:
            table = self.get_table(table_name)
            logger.info(f"Writing item to table: {table_name}")
            with table.batch_writer() as batch:
                for item in item_list:
                    batch.put_item(Item=item)
        except ClientError as e:
            logger.error(
                str(e), {"Result": f"Unable to write item to table: {table_name}"}
            )
            raise e
