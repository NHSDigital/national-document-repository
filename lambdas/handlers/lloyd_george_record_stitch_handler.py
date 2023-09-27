import os
from datetime import datetime
from io import BytesIO

import boto3
from botocore.exceptions import ClientError
from pypdf import PdfWriter

from enums.metadata_field_names import DocumentReferenceMetadataFields
from services.dynamo_service import DynamoDBService
from services.s3_service import S3Service
from utils.exceptions import InvalidResourceIdException
from utils.lambda_response import ApiGatewayResponse
from utils.order_response_by_filenames import order_response_by_filenames
from utils.utilities import validate_id


def lambda_handler(event, context):
    try:
        nhs_number = event["queryStringParameters"]["patientId"]
        validate_id(nhs_number)

        lloyd_george_table_name = os.environ["LLOYD_GEORGE_DYNAMODB_NAME"]
        lloyd_george_bucket_name = os.environ["LLOYD_GEORGE_BUCKET_NAME"]

    except InvalidResourceIdException:
        return ApiGatewayResponse(
            400, "Invalid NHS number", "GET"
        ).create_api_gateway_response()
    except KeyError as e:
        return ApiGatewayResponse(
            400, f"An error occurred due to missing key: {str(e)}", "GET"
        ).create_api_gateway_response()

    dynamo_service = DynamoDBService()
    try:
        response = dynamo_service.query_service(
            lloyd_george_table_name,
            "NhsNumberIndex",
            "NhsNumber",
            nhs_number,
            [
                DocumentReferenceMetadataFields.ID,
                DocumentReferenceMetadataFields.NHS_NUMBER,
                DocumentReferenceMetadataFields.FILE_LOCATION,
                DocumentReferenceMetadataFields.FILE_NAME
            ],
        )
        # [
        # 2of2_Lloyd_George_Record_[Joe Bloggs]_[123456789]_[25-12-2019]
        # 1of2_Lloyd_George_Record_[Joe Bloggs]_[123456789]_[25-12-2019]
        # ]

    except ClientError:
        return ApiGatewayResponse(500, f"Unable to retrieve documents for patient {nhs_number}",
                                  "GET").create_api_gateway_response()

    ordered_lg_records = order_response_by_filenames(response['Items'])

    s3_service = S3Service()

    merger = PdfWriter()

    for lg_part in ordered_lg_records:
        s3_service.download_file(lloyd_george_bucket_name, lg_part["ID"], lg_part["FileName"])
        merger.append(lg_part["FileName"])

    with BytesIO() as bytes_stream:
        merger.write(bytes_stream)
        bytes_stream.seek(0)

        s3_client = boto3.client("s3", region_name="eu-west-2")
        s3_upload_response = s3_client.put_object(Body=bytes_stream, Bucket="ndr-dev-lloyd-george-store",
                                                  Expires=datetime(2015, 9, 27), Key="alexCool.pdf")

    # Get the patient's list of docs from the NDR LG Dynamo table
    # Download them all in order, their filenames should impose an order
    # File names are stored in Dynamo which is why we need it first
    # Stitch them together in order
    # upload them to S3 - set a TTL on the bucket
    # return pre-signed URL to download and send it to the UI using api response

    pass
