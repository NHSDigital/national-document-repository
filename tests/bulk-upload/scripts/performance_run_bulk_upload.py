import argparse
import json
import sys

import boto3


def invoke_lambda(lambda_name, payload={}):
    client = boto3.client("lambda")
    response = client.invoke(
        FunctionName=lambda_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )
    return json.loads(response["Payload"].read())


def update_lambda_environment_variables(lambda_name, new_variables):
    session = boto3.Session()
    lambda_client = session.client("lambda")

    response = lambda_client.get_function_configuration(FunctionName=lambda_name)
    current_environment = response["Environment"]["Variables"]

    updated_environment = current_environment.copy()
    updated_environment.update(new_variables)

    lambda_client.update_function_configuration(
        FunctionName=lambda_name, Environment={"Variables": updated_environment}
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Bulk Upload Script")

    parser.add_argument(
        "--environment",
        help="The name of the environment",
    )
    parser.add_argument(
        "--disable-pds-stub",
        action="store_true",
        help="Disable the PDS Stub",
    )
    parser.add_argument(
        "--start-bulk-upload",
        action="store_true",
        help="Start the Bulk Upload",
    )

    parser.add_argument(
        "--use-bulk-upload-metadata-processor",
        action="store_true",
        help="Use BulkUploadMetadataProcessor Lambda",
    )

    args = parser.parse_args()

    if not args.environment:
        args.environment = input("Please enter the name of the environment: ")

    bulk_upload_lambda_name = f"{args.environment}_BulkUploadLambda"
    bulk_upload_metadata_lambda_name = f"{args.environment}_BulkUploadMetadataLambda"
    search_lambda_name = f"{args.environment}_SearchPatientDetailsLambda"

    if args.use_bulk_upload_metadata_processor:
        bulk_upload_metadata_lambda_name = f"{args.environment}_BulkUploadMetadataProcessor"

    if args.disable_pds_stub or (
        sys.stdin.isatty()
        and input("Would you like to disable the FHIR Stub: ").lower() == "y"
    ):
        new_variables = {"PDS_FHIR_IS_STUBBED": "false"}
        update_lambda_environment_variables(bulk_upload_lambda_name, new_variables)
        update_lambda_environment_variables(search_lambda_name, new_variables)
    else:
        new_variables = {"PDS_FHIR_IS_STUBBED": "true", "BYPASS_PDS": "true"}
        update_lambda_environment_variables(bulk_upload_lambda_name, new_variables)
        update_lambda_environment_variables(search_lambda_name, new_variables)
    if args.start_bulk_upload or input(
        "Would you like to start the Bulk Upload Process:"
    ):
        invoke_lambda(bulk_upload_metadata_lambda_name)