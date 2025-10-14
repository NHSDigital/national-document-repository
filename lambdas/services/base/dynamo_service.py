import time
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

    def query_table_by_index(
        self,
        table_name,
        index_name,
        search_key,
        search_condition: str,
        requested_fields: list[str] = None,
        query_filter: Attr | ConditionBase = None,
        exclusive_start_key: dict = None,
    ):
        try:
            table = self.get_table(table_name)

            query_params = {
                "KeyConditionExpression": Key(search_key).eq(search_condition),
            }

            if index_name:
                query_params["IndexName"] = index_name

            if requested_fields:
                projection_expression = ",".join(requested_fields)
                query_params["ProjectionExpression"] = projection_expression

            if query_filter:
                query_params["FilterExpression"] = query_filter
            if exclusive_start_key:
                query_params["ExclusiveStartKey"] = exclusive_start_key

            results = table.query(**query_params)

            if results is None or "Items" not in results:
                logger.error(f"Unusable results in DynamoDB: {results!r}")
                raise DynamoServiceException("Unrecognised response from DynamoDB")

            return results
        except ClientError as e:
            logger.error(str(e), {"Result": f"Unable to query table: {table_name}"})
            raise e

    def query_with_pagination(
        self, table_name: str, search_key: str, search_condition: str
    ):

        try:
            table = self.get_table(table_name)
            results = table.query(
                KeyConditionExpression=Key(search_key).eq(search_condition)
            )
            if results is None or "Items" not in results:
                logger.error(f"Unusable results in DynamoDB: {results!r}")
                raise DynamoServiceException("Unrecognised response from DynamoDB")

            dynamodb_scan_result = results["Items"]

            while "LastEvaluatedKey" in results:
                start_key_for_next_page = results["LastEvaluatedKey"]
                results = table.query(
                    KeyConditionExpression=Key(search_key).eq(search_condition),
                    ExclusiveStartKey=start_key_for_next_page,
                )
                dynamodb_scan_result.extend(results["Items"])
            return dynamodb_scan_result

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

    def update_item(
        self,
        table_name: str,
        key_pair: dict[str, str],
        updated_fields: dict,
        condition_expression: str = None,
        expression_attribute_values: dict = None,
    ):
        table = self.get_table(table_name)
        updated_field_names = list(updated_fields.keys())
        update_expression = create_update_expression(updated_field_names)
        _, expression_attribute_names = create_expressions(updated_field_names)

        generated_expression_attribute_values = create_expression_attribute_values(
            updated_fields
        )

        if expression_attribute_values:
            generated_expression_attribute_values.update(expression_attribute_values)

        update_item_args = {
            "Key": key_pair,
            "UpdateExpression": update_expression,
            "ExpressionAttributeNames": expression_attribute_names,
            "ExpressionAttributeValues": generated_expression_attribute_values,
            "ReturnValues": "ALL_NEW",
        }

        if condition_expression:
            update_item_args["ConditionExpression"] = condition_expression

        return table.update_item(**update_item_args)

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

    def batch_get_items(self, table_name: str, key_list: list[str]):
        if len(key_list) > 100:
            return DynamoServiceException("Cannot fetch more than 100 items at a time")

        keys_to_get = [{"ID": item_id} for item_id in key_list]
        request_items = {table_name: {"Keys": keys_to_get}}

        all_fetched_items = []
        retries = 0
        max_retries = 3

        while request_items[table_name]["Keys"] and retries < max_retries:
            try:
                response = self.dynamodb.batch_get_item(RequestItems=request_items)

                table_responses = response.get("Responses", {}).get(table_name, [])
                all_fetched_items.extend(table_responses)

                unprocessed_keys = response.get("UnprocessedKeys", {})
                if table_name in unprocessed_keys:
                    logger.info(
                        f"Retrying {len(unprocessed_keys[table_name]['Keys'])} unprocessed keys..."
                    )
                    request_items = unprocessed_keys
                    retries += 1
                    time.sleep((2**retries) * 0.1)
                else:
                    break

            except Exception as e:
                print(f"An error occurred during batch_get_item: {e}")
                raise e
        return all_fetched_items

    def get_item(self, table_name: str, key: dict):
        try:
            table = self.get_table(table_name)
            logger.info(f"Retrieving item from table: {table_name}")
            return table.get_item(Key=key)
        except ClientError as e:
            logger.error(
                str(e), {"Result": f"Unable to retrieve item from table: {table_name}"}
            )
            raise e
