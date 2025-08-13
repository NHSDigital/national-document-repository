import json

import boto3
import pytest
from botocore.exceptions import ClientError
from enums.lambda_error import LambdaError
from models.feedback_model import Feedback
from requests import Response
from services.base.ssm_service import SSMService
from services.send_feedback_service import SendFeedbackService
from tests.unit.conftest import (
    MOCK_FEEDBACK_EMAIL_SUBJECT,
    MOCK_FEEDBACK_RECIPIENT_EMAIL_LIST,
    MOCK_FEEDBACK_SENDER_EMAIL,
    MOCK_ITOC_SLACK_CHANNEL_ID,
    MOCK_ITOC_TEST_EMAIL_ADDRESS,
    MOCK_SLACK_BOT_TOKEN,
)
from tests.unit.helpers.data.feedback.mock_data import (
    MOCK_BAD_FEEDBACK_BODY_WITH_XSS_INJECTION,
    MOCK_EMAIL_BODY,
    MOCK_EMAIL_BODY_ANONYMOUS,
    MOCK_ITOC_FEEDBACK_BODY,
    MOCK_ITOC_FEEDBACK_BODY_JSON_STR,
    MOCK_PARSED_FEEDBACK,
    MOCK_PARSED_FEEDBACK_ANONYMOUS,
    MOCK_VALID_FEEDBACK_BODY_ANONYMOUS_JSON_STR,
    MOCK_VALID_FEEDBACK_BODY_JSON_STR,
    readfile,
)
from utils.lambda_exceptions import SendFeedbackException


@pytest.fixture
def mock_get_ssm_parameter(mocker):
    yield mocker.patch.object(SSMService, "get_ssm_parameter")


@pytest.fixture
def send_feedback_service(mocker, set_env):
    mocker.patch.object(
        SendFeedbackService,
        "get_email_recipients_list",
        return_value=MOCK_FEEDBACK_RECIPIENT_EMAIL_LIST,
    )
    return SendFeedbackService()


@pytest.fixture
def mock_send_feedback_by_email(mocker):
    yield mocker.patch.object(SendFeedbackService, "send_feedback_by_email")


@pytest.fixture
def mock_validator(mocker):
    yield mocker.patch.object(
        Feedback, "model_validate_json", return_value=MOCK_PARSED_FEEDBACK
    )


@pytest.fixture
def mock_ses_client(mocker):
    yield mocker.create_autospec(boto3.client("ses"))


@pytest.fixture
def mock_send_itoc_feedback_service(send_feedback_service, mocker):
    service = send_feedback_service
    mocker.patch.object(service, "compose_slack_message")
    mocker.patch.object(service, "send_itoc_feedback_via_slack")
    mocker.patch.object(service, "send_feedback_by_email")
    yield service


@pytest.fixture
def mock_post(mocker):
    yield mocker.patch("requests.post")


def test_process_feedback_validate_feedback_content_and_send_email(
    send_feedback_service,
    mock_send_feedback_by_email,
    mock_validator,
    mock_get_ssm_parameter,
):
    mock_event_body = MOCK_VALID_FEEDBACK_BODY_JSON_STR
    expected_email_body = MOCK_EMAIL_BODY

    send_feedback_service.process_feedback(mock_event_body)

    mock_validator.assert_called_with(mock_event_body)
    mock_send_feedback_by_email.assert_called_with(expected_email_body)


def test_process_feedback_allow_respondent_email_and_name_to_be_blank(
    send_feedback_service, mock_send_feedback_by_email, mock_get_ssm_parameter
):
    mock_event_body = MOCK_VALID_FEEDBACK_BODY_ANONYMOUS_JSON_STR
    expected_email_body = MOCK_EMAIL_BODY_ANONYMOUS

    send_feedback_service.process_feedback(mock_event_body)

    mock_send_feedback_by_email.assert_called_with(expected_email_body)


def test_process_feedback_sanitise_html_tags_before_send_out_email(
    send_feedback_service, mock_send_feedback_by_email, mock_get_ssm_parameter
):
    mock_event_body = MOCK_BAD_FEEDBACK_BODY_WITH_XSS_INJECTION
    bad_code = (
        r"<img src=some_malicious_xss_payload onerror=some_malicious_xss_payload>"
    )
    sanitised = (
        r"&lt;img src=some_malicious_xss_payload onerror=some_malicious_xss_payload&gt;"
    )

    assert bad_code in mock_event_body

    send_feedback_service.process_feedback(mock_event_body)

    outbound_email_body = mock_send_feedback_by_email.call_args[0][0]
    assert bad_code not in outbound_email_body
    assert sanitised in outbound_email_body


def test_process_feedback_raise_error_when_given_invalid_data(
    send_feedback_service, mock_send_feedback_by_email
):
    mock_event_body = '{"key1": "value1"}'
    expected_error = SendFeedbackException(400, LambdaError.FeedbackInvalidBody)

    with pytest.raises(SendFeedbackException) as error:
        send_feedback_service.process_feedback(mock_event_body)

    assert error.value == expected_error

    mock_send_feedback_by_email.assert_not_called()


def test_process_feedback_raise_error_when_fail_to_send_email_by_ses(
    send_feedback_service, mock_ses_client, mock_get_ssm_parameter
):
    mock_error = ClientError(
        {
            "Error": {
                "Code": "LimitExceededException",
                "Message": "API call limit exceeded",
            }
        },
        "SendEmail",
    )
    mock_ses_client.send_email.side_effect = mock_error
    send_feedback_service.ses_client = mock_ses_client

    expected_error = SendFeedbackException(500, LambdaError.FeedbackSESFailure)
    event_body = MOCK_VALID_FEEDBACK_BODY_JSON_STR

    with pytest.raises(SendFeedbackException) as error:
        send_feedback_service.process_feedback(event_body)

    assert error.value == expected_error


def test_build_email_body_convert_feedback_to_html(send_feedback_service):
    expected = (
        "<html><body>"
        + "<h2>Name</h2><p>Jane Smith</p>"
        + "<h2>Email Address</h2><p>jane_smith@test-email.com</p>"
        + "<h2>Feedback</h2><p>Mock feedback content</p>"
        + "<h2>Overall Experience</h2><p>Very Satisfied</p>"
        + "</html></body>"
    )

    actual = send_feedback_service.build_email_body(MOCK_PARSED_FEEDBACK)

    assert actual == expected


def test_build_email_body_skip_name_and_email_if_not_given(send_feedback_service):
    expected = (
        "<html><body>"
        + "<h2>Feedback</h2><p>Mock feedback content</p>"
        + "<h2>Overall Experience</h2><p>Very Satisfied</p>"
        + "</html></body>"
    )

    actual = send_feedback_service.build_email_body(MOCK_PARSED_FEEDBACK_ANONYMOUS)

    assert actual == expected


def test_send_feedback_by_email_happy_path(
    send_feedback_service, mock_ses_client, mocker
):
    mock_send_itoc_feedback = mocker.patch.object(
        send_feedback_service, "send_itoc_feedback_via_slack"
    )
    send_feedback_service.ses_client = mock_ses_client

    send_feedback_service.send_feedback_by_email(MOCK_EMAIL_BODY)

    mock_ses_client.send_email.assert_called_with(
        Source=MOCK_FEEDBACK_SENDER_EMAIL,
        Destination={"ToAddresses": MOCK_FEEDBACK_RECIPIENT_EMAIL_LIST},
        Message={
            "Subject": {"Data": MOCK_FEEDBACK_EMAIL_SUBJECT},
            "Body": {"Html": {"Data": MOCK_EMAIL_BODY}},
        },
    )

    mock_send_itoc_feedback.assert_not_called()


def test_send_feedback_by_email_raise_error_on_failure(
    send_feedback_service, mock_ses_client
):
    mock_error = ClientError(
        {
            "Error": {
                "Code": "LimitExceededException",
                "Message": "API call limit exceeded",
            }
        },
        "SendEmail",
    )
    mock_ses_client.send_email.side_effect = mock_error
    send_feedback_service.ses_client = mock_ses_client

    expected_error = SendFeedbackException(500, LambdaError.FeedbackSESFailure)
    email_body = MOCK_EMAIL_BODY

    with pytest.raises(SendFeedbackException) as error:
        send_feedback_service.send_feedback_by_email(email_body)

    assert error.value == expected_error


def test_get_email_recipients_list_fetch_parameter_from_ssm_param_store(
    set_env,
    mock_get_ssm_parameter,
):
    mock_get_ssm_parameter.return_value = "gp2gp@localhost, test_email@localhost"

    actual = SendFeedbackService.get_email_recipients_list()
    expected = ["gp2gp@localhost", "test_email@localhost"]

    assert actual == expected


def test_get_email_recipients_list_raise_error_when_fail_to_fetch_from_ssm(
    set_env,
    mock_get_ssm_parameter,
):
    mock_error = ClientError(
        {
            "Error": {
                "Code": "UnauthorizedException",
                "Message": "Not authorized to access parameter store",
            }
        },
        "GetParameter",
    )
    expected_lambda_error = SendFeedbackException(
        500, LambdaError.FeedbackFetchParamFailure
    )

    mock_get_ssm_parameter.side_effect = mock_error

    with pytest.raises(SendFeedbackException) as error:
        SendFeedbackService.get_email_recipients_list()

    assert error.value == expected_lambda_error


def test_itoc_feedback_journey(
    mock_send_itoc_feedback_service, mock_post, mock_get_ssm_parameter
):
    mock_get_ssm_parameter.return_value = "itoc_testing@testing.com"

    mock_send_itoc_feedback_service.process_feedback(MOCK_ITOC_FEEDBACK_BODY_JSON_STR)

    mock_send_itoc_feedback_service.send_itoc_feedback_via_slack.assert_called()
    mock_send_itoc_feedback_service.send_feedback_by_email.assert_not_called()


def test_is_itoc_test_feedback_itoc_email(
    set_env, send_feedback_service, mock_get_ssm_parameter
):
    mock_get_ssm_parameter.return_value = MOCK_ITOC_TEST_EMAIL_ADDRESS

    assert send_feedback_service.is_itoc_test_feedback(MOCK_ITOC_TEST_EMAIL_ADDRESS)


def test_is_itoc_test_feedback_non_itoc_email(
    set_env, send_feedback_service, mock_get_ssm_parameter
):
    mock_get_ssm_parameter.return_value = MOCK_ITOC_TEST_EMAIL_ADDRESS

    assert (
        send_feedback_service.is_itoc_test_feedback("jane_smith@test-email.com")
        is False
    )


def test_compose_slack_message(send_feedback_service):
    slack_block_json_str = readfile("mock_itoc_slack_message_blocks.json")
    expected = json.loads(slack_block_json_str)
    feedback = Feedback.model_validate(MOCK_ITOC_FEEDBACK_BODY)
    actual = send_feedback_service.compose_slack_message(feedback)
    assert actual == expected


def test_send_slack_message(send_feedback_service, mock_post):
    slack_block_json_str = readfile("mock_itoc_slack_message_blocks.json")
    slack_blocks = json.loads(slack_block_json_str)
    feedback = Feedback.model_validate(MOCK_ITOC_FEEDBACK_BODY)

    headers = {
        "Authorization": "Bearer " + MOCK_SLACK_BOT_TOKEN,
        "Content-type": "application/json; charset=utf-8",
    }

    body = {"blocks": slack_blocks, "channel": MOCK_ITOC_SLACK_CHANNEL_ID}

    send_feedback_service.send_itoc_feedback_via_slack(feedback)

    mock_post.assert_called_with(
        url="https://slack.com/api/chat.postMessage", json=body, headers=headers
    )


def test_send_slack_message_raise_error_on_failure(send_feedback_service, mock_post):
    feedback = Feedback.model_validate(MOCK_ITOC_FEEDBACK_BODY)
    response = Response()
    response.status_code = 403
    mock_post.return_value = response

    expected_error = SendFeedbackException(403, LambdaError.FeedbackITOCFailure)

    with pytest.raises(SendFeedbackException) as error:
        send_feedback_service.send_itoc_feedback_via_slack(feedback)

    assert error.value == expected_error
