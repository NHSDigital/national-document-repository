import json
import uuid
from time import time

import boto3
import jwt
import requests
from models.pds_models import Patient, PatientDetails
from requests.models import Response
from utils.exceptions import (InvalidResourceIdException,
                              PatientNotFoundException, PdsErrorException)
from utils.utilities import validate_id


class PdsApiService:
    def fetch_patient_details(self, nhs_number: str) -> PatientDetails:
        validate_id(nhs_number)

        response = self.fake_pds_request(nhs_number)

        return self.handle_response(response, nhs_number)

    def handle_response(self, response: Response, nhs_number: str) -> PatientDetails:
        if response.status_code == 200:
            patient = Patient.model_validate(response.content)
            patient_details = patient.get_patient_details(nhs_number)
            return patient_details

        if response.status_code == 404:
            raise PatientNotFoundException(
                "Patient does not exist for given NHS number"
            )

        if response.status_code == 400:
            raise InvalidResourceIdException("Invalid NHS number")

        raise PdsErrorException("Error when requesting patient from PDS")

    def pds_request(self, nshNumber: str) -> Response:
        kid = self.get_ssm_parameter("/prs/dev/user-input/pds-fhir-kid")
        key = self.get_ssm_parameter("/prs/dev/user-input/pds-fhir-private-key")
        endpoint = self.get_ssm_parameter("/prs/dev/user-input/pds-fhir-endpoint")
        payload = {
            "iss": key,
            "sub": key,
            "aud": endpoint,
            "jti": str(uuid.uuid4()),
            "exp": int(time()) + 300
        }
        token = self.encode_token(payload, key=key, additional_headers={"kid": kid})



    def fake_pds_request(self, nhsNumber: str) -> Response:
        mock_pds_results: list[dict] = []

        try:
            with open("services/mock_data/pds_patient.json") as f:
                mock_pds_results.append(json.load(f))

            with open("services/mock_data/pds_patient_restricted.json") as f:
                mock_pds_results.append(json.load(f))

        except FileNotFoundError:
            raise PdsErrorException("Error when requesting patient from PDS")

        pds_patient: dict = {}

        for result in mock_pds_results:
            for k, v in result.items():
                if v == nhsNumber:
                    pds_patient = result.copy()

        response = Response()

        if bool(pds_patient):
            response.status_code = 200
            response._content = pds_patient
        else:
            response.status_code = 404

        return response

    def get_ssm_parameter(self, key):
        client = boto3.client("ssm", region_name="eu-west-2")
        ssm_response = client.get_parameter(Name=key, WithDecryption=True)
        return ssm_response["Parameter"]["Value"]

    def encode_token(self, token_content, key, additional_headers ):
        return jwt.encode(token_content, key, algorithm="RS512", headers=additional_headers)

    def get_access_token(self, endpoint, token):
        access_token_headers = {
            "content-type": "application/x-www-form-urlencoded"
        }
        access_token_data = {
            "grant_type" : "client_credentials",
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion ": token
        }
        response = requests.post(url=endpoint, headers=access_token_headers, data=json.dumps(access_token_data))
        response.raise_for_status()
        return response.json()['access_token']


