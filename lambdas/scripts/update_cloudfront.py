import os
import sys
import time

import boto3
from botocore.exceptions import ClientError

distribution_id = os.getenv("DISTRIBUTION_ID")
lambda_name = os.getenv("LAMBDA_NAME")
aws_region = os.getenv("AWS_REGION")
aws_account_id = os.getenv("AWS_ACCOUNT_ID")

cloudfront_client = boto3.client("cloudfront", region_name=aws_region)
lambda_client = boto3.client("lambda", region_name=aws_region)
sts_client = boto3.client("sts", region_name=aws_region)


def get_aws_account_id():
    """Retrieve the AWS account ID using STS."""
    try:
        response = sts_client.get_caller_identity()
        account_id = response["Account"]
        print("Retrieved AWS Account ID: ***")
        return account_id
    except ClientError as e:
        print(f"Client error: {e.response['Error']['Message']}")
        sys.exit(1)


def propagate_lambda_update(retry_count=3, seconds_delay=5):
    time.sleep(seconds_delay)

    for attempt in range(1, retry_count + 1):
        print(f"Attempt {attempt}: Propagating lambda update...")
        response = lambda_client.get_function_configuration(FunctionName=lambda_name)
        if (
            response.get("State") == "Active"
            and response.get("LastUpdateStatus") == "Successful"
        ):
            print("Edge Lambda propagated update successfully...")
            return

        if attempt < retry_count:
            print("Edge Lambda has not finished propagating update, retrying...")
            time.sleep(seconds_delay)

    print("Exceeded retries. Failed to verify Edge Lambda state.")
    sys.exit(1)


def get_latest_lambda_version(function_name):
    """Get the latest version of the Lambda function."""
    try:
        response = lambda_client.get_function_configuration(FunctionName=function_name)
    except ClientError as ex:
        print(f"Client error: {ex.response['Error']['Message']}")
        sys.exit(2)
    try:
        version = response["Version"]
        if not version:
            print(f"No published versions found for Lambda function: {function_name}")
            sys.exit(3)
        return version
    except ValueError as ex:
        print(f"Error while processing versions: {ex}")
        sys.exit(4)
    except KeyError:
        print("Unexpected response format: missing 'Version' key.")
        sys.exit(5)


def check_lambda_status(
    function_name, version, retry_limit_seconds=60, retry_interval=15
):
    """Check the status of a Lambda function, retrying for up to 1 minute."""
    total_time = 0
    while total_time < retry_limit_seconds:
        try:
            response = lambda_client.get_function(
                FunctionName=function_name, Qualifier=version
            )
            status = response["Configuration"]["State"]
            print(f"Lambda function status: {status}")
            if status == "Active":
                print("Lambda function is active.")
                return
        except ClientError as e:
            print(f"Error checking Lambda status: {e.response['Error']['Message']}")
            sys.exit(6)

        print(
            f"Lambda function not yet active. Retrying in {retry_interval} seconds..."
        )
        time.sleep(retry_interval)
        total_time += retry_interval

    print(
        f"Exceeded retry limit of {retry_limit_seconds} seconds. Lambda function is still not active."
    )
    sys.exit(7)


def invalidate_cloudfront_cache(distribution_id):
    try:
        invalidation_response = cloudfront_client.create_invalidation(
            DistributionId=distribution_id,
            InvalidationBatch={
                "Paths": {"Quantity": 1, "Items": ["/*"]},
                "CallerReference": str(time.time()),
            },
        )
        print(
            f"Cache invalidation started: {invalidation_response['Invalidation']['Id']}"
        )
    except ClientError as e:
        print(f"Error invalidating cache: {e.response['Error']['Message']}")
        sys.exit(12)


def update_cloudfront_lambda_association(distribution_id: str, lambda_arn: str):
    """Update the CloudFront distribution with the new Lambda function version."""
    print(
        f"Updating CloudFront distribution: {distribution_id} with Lambda function ARN: {lambda_arn}"
    )
    try:
        response = cloudfront_client.get_distribution_config(Id=distribution_id)
        distribution_config = response["DistributionConfig"]
        etag = response["ETag"]

        lambda_associations = distribution_config["DefaultCacheBehavior"].get(
            "LambdaFunctionAssociations", {}
        )
        items = lambda_associations.get("Items", [])

        if not items:
            print(
                f"Error for distribution '{distribution_id}'. Lambda associations not found. "
                "Manually clean any duplicated and unused distributions and try again."
            )
            sys.exit(8)

        for item in items:
            if item["EventType"] in [
                "viewer-request",
                "viewer-response",
                "origin-request",
                "origin-response",
            ]:
                print(f"Updating LambdaFunctionARN for event type {item['EventType']}")
                item["LambdaFunctionARN"] = lambda_arn

        cloudfront_client.update_distribution(
            Id=distribution_id, DistributionConfig=distribution_config, IfMatch=etag
        )
        print(
            f"Updated CloudFront distribution '{distribution_id}' to use Lambda '{lambda_arn}'."
        )

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "NoSuchDistribution":
            print(f"Distribution '{distribution_id}' does not exist. Skipping update.")
            sys.exit(9)
        else:
            print(f"Error updating distribution: {str(e)}")
            sys.exit(10)


if __name__ == "__main__":
    try:
        if not aws_account_id:
            aws_account_id = get_aws_account_id()

        propagate_lambda_update()
        lambda_version = get_latest_lambda_version(lambda_name)
        lambda_arn = f"arn:aws:lambda:{aws_region}:{aws_account_id}:function:{lambda_name}:{lambda_version}"
        print(f"Lambda ARN: {lambda_arn}")

        check_lambda_status(lambda_name, lambda_version)
        update_cloudfront_lambda_association(distribution_id, lambda_arn)
        invalidate_cloudfront_cache(distribution_id)
        print("Lambda@Edge update process completed successfully.")

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(11)
