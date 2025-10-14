import json
from copy import deepcopy

import pytest
from enums.lambda_error import LambdaError
from handlers.send_feedback_handler import is_itoc_test_feedback, lambda_handler
from models.feedback_model import Feedback
from requests import Response
from services.send_feedback_service import SendFeedbackService
from tests.unit.conftest import (
    MOCK_FEEDBACK_RECIPIENT_EMAIL_LIST,
    MOCK_INTERACTION_ID,
    MOCK_ITOC_ODS_CODES,
)
from tests.unit.helpers.data.feedback.mock_data import (
    MOCK_ITOC_FEEDBACK_BODY_JSON_STR,
    MOCK_PARSED_FEEDBACK,
    MOCK_PARSED_ITOC_FEEDBACK,
    MOCK_VALID_FEEDBACK_BODY_JSON_STR,
    MOCK_VALID_SEND_FEEDBACK_EVENT,
)
from utils.lambda_exceptions import SendFeedbackException
from utils.lambda_response import ApiGatewayResponse


@pytest.fixture
def mock_feedback_service(mocker):
    mocked_class = mocker.patch("handlers.send_feedback_handler.SendFeedbackService")
    mocked_instance = mocked_class.return_value
    return mocked_instance


@pytest.fixture
def mock_send_test_feedback_service(mocker):
    mocked_class = mocker.patch(
        "handlers.send_feedback_handler.SendTestFeedbackService"
    )
    mocked_instance = mocked_class.return_value
    return mocked_instance


@pytest.fixture
def mock_get_email_recipients_list(mocker):
    yield mocker.patch.object(
        SendFeedbackService,
        "get_email_recipients_list",
        return_value=MOCK_FEEDBACK_RECIPIENT_EMAIL_LIST,
    )


@pytest.fixture
def mock_validator(mocker):
    yield mocker.patch.object(Feedback, "model_validate_json")


@pytest.fixture
def mock_jwt_encode_itoc_user(mocker):
    decoded_token = {"selected_organisation": {"org_ods_code": MOCK_ITOC_ODS_CODES[0]}}
    yield mocker.patch("jwt.decode", return_value=decoded_token)


@pytest.fixture
def mock_itoc_test_event(event):
    itoc_event = deepcopy(event)
    itoc_event["body"] = MOCK_ITOC_FEEDBACK_BODY_JSON_STR
    itoc_event["httpMethod"] = "POST"
    yield itoc_event


@pytest.fixture
def mock_valid_feedback_event(event):
    valid_feedback_event = deepcopy(event)
    valid_feedback_event["body"] = MOCK_VALID_FEEDBACK_BODY_JSON_STR
    valid_feedback_event["httpMethod"] = "POST"
    yield valid_feedback_event


@pytest.fixture
def mock_post(mocker):
    yield mocker.patch("requests.post")


def test_lambda_handler_respond_with_200_when_successful(
    set_env,
    context,
    mock_feedback_service,
    mock_validator,
    mock_valid_feedback_event,
    mock_jwt_encode,
):
    mock_validator.return_value = MOCK_PARSED_FEEDBACK

    expected = ApiGatewayResponse(
        status_code=200, body="Feedback email processed", methods="POST"
    ).create_api_gateway_response()

    actual = lambda_handler(mock_valid_feedback_event, context)
    mock_validator.assert_called_with(MOCK_VALID_FEEDBACK_BODY_JSON_STR)
    assert actual == expected


def test_lambda_handler_respond_with_400_when_no_event_body_given(
    set_env, context, mock_valid_feedback_event, mock_jwt_encode
):
    test_event = deepcopy(mock_valid_feedback_event)
    test_event.pop("body")
    expected = ApiGatewayResponse(
        status_code=400,
        body=json.dumps(
            {
                "message": "Missing POST request body",
                "err_code": "SFB_4001",
                "interaction_id": MOCK_INTERACTION_ID,
            }
        ),
        methods="POST",
    ).create_api_gateway_response()

    actual = lambda_handler(test_event, context)
    assert actual == expected


def test_lambda_handler_respond_with_400_when_invalid_event_body_given(
    set_env,
    context,
    mock_get_email_recipients_list,
    mock_valid_feedback_event,
    mock_jwt_encode,
):
    test_event = deepcopy(mock_valid_feedback_event)
    test_event["body"] = "some invalid feedback body"
    expected = ApiGatewayResponse(
        status_code=400,
        body=json.dumps(
            {
                "message": "Invalid POST request body",
                "err_code": "SFB_4002",
                "interaction_id": MOCK_INTERACTION_ID,
            }
        ),
        methods="POST",
    ).create_api_gateway_response()

    actual = lambda_handler(test_event, context)
    assert actual == expected


def test_lambda_handler_respond_with_500_when_missing_env_var(context):
    test_event = MOCK_VALID_SEND_FEEDBACK_EVENT
    expected = ApiGatewayResponse(
        status_code=500,
        body=json.dumps(
            {
                "message": "An error occurred due to missing environment variable: 'FROM_EMAIL_ADDRESS'",
                "err_code": "ENV_5001",
                "interaction_id": MOCK_INTERACTION_ID,
            }
        ),
        methods="POST",
    ).create_api_gateway_response()

    actual = lambda_handler(test_event, context)
    assert actual == expected


def test_lambda_handler_respond_with_500_when_failed_to_get_recipient_emails_from_param_store(
    set_env,
    context,
    mock_get_email_recipients_list,
    mock_valid_feedback_event,
    mock_jwt_encode,
):

    mock_get_email_recipients_list.side_effect = SendFeedbackException(
        500, LambdaError.FeedbackFetchParamFailure
    )

    expected = ApiGatewayResponse(
        status_code=500,
        body=json.dumps(
            {
                "message": "Failed to fetch parameters for sending email from SSM param store",
                "err_code": "SFB_5002",
                "interaction_id": MOCK_INTERACTION_ID,
            }
        ),
        methods="POST",
    ).create_api_gateway_response()

    actual = lambda_handler(mock_valid_feedback_event, context)
    assert actual == expected


def test_lambda_handler_respond_with_500_when_failed_to_send_email(
    set_env, context, mock_feedback_service, mock_valid_feedback_event, mock_jwt_encode
):
    mock_feedback_service.process_feedback.side_effect = SendFeedbackException(
        500, LambdaError.FeedbackSESFailure
    )

    expected = ApiGatewayResponse(
        status_code=500,
        body=json.dumps(
            {
                "message": "Error occur when sending email by SES",
                "err_code": "SFB_5001",
                "interaction_id": MOCK_INTERACTION_ID,
            }
        ),
        methods="POST",
    ).create_api_gateway_response()

    actual = lambda_handler(mock_valid_feedback_event, context)
    assert actual == expected


def test_lambda_handler_respond_with_200_when_itoc_feedback_sent(
    set_env,
    context,
    mock_send_test_feedback_service,
    mock_validator,
    mock_jwt_encode_itoc_user,
    mock_itoc_test_event,
    mock_feedback_service,
    mock_get_email_recipients_list,
):
    mock_validator.return_value = MOCK_PARSED_ITOC_FEEDBACK

    expected = ApiGatewayResponse(
        status_code=200, body="Feedback email processed", methods="POST"
    ).create_api_gateway_response()

    actual = lambda_handler(mock_itoc_test_event, context)

    mock_validator.assert_called_once_with(MOCK_ITOC_FEEDBACK_BODY_JSON_STR)
    mock_feedback_service.process_feedback.assert_called()
    assert actual == expected


def test_lambda_handler_respond_with_200_when_failed_to_send_itoc_feedback(
    set_env,
    context,
    mock_send_test_feedback_service,
    mock_jwt_encode_itoc_user,
    mock_itoc_test_event,
    mock_post,
    mock_feedback_service,
    mock_get_email_recipients_list,
):

    response = Response()
    response.status_code = 500
    mock_post.return_value = response

    expected = ApiGatewayResponse(
        status_code=200, body="Feedback email processed", methods="POST"
    ).create_api_gateway_response()

    actual = lambda_handler(mock_itoc_test_event, context)
    mock_feedback_service.process_feedback.assert_called()
    assert actual == expected


def test_is_itoc_test_feedback_itoc_email(set_env):
    assert is_itoc_test_feedback(MOCK_ITOC_ODS_CODES.split(",")[0])


def test_is_itoc_test_feedback_non_itoc_email(set_env):
    assert is_itoc_test_feedback("ABC1234") is False
