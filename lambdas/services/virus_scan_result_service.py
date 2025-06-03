import json
import os

import requests
from botocore.exceptions import ClientError
from enums.lambda_error import LambdaError
from enums.pds_ssm_parameters import SSMParameter
from enums.supported_document_types import SupportedDocumentTypes
from enums.virus_scan_result import VirusScanResult
from requests.models import HTTPError
from services.base.dynamo_service import DynamoDBService
from services.base.ssm_service import SSMService
from utils.audit_logging_setup import LoggingService
from utils.lambda_exceptions import VirusScanResultException

logger = LoggingService(__name__)

FAIL_SCAN = "Virus scan result failed"
SCAN_ENDPOINT = "/api/Scan/Existing"
TOKEN_ENDPOINT = "/api/Token"


class VirusScanService:
    def __init__(self):
        self.staging_s3_bucket_name = os.getenv("STAGING_STORE_BUCKET_NAME")
        self.lg_table_name = os.getenv("LLOYD_GEORGE_DYNAMODB_NAME")
        self.arf_table_name = os.getenv("DOCUMENT_STORE_DYNAMODB_NAME")
        self.ssm_service = SSMService()
        self.dynamo_service = DynamoDBService()
        self.username = ""
        self.password = ""
        self.base_url = ""
        self.access_token = ""

    def scan_file(self, file_ref):
        try:
            if not self.base_url:
                self.get_ssm_parameters_for_request_access_token()

            result = self.request_virus_scan(file_ref, retry_on_expired=True)

            self.update_dynamo_table(file_ref, result)

            if result == VirusScanResult.CLEAN:
                logger.info(
                    "Virus scan request succeeded",
                    {"Result": "Virus scan request succeeded"},
                )
                return
            else:
                logger.info(
                    "File is not clean",
                    {"Result": FAIL_SCAN},
                )
                raise VirusScanResultException(400, LambdaError.VirusScanUnclean)
        except ClientError as e:
            logger.error(
                f"{LambdaError.VirusScanAWSFailure.to_str()}: {str(e)}",
                {"Result": FAIL_SCAN},
            )
            raise VirusScanResultException(500, LambdaError.VirusScanAWSFailure)

    def request_virus_scan(self, file_ref: str, retry_on_expired: bool):
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.access_token,
            }
            scan_url = self.base_url + SCAN_ENDPOINT
            json_data_request = {
                "container": self.staging_s3_bucket_name,
                "objectPath": file_ref,
            }
            logger.info(f"Json data request: {json_data_request}")

            response = requests.post(
                url=scan_url, data=json.dumps(json_data_request), headers=headers
            )
            if response.status_code == 401 and retry_on_expired:
                self.get_new_access_token()
                return self.request_virus_scan(file_ref, retry_on_expired=False)
            response.raise_for_status()

            parsed = response.json()
            return parsed["result"]

        except HTTPError:
            logger.info(
                "Virus scan request failed",
                {"Result": FAIL_SCAN},
            )
            raise VirusScanResultException(400, LambdaError.VirusScanTokenRequest)

    def get_new_access_token(self):
        try:
            json_login = json.dumps(
                {"username": self.username, "password": self.password}
            )
            token_url = self.base_url + TOKEN_ENDPOINT

            response = requests.post(
                url=token_url,
                headers={"Content-type": "application/json"},
                data=json_login,
            )

            response.raise_for_status()
            new_access_token = response.json()["accessToken"]

            self.update_ssm_access_token(new_access_token)
            self.access_token = new_access_token
        except (HTTPError, KeyError, TypeError) as e:
            logger.error(
                f"{LambdaError.VirusScanNoToken.to_str()}: {str(e)}",
                {"Result": FAIL_SCAN},
            )
            raise VirusScanResultException(500, LambdaError.VirusScanTokenRequest)

    def update_ssm_access_token(self, access_token):
        parameter_key = SSMParameter.VIRUS_API_ACCESS_TOKEN.value
        self.ssm_service.update_ssm_parameter(
            parameter_key=parameter_key,
            parameter_value=access_token,
            parameter_type="SecureString",
        )

    def get_ssm_parameters_for_request_access_token(self):
        access_token_key = SSMParameter.VIRUS_API_ACCESS_TOKEN.value
        username_key = SSMParameter.VIRUS_API_USER.value
        password_key = SSMParameter.VIRUS_API_PASSWORD.value
        url_key = SSMParameter.VIRUS_API_BASE_URL.value

        parameters = [username_key, password_key, url_key, access_token_key]

        ssm_response = self.ssm_service.get_ssm_parameters(
            parameters, with_decryption=True
        )
        self.username = ssm_response[username_key]
        self.password = ssm_response[password_key]
        self.base_url = ssm_response[url_key]
        self.access_token = ssm_response[access_token_key]

    def update_dynamo_table(self, file_ref: str, scan_result: VirusScanResult):
        table_name, key = self.get_dynamo_info(file_ref)
        logger.info("Updating dynamo db table")
        updated_fields: dict[str] = {"VirusScannerResult": scan_result}
        if scan_result == VirusScanResult.INFECTED:
            updated_fields["DocStatus"] = "failed"

        self.dynamo_service.update_item(
            table_name=table_name,
            key_pair={"ID": key},
            updated_fields=updated_fields,
        )

    def get_dynamo_info(self, file_ref: str):
        doc_type = file_ref.split("/")[1].upper()
        file_id = file_ref.split("/")[3]

        match doc_type:
            case SupportedDocumentTypes.ARF.value:
                return self.arf_table_name, file_id
            case SupportedDocumentTypes.LG.value:
                return self.lg_table_name, file_id
