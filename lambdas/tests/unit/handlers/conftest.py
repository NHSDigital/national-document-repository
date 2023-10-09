from dataclasses import dataclass

import pytest

from lambdas.enums.supported_document_types import SupportedDocumentTypes


@pytest.fixture
def valid_id_event():
    api_gateway_proxy_event = {
        "queryStringParameters": {"patientId": "9000000009",
                                  "docType": SupportedDocumentTypes.list_names()},
    }
    return api_gateway_proxy_event


@pytest.fixture
def invalid_id_event():
    api_gateway_proxy_event = {
        "queryStringParameters": {"patientId": "900000000900"},
    }
    return api_gateway_proxy_event


@pytest.fixture
def missing_id_event():
    api_gateway_proxy_event = {
        "queryStringParameters": {"invalid": ""},
    }
    return api_gateway_proxy_event


@pytest.fixture
def context():
    @dataclass
    class LambdaContext:
        function_name: str = "test"
        aws_request_id: str = "88888888-4444-4444-4444-121212121212"
        invoked_function_arn: str = (
            "arn:aws:lambda:eu-west-1:123456789101:function:test"
        )

    return LambdaContext()
