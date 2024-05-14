import os
import time

import boto3
from models.cloudwatch_logs_query import CloudwatchLogsQueryParams


class CloudwatchLogsQueryService:
    def __init__(self):
        self.logs_client = boto3.client("logs")
        self.workspace = os.environ["WORKSPACE"]

    def query_logs(
        self, query_params: CloudwatchLogsQueryParams, start_time: int, end_time: int
    ) -> list[dict]:
        response = self.logs_client.start_query(
            logGroupName=f"/aws/lambda/{self.workspace}_{query_params.lambda_name}",
            startTime=start_time,
            endTime=end_time,
            queryString=query_params.query_string,
        )
        query_id = response["queryId"]

        raw_query_result = self.poll_query_result(query_id)
        query_result = [
            {column["field"]: column["value"] for column in row}
            for row in raw_query_result
        ]
        return query_result

    def poll_query_result(self, query_id: str, max_retries=20) -> list[list]:
        for _ in range(max_retries):
            response = self.logs_client.get_query_results(queryId=query_id)
            if response["status"] == "Complete":
                return response["results"]
            time.sleep(1)

        # TODO: replace this with a lambda error
        raise RuntimeError(
            f"Failed to get query result within max retries of {max_retries} times"
        )
