import json
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from unittest import mock

import pytest
from models.document_reference import DocumentReference
from models.pds_models import PatientDetails
from pydantic import ValidationError
from requests import Response

REGION_NAME = "eu-west-2"

MOCK_TABLE_NAME = "test-table"
MOCK_BUCKET = "test-s3-bucket"

MOCK_ARF_TABLE_NAME_ENV_NAME = "DOCUMENT_STORE_DYNAMODB_NAME"
MOCK_ARF_BUCKET_ENV_NAME = "DOCUMENT_STORE_BUCKET_NAME"

MOCK_LG_TABLE_NAME_ENV_NAME = "LLOYD_GEORGE_DYNAMODB_NAME"
MOCK_LG_BUCKET_ENV_NAME = "LLOYD_GEORGE_BUCKET_NAME"

MOCK_ZIP_OUTPUT_BUCKET_ENV_NAME = "ZIPPED_STORE_BUCKET_NAME"
MOCK_ZIP_TRACE_TABLE_ENV_NAME = "ZIPPED_STORE_DYNAMODB_NAME"

MOCK_LG_STAGING_STORE_BUCKET_ENV_NAME = "STAGING_STORE_BUCKET_NAME"
MOCK_LG_METADATA_SQS_QUEUE_ENV_NAME = "METADATA_SQS_QUEUE_URL"
MOCK_LG_INVALID_SQS_QUEUE_ENV_NAME = "INVALID_SQS_QUEUE_URL"
MOCK_LG_BULK_UPLOAD_DYNAMO_ENV_NAME = "BULK_UPLOAD_DYNAMODB_NAME"

MOCK_AUTH_DYNAMODB_NAME = "AUTH_DYNAMODB_NAME"
MOCK_AUTH_STATE_TABLE_NAME_ENV_NAME = "AUTH_STATE_TABLE_NAME"
MOCK_AUTH_SESSION_TABLE_NAME_ENV_NAME = "AUTH_SESSION_TABLE_NAME"
MOCK_OIDC_CALLBACK_URL_ENV_NAME = "OIDC_CALLBACK_URL"
MOCK_OIDC_ISSUER_URL_ENV_NAME = "OIDC_ISSUER_URL"
MOCK_OIDC_TOKEN_URL_ENV_NAME = "OIDC_TOKEN_URL"
MOCK_OIDC_USER_INFO_URL_ENV_NAME = "OIDC_USER_INFO_URL"
MOCK_OIDC_JWKS_URL_ENV_NAME = "OIDC_JWKS_URL"
MOCK_OIDC_CLIENT_ID_ENV_NAME = "OIDC_CLIENT_ID"
MOCK_OIDC_CLIENT_SECRET_ENV_NAME = "OIDC_CLIENT_SECRET"
MOCK_WORKSPACE_ENV_NAME = "WORKSPACE"
MOCK_JWT_PUBLIC_KEY_NAME = "SSM_PARAM_JWT_TOKEN_PUBLIC_KEY"
MOCK_FEEDBACK_SENDER_EMAIL_ENV_NAME = "FROM_EMAIL_ADDRESS"
MOCK_FEEDBACK_EMAIL_SUBJECT_ENV_NAME = "EMAIL_SUBJECT"
MOCK_EMAIL_RECIPIENT_SSM_PARAM_KEY_ENV_NAME = "EMAIL_RECIPIENT_SSM_PARAM_KEY"
MOCK_APPCONFIG_APPLICATION_ENV_NAME = "APPCONFIG_APPLICATION"
MOCK_APPCONFIG_ENVIRONMENT_ENV_NAME = "APPCONFIG_ENVIRONMENT"
MOCK_APPCONFIG_CONFIGURATION_ENV_NAME = "APPCONFIG_CONFIGURATION"
MOCK_STATISTICS_TABLE_NAME = "STATISTICS_TABLE"
MOCK_STATISTICS_REPORT_BUCKET_NAME = "STATISTICAL_REPORTS_BUCKET"

MOCK_ARF_TABLE_NAME = "test_arf_dynamoDB_table"
MOCK_LG_TABLE_NAME = "test_lg_dynamoDB_table"
MOCK_BULK_REPORT_TABLE_NAME = "test_report_dynamoDB_table"
MOCK_ARF_BUCKET = "test_arf_s3_bucket"
MOCK_LG_BUCKET = "test_lg_s3_bucket"
MOCK_ZIP_OUTPUT_BUCKET = "test_s3_output_bucket"
MOCK_ZIP_TRACE_TABLE = "test_zip_table"
MOCK_STAGING_STORE_BUCKET = "test_staging_bulk_store"
MOCK_LG_METADATA_SQS_QUEUE = "test_bulk_upload_metadata_queue"
MOCK_LG_INVALID_SQS_QUEUE = "INVALID_SQS_QUEUE_URL"
MOCK_STATISTICS_TABLE = "test_statistics_table"
MOCK_STATISTICS_REPORT_BUCKET = "test_statistics_report_bucket"

TEST_NHS_NUMBER = "9000000009"
TEST_UUID = "1234-4567-8912-HSDF-TEST"
TEST_FILE_KEY = "test_file_key"
TEST_FILE_NAME = "test.pdf"
TEST_VIRUS_SCANNER_RESULT = "not_scanned"
TEST_DOCUMENT_LOCATION = f"s3://{MOCK_BUCKET}/{TEST_FILE_KEY}"
TEST_CURRENT_GP_ODS = "Y12345"

AUTH_STATE_TABLE_NAME = "test_state_table"
AUTH_SESSION_TABLE_NAME = "test_session_table"
FAKE_URL = "https://fake-url.com"
OIDC_CALLBACK_URL = FAKE_URL
OIDC_ISSUER_URL = FAKE_URL
OIDC_TOKEN_URL = FAKE_URL
OIDC_USER_INFO_URL = FAKE_URL
OIDC_JWKS_URL = FAKE_URL
OIDC_CLIENT_ID = "client-id"
OIDC_CLIENT_SECRET = "client-secret-shhhhhh"
WORKSPACE = "dev"
JWT_PUBLIC_KEY = "mock_public_key"

SSM_PARAM_JWT_TOKEN_PUBLIC_KEY_ENV_NAME = "SSM_PARAM_JWT_TOKEN_PUBLIC_KEY"
SSM_PARAM_JWT_TOKEN_PUBLIC_KEY = "test_jwt_token_public_key"

MOCK_FEEDBACK_SENDER_EMAIL = "feedback@localhost"
MOCK_FEEDBACK_RECIPIENT_EMAIL_LIST = ["gp2gp@localhost", "test_email@localhost"]
MOCK_FEEDBACK_EMAIL_SUBJECT = "Digitised Lloyd George feedback"
MOCK_EMAIL_RECIPIENT_SSM_PARAM_KEY = "/prs/dev/user-input/feedback-recipient-email-list"

MOCK_INTERACTION_ID = "88888888-4444-4444-4444-121212121212"

MOCK_APPCONFIG_APPLICATION_ID = "A1234"
MOCK_APPCONFIG_ENVIRONMENT_ID = "B1234"
MOCK_APPCONFIG_CONFIGURATION_ID = "C1234"

MOCK_PRESIGNED_URL_ROLE_ARN_KEY = "PRESIGNED_ASSUME_ROLE"
MOCK_PRESIGNED_URL_ROLE_ARN_VALUE = "arn:aws:iam::test123"


@pytest.fixture
def set_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION_NAME)
    monkeypatch.setenv(MOCK_ARF_TABLE_NAME_ENV_NAME, MOCK_ARF_TABLE_NAME)
    monkeypatch.setenv(MOCK_ARF_BUCKET_ENV_NAME, MOCK_ARF_BUCKET)
    monkeypatch.setenv(MOCK_LG_TABLE_NAME_ENV_NAME, MOCK_LG_TABLE_NAME)
    monkeypatch.setenv(MOCK_LG_BUCKET_ENV_NAME, MOCK_LG_BUCKET)
    monkeypatch.setenv(
        "DYNAMODB_TABLE_LIST", json.dumps([MOCK_ARF_TABLE_NAME, MOCK_LG_TABLE_NAME])
    )
    monkeypatch.setenv(MOCK_ZIP_OUTPUT_BUCKET_ENV_NAME, MOCK_ZIP_OUTPUT_BUCKET)
    monkeypatch.setenv(MOCK_ZIP_TRACE_TABLE_ENV_NAME, MOCK_ZIP_TRACE_TABLE)
    monkeypatch.setenv(MOCK_LG_STAGING_STORE_BUCKET_ENV_NAME, MOCK_STAGING_STORE_BUCKET)
    monkeypatch.setenv(MOCK_LG_METADATA_SQS_QUEUE_ENV_NAME, MOCK_LG_METADATA_SQS_QUEUE)
    monkeypatch.setenv(MOCK_LG_INVALID_SQS_QUEUE_ENV_NAME, MOCK_LG_INVALID_SQS_QUEUE)
    monkeypatch.setenv(MOCK_AUTH_STATE_TABLE_NAME_ENV_NAME, AUTH_STATE_TABLE_NAME)
    monkeypatch.setenv(MOCK_AUTH_SESSION_TABLE_NAME_ENV_NAME, AUTH_SESSION_TABLE_NAME)
    monkeypatch.setenv(MOCK_OIDC_CALLBACK_URL_ENV_NAME, OIDC_CALLBACK_URL)
    monkeypatch.setenv(MOCK_OIDC_CLIENT_ID_ENV_NAME, OIDC_CLIENT_ID)
    monkeypatch.setenv(MOCK_WORKSPACE_ENV_NAME, WORKSPACE)
    monkeypatch.setenv(MOCK_LG_BULK_UPLOAD_DYNAMO_ENV_NAME, MOCK_BULK_REPORT_TABLE_NAME)
    monkeypatch.setenv(MOCK_OIDC_ISSUER_URL_ENV_NAME, OIDC_USER_INFO_URL)
    monkeypatch.setenv(MOCK_OIDC_TOKEN_URL_ENV_NAME, OIDC_TOKEN_URL)
    monkeypatch.setenv(MOCK_OIDC_USER_INFO_URL_ENV_NAME, OIDC_USER_INFO_URL)
    monkeypatch.setenv(MOCK_OIDC_JWKS_URL_ENV_NAME, OIDC_JWKS_URL)
    monkeypatch.setenv(MOCK_OIDC_CLIENT_SECRET_ENV_NAME, OIDC_CLIENT_SECRET)
    monkeypatch.setenv(MOCK_JWT_PUBLIC_KEY_NAME, JWT_PUBLIC_KEY)
    monkeypatch.setenv(
        SSM_PARAM_JWT_TOKEN_PUBLIC_KEY_ENV_NAME, SSM_PARAM_JWT_TOKEN_PUBLIC_KEY
    )
    monkeypatch.setenv(MOCK_AUTH_DYNAMODB_NAME, "test_dynamo")
    monkeypatch.setenv(MOCK_FEEDBACK_SENDER_EMAIL_ENV_NAME, MOCK_FEEDBACK_SENDER_EMAIL)
    monkeypatch.setenv(
        MOCK_FEEDBACK_EMAIL_SUBJECT_ENV_NAME, MOCK_FEEDBACK_EMAIL_SUBJECT
    )
    monkeypatch.setenv(
        MOCK_EMAIL_RECIPIENT_SSM_PARAM_KEY_ENV_NAME, MOCK_EMAIL_RECIPIENT_SSM_PARAM_KEY
    )
    monkeypatch.setenv(
        MOCK_APPCONFIG_APPLICATION_ENV_NAME, MOCK_APPCONFIG_APPLICATION_ID
    )
    monkeypatch.setenv(
        MOCK_APPCONFIG_ENVIRONMENT_ENV_NAME, MOCK_APPCONFIG_ENVIRONMENT_ID
    )
    monkeypatch.setenv(
        MOCK_APPCONFIG_CONFIGURATION_ENV_NAME, MOCK_APPCONFIG_CONFIGURATION_ID
    )
    monkeypatch.setenv(
        MOCK_PRESIGNED_URL_ROLE_ARN_KEY, MOCK_PRESIGNED_URL_ROLE_ARN_VALUE
    )
    monkeypatch.setenv(MOCK_STATISTICS_TABLE_NAME, MOCK_STATISTICS_TABLE)
    monkeypatch.setenv(
        MOCK_STATISTICS_REPORT_BUCKET_NAME, MOCK_STATISTICS_REPORT_BUCKET
    )


EXPECTED_PARSED_PATIENT_BASE_CASE = PatientDetails(
    givenName=["Jane"],
    familyName="Smith",
    birthDate="2010-10-22",
    postalCode="LS1 6AE",
    nhsNumber="9000000009",
    superseded=False,
    restricted=False,
    generalPracticeOds="Y12345",
    active=True,
)


@pytest.fixture
def mock_patient_details():
    yield EXPECTED_PARSED_PATIENT_BASE_CASE


@pytest.fixture
def mock_valid_pds_response():
    mock_response = Response()
    mock_response.status_code = 200
    with open("services/mock_data/pds_patient_9000000002_H81109_gp.json", "rb") as f:
        mock_data = f.read()
        mock_response._content = mock_data
    yield mock_response


@pytest.fixture(scope="session", autouse=True)
def logger_mocker():
    with mock.patch("utils.audit_logging_setup.SensitiveAuditService.emit") as _fixture:
        yield _fixture


@pytest.fixture
def event():
    api_gateway_proxy_event = {
        "httpMethod": "GET",
        "headers": {"Authorization": "test_token"},
    }
    return api_gateway_proxy_event


@pytest.fixture
def context():
    @dataclass
    class LambdaContext:
        function_name: str = "test"
        aws_request_id: str = MOCK_INTERACTION_ID
        invoked_function_arn: str = (
            "arn:aws:lambda:eu-west-1:123456789101:function:test"
        )

    return LambdaContext()


@pytest.fixture
def mock_userinfo():
    role_id = "500000000001"
    org_code = "A9A5A"
    role_code = "R8015"
    user_id = "500000000000"
    mock_userinfo = {
        "nhsid_useruid": user_id,
        "name": "TestUserOne Caius Mr",
        "nhsid_nrbac_roles": [
            {
                "person_orgid": "500000000000",
                "person_roleid": role_id,
                "org_code": org_code,
                "role_name": '"Support":"Systems Support":"Systems Support Access Role"',
                "role_code": "S8001:G8005:" + role_code,
            },
            {
                "person_orgid": "500000000000",
                "person_roleid": "500000000000",
                "org_code": "B9A5A",
                "role_name": '"Primary Care Support England":"Systems Support Access Role"',
                "role_code": "S8001:G8005:R8015",
            },
        ],
        "given_name": "Caius",
        "family_name": "TestUserOne",
        "uid": "500000000000",
        "nhsid_user_orgs": [
            {"org_name": "NHSID DEV", "org_code": "A9A5A"},
            {"org_name": "Primary Care Support England", "org_code": "B9A5A"},
        ],
        "sub": "500000000000",
    }
    yield {
        "role_id": role_id,
        "role_code": role_code,
        "org_code": org_code,
        "user_id": user_id,
        "user_info": mock_userinfo,
    }


@pytest.fixture()
def validation_error() -> ValidationError:
    try:
        data = {}
        DocumentReference.model_validate(data)
    except ValidationError as e:
        return e


class MockError(Enum):
    Error = {
        "message": "Client error",
        "err_code": "AB_XXXX",
        "interaction_id": "88888888-4444-4444-4444-121212121212",
    }


@pytest.fixture
def mock_temp_folder(mocker):
    temp_folder = tempfile.mkdtemp()
    mocker.patch.object(tempfile, "mkdtemp", return_value=temp_folder)
    yield temp_folder


@pytest.fixture
def mock_uuid(mocker):
    mocker.patch("uuid.uuid4", return_value=TEST_UUID)
    yield TEST_UUID


@contextmanager
def expect_not_to_raise(exception, message_when_fail=""):
    try:
        yield
    except exception:
        message_when_fail = message_when_fail or "DID RAISE {0}".format(exception)
        raise pytest.fail(message_when_fail)
