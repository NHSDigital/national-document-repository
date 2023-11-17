import json
import os
from unittest.mock import patch

import pytest
from handlers.search_patient_details_handler import lambda_handler
from requests.models import Response
from tests.unit.helpers.data.pds.pds_patient_response import PDS_PATIENT


@pytest.fixture
def patch_env_vars():
    env_vars = {
        "PDS_FHIR_IS_STUBBED": "1",
        "SSM_PARAM_JWT_TOKEN_PUBLIC_KEY": "mock_public_key",
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


def skip_test_lambda_handler_valid_id_returns_200(
    valid_id_event, context, mocker, patch_env_vars
):
    response = Response()
    response.status_code = 200
    response._content = json.dumps(PDS_PATIENT).encode("utf-8")

    mocker.patch("ssm_service.get_ssm_parameter")
    mocker.patch(
        "services.mock_pds_service.MockPdsApiService.pds_request",
        return_value=response,
    )

    actual = lambda_handler(valid_id_event, context)

    expected = {
        "body": '{"givenName":["Jane"],"familyName":"Smith","birthDate":"2010-10-22",'
        '"postalCode":"LS1 6AE","nhsNumber":"9000000009","superseded":false,'
        '"restricted":false,"generalPracticeOds":"","active":false}',
        "headers": {
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "application/fhir+json",
        },
        "isBase64Encoded": False,
        "statusCode": 200,
    }

    assert expected == actual


def test_lambda_handler_invalid_id_returns_400(
    invalid_id_event, context, mocker, patch_env_vars
):
    response = Response()
    response.status_code = 400

    mocker.patch(
        "services.mock_pds_service.MockPdsApiService.pds_request",
        return_value=response,
    )

    actual = lambda_handler(invalid_id_event, context)

    expected = {
        "body": "Invalid NHS number",
        "headers": {
            "Content-Type": "application/fhir+json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Strict-Transport-Security": "max-age=63072000",
        },
        "isBase64Encoded": False,
        "statusCode": 400,
    }

    assert expected == actual


def skip_test_lambda_handler_valid_id_not_in_pds_returns_404(
    valid_id_event, context, mocker, patch_env_vars
):
    response = Response()
    response.status_code = 404

    mocker.patch(
        "services.mock_pds_service.MockPdsApiService.pds_request",
        return_value=response,
    )

    actual = lambda_handler(valid_id_event, context)

    expected = {
        "body": "Patient does not exist for given NHS number",
        "headers": {
            "Content-Type": "application/fhir+json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
        },
        "isBase64Encoded": False,
        "statusCode": 404,
    }

    assert expected == actual


def test_lambda_handler_missing_id_in_query_params_returns_400(
    missing_id_event, context, mocker, patch_env_vars
):
    actual = lambda_handler(missing_id_event, context)

    expected = {
        "body": "An error occurred due to missing key: 'patientId'",
        "headers": {
            "Content-Type": "application/fhir+json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Strict-Transport-Security": "max-age=63072000",
        },
        "isBase64Encoded": False,
        "statusCode": 400,
    }

    assert expected == actual
