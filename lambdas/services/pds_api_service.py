import json
import logging
import uuid
import time

import jwt
import requests
from botocore.exceptions import ClientError
from models.pds_models import Patient, PatientDetails
from requests.models import Response, HTTPError
from utils.exceptions import (
    InvalidResourceIdException,
    PatientNotFoundException,
    PdsErrorException,
)
from utils.utilities import validate_id

from enums.pds_ssm_parameters import SSMParameter

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class PdsApiService:
    def __init__(self, ssm_service):
        self.ssm_service = ssm_service

    def fetch_patient_details(
        self,
        nhs_number: str,
    ) -> PatientDetails:
        try:
            validate_id(nhs_number)
            response = self.pds_request(nhs_number, retry_on_expired=True)
            return self.handle_response(response, nhs_number)
        except ClientError as e:
            logger.error(f"Error when getting ssm parameters {e}")
            raise PdsErrorException("Failed to preform patient search")

    def handle_response(self, response: Response, nhs_number: str) -> PatientDetails:
        if response.status_code == 200:
            patient = Patient.model_validate(response.json())
            patient_details = patient.get_patient_details(nhs_number)
            return patient_details

        if response.status_code == 404:
            raise PatientNotFoundException(
                "Patient does not exist for given NHS number"
            )

        if response.status_code == 400:
            raise InvalidResourceIdException("Invalid NHS number")

        raise PdsErrorException("Error when requesting patient from PDS")

    def pds_request(self, nshNumber: str, retry_on_expired: bool):
        endpoint, access_token_response = self.get_parameters_for_pds_api_request()
        access_token_response = json.loads(access_token_response)
        access_token = access_token_response["access_token"]
        access_token_expiration = int(access_token_response["expires_in"]) + int(
            access_token_response["issued_at"]
        )
        time_safety_margin_seconds = 10
        if time.time() - access_token_expiration < time_safety_margin_seconds:
            access_token = self.get_new_access_token()

        x_request_id = str(uuid.uuid4())

        authorization_header = {
            "Authorization": f"Bearer {access_token}",
            "X-Request-ID": x_request_id,
        }

        url_endpoint = endpoint + "Patient/" + nshNumber
        pds_response = requests.get(url=url_endpoint, headers=authorization_header)

        if pds_response.status_code == 401 & retry_on_expired:
            return self.pds_request(nshNumber, retry_on_expired=False)
        return pds_response

    def get_new_access_token(self):
        try:
            access_token_ssm_parameter = self.get_parameters_for_new_access_token()
            jwt_token = self.create_jwt_token_for_new_access_token_request(
                access_token_ssm_parameter
            )
            nhs_oauth_endpoint = access_token_ssm_parameter[
                SSMParameter.NHS_OAUTH_ENDPOINT
            ]
            nhs_oauth_response = self.request_new_access_token(
                jwt_token, nhs_oauth_endpoint
            )
            nhs_oauth_response.raise_for_status()
            token_access_response = nhs_oauth_response.json()
            self.update_access_token_ssm(json.dumps(token_access_response))
        except HTTPError as e:
            logger.error(f"Issue while creating new access token: {e.response}")
            raise PdsErrorException("Error accessing PDS API")
        return token_access_response["access_token"]

    def get_parameters_for_new_access_token(self):
        parameters = [
            SSMParameter.NHS_OAUTH_ENDPOINT,
            SSMParameter.PDS_KID,
            SSMParameter.NHS_OAUTH_KEY,
            SSMParameter.PDS_API_KEY,
        ]
        return self.ssm_service.get_ssm_parameters(parameters, with_decryption=True)

    def update_access_token_ssm(self, parameter_value: str):
        parameter_key = SSMParameter.PDS_API_ACCESS_TOKEN
        self.ssm_service.update_ssm_parameter(
            parameter_key=parameter_key,
            parameter_value=parameter_value,
            parameter_type="SecureString",
        )

    def get_parameters_for_pds_api_request(self):
        parameters = [
            SSMParameter.PDS_API_ENDPOINT,
            SSMParameter.PDS_API_ACCESS_TOKEN,
        ]
        ssm_response = self.ssm_service.get_ssm_parameters(
            parameters_keys=parameters, with_decryption=True
        )
        return ssm_response[parameters[0]], ssm_response[parameters[1]]

    def create_jwt_token_for_new_access_token_request(
        self, access_token_ssm_parameters
    ):
        nhs_oauth_endpoint = access_token_ssm_parameters[
            SSMParameter.NHS_OAUTH_ENDPOINT
        ]
        kid = access_token_ssm_parameters[SSMParameter.PDS_KID]
        nhs_key = access_token_ssm_parameters[SSMParameter.NHS_OAUTH_KEY]
        pds_key = access_token_ssm_parameters[SSMParameter.PDS_API_KEY]
        payload = {
            "iss": nhs_key,
            "sub": nhs_key,
            "aud": nhs_oauth_endpoint,
            "jti": str(uuid.uuid4()),
            "exp": int(time.time()) + 300,
        }
        return jwt.encode(payload, pds_key, algorithm="RS512", headers={"kid": kid})

    def request_new_access_token(self, jwt_token, nhs_oauth_endpoint):
        access_token_headers = {"content-type": "application/x-www-form-urlencoded"}
        access_token_data = {
            "grant_type": "client_credentials",
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": jwt_token,
        }
        return requests.post(
            url=nhs_oauth_endpoint, headers=access_token_headers, data=access_token_data
        )
