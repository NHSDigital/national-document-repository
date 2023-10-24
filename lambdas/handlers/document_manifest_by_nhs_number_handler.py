import logging
import os

from botocore.exceptions import ClientError
from pydantic import ValidationError
from services.document_manifest_service import DocumentManifestService
from services.document_service import DocumentService
from utils.decorators.ensure_env_var import ensure_environment_variables
from utils.decorators.validate_document_type import validate_document_type
from utils.decorators.validate_patient_id import validate_patient_id
from utils.exceptions import DynamoDbException, ManifestDownloadException
from utils.lambda_response import ApiGatewayResponse

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@validate_patient_id
@validate_document_type
@ensure_environment_variables(
    names=[
        "DOCUMENT_STORE_DYNAMODB_NAME",
        "LLOYD_GEORGE_DYNAMODB_NAME",
        "ZIPPED_STORE_BUCKET_NAME",
        "ZIPPED_STORE_DYNAMODB_NAME",
    ]
)
def lambda_handler(event, context):
    logger.info("Starting document manifest process")

    try:
        nhs_number = event["queryStringParameters"]["patientId"]
        doc_type = event["queryStringParameters"]["docType"]

        zip_output_bucket = os.environ["ZIPPED_STORE_BUCKET_NAME"]
        zip_trace_table_name = os.environ["ZIPPED_STORE_DYNAMODB_NAME"]
        # zip_trace_ttl = os.environ["DOCUMENT_ZIP_TRACE_TTL_IN_DAYS"]

        dynamo_service = DocumentService()
        documents = dynamo_service.retrieve_all_document_references(
            nhs_number, doc_type
        )

        if not documents:
            return ApiGatewayResponse(
                204, "No documents found for given NHS number and document type", "GET"
            ).create_api_gateway_response()

        logger.info("Starting document manifest process")
        document_manifest_service = DocumentManifestService(
            nhs_number=nhs_number,
            documents=documents,
            zip_output_bucket=zip_output_bucket,
            zip_trace_table=zip_trace_table_name,
        )

        response = document_manifest_service.create_document_manifest_presigned_url()

        return ApiGatewayResponse(200, response, "GET").create_api_gateway_response()

    except ValidationError as e:
        logger.info(e)
        return ApiGatewayResponse(
            500,
            "Failed to parse document reference from from DynamoDb response",
            "GET",
        ).create_api_gateway_response()
    except ManifestDownloadException as e:
        return ApiGatewayResponse(
            500,
            f"{str(e)}",
            "GET",
        ).create_api_gateway_response()
    except DynamoDbException as e:
        return ApiGatewayResponse(
            500,
            f"An error occurred when searching for available documents: {str(e)}",
            "GET",
        ).create_api_gateway_response()
    except ClientError as e:
        logger.error(str(e))
        response = ApiGatewayResponse(
            500, "An error occurred when creating document manifest", "GET"
        ).create_api_gateway_response()
        return response
