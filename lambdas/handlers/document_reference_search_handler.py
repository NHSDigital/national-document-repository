import json
import logging
import os

from botocore.exceptions import ClientError
from enums.metadata_field_names import DocumentReferenceMetadataFields
from services.dynamo_service import DynamoDBService
from utils.exceptions import DynamoDbException, InvalidResourceIdException
from utils.lambda_response import ApiGatewayResponse
from utils.utilities import decapitalise_keys, validate_id

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info("Starting document reference search process")

    try:
        nhs_number = event["queryStringParameters"]["patientId"]
        validate_id(nhs_number)

        document_store_table_name = os.environ["DOCUMENT_STORE_DYNAMODB_NAME"]
        lloyd_george_table_name = os.environ["LLOYD_GEORGE_DYNAMODB_NAME"]

    except InvalidResourceIdException:
        return ApiGatewayResponse(
            400, "Invalid NHS number", "GET"
        ).create_api_gateway_response()
    except KeyError as e:
        return ApiGatewayResponse(
            400, f"An error occurred due to missing key: {str(e)}", "GET"
        ).create_api_gateway_response()

    list_of_table_names = [document_store_table_name, lloyd_george_table_name]

    dynamo_service_for_tables: dict = {
        table_name: DynamoDBService(table_name) for table_name in list_of_table_names
    }

    try:
        results = []
        for dynamo_service in dynamo_service_for_tables.values():
            response = dynamo_service.query_service(
                "NhsNumberIndex",
                "NhsNumber",
                nhs_number,
                [
                    DocumentReferenceMetadataFields.CREATED,
                    DocumentReferenceMetadataFields.FILE_NAME,
                    DocumentReferenceMetadataFields.VIRUS_SCAN_RESULT,
                ],
            )
            if response is None or ("Items" not in response):
                logger.error(f"Unrecognised response from DynamoDB: {response!r}")
                return ApiGatewayResponse(
                    500,
                    "Unrecognised response when searching for available documents",
                    "GET",
                ).create_api_gateway_response()

            results += response["Items"]

    except InvalidResourceIdException:
        return ApiGatewayResponse(
            500, "No data was requested to be returned in query", "GET"
        ).create_api_gateway_response()
    except ClientError as e:
        logger.error(f"Unable to connect to DynamoDB: {str(e)}")
        return ApiGatewayResponse(
            500, "An error occurred when searching for available documents", "GET"
        ).create_api_gateway_response()
    except DynamoDbException as e:
        logger.error(f"An error occurred when querying DynamoDB: {str(e)}")
        return ApiGatewayResponse(
            500,
            "An error occurred when searching for available documents",
            "GET",
        ).create_api_gateway_response()

    response = [decapitalise_keys(result) for result in results]

    if not results or not response:
        return ApiGatewayResponse(
            204, json.dumps([]), "GET"
        ).create_api_gateway_response()

    return ApiGatewayResponse(
        200, json.dumps(response), "GET"
    ).create_api_gateway_response()
