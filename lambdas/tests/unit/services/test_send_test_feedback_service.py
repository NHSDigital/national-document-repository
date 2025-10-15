import json

import pytest
from enums.message_templates import MessageTemplates
from models.feedback_model import Feedback
from requests import Response
from services.send_test_feedback_service import SendTestFeedbackService
from tests.unit.conftest import (
    MOCK_ITOC_SLACK_CHANNEL_ID,
    MOCK_ITOC_TEAMS_WEBHOOK,
    MOCK_SLACK_BOT_TOKEN,
)
from tests.unit.helpers.data.feedback.mock_data import (
    MOCK_ITOC_FEEDBACK_BODY,
    MOCK_ITOC_FEEDBACK_BODY_JSON_STR,
    readfile,
)


@pytest.fixture
def send_test_feedback_service(set_env):
    return SendTestFeedbackService()


@pytest.fixture
def mock_send_test_feedback_service(send_test_feedback_service, mocker):
    service = send_test_feedback_service
    mocker.patch.object(service, "compose_message")
    mocker.patch.object(service, "send_itoc_feedback_via_slack")
    mocker.patch.object(service, "send_itoc_feedback_via_teams")
    yield service


@pytest.fixture
def mock_post(mocker):
    yield mocker.patch("requests.post")


def test_itoc_feedback_journey(mock_send_test_feedback_service, mock_post):
    mock_send_test_feedback_service.process_feedback(MOCK_ITOC_FEEDBACK_BODY_JSON_STR)

    mock_send_test_feedback_service.send_itoc_feedback_via_slack.assert_called()
    mock_send_test_feedback_service.send_itoc_feedback_via_teams.assert_called()


def test_compose_slack_message(send_test_feedback_service):
    slack_block_json_str = readfile("mock_itoc_slack_message_blocks.json")
    expected = json.loads(slack_block_json_str)
    feedback = Feedback.model_validate(MOCK_ITOC_FEEDBACK_BODY)
    actual = send_test_feedback_service.compose_message(
        feedback, MessageTemplates.ITOC_FEEDBACK_TEST_SLACK
    )
    assert actual == expected


def test_send_slack_message(send_test_feedback_service, mock_post):
    slack_block_json_str = readfile("mock_itoc_slack_message_blocks.json")
    slack_blocks = json.loads(slack_block_json_str)
    feedback = Feedback.model_validate(MOCK_ITOC_FEEDBACK_BODY)

    headers = {
        "Authorization": "Bearer " + MOCK_SLACK_BOT_TOKEN,
        "Content-type": "application/json; charset=utf-8",
    }

    body = {"blocks": slack_blocks, "channel": MOCK_ITOC_SLACK_CHANNEL_ID}

    send_test_feedback_service.send_itoc_feedback_via_slack(feedback)

    mock_post.assert_called_with(
        url="https://slack.com/api/chat.postMessage", json=body, headers=headers
    )


def test_send_slack_message_logs_error_on_failure(
    send_test_feedback_service, mock_post, caplog
):
    feedback = Feedback.model_validate(MOCK_ITOC_FEEDBACK_BODY)
    response = Response()
    response.status_code = 500
    mock_post.return_value = response

    expected_log = "Failed to send ITOC test feedback via slack."

    send_test_feedback_service.send_itoc_feedback_via_slack(feedback)

    actual = caplog.messages[-1]

    assert actual == expected_log


def test_compose_teams_message(send_test_feedback_service):
    teams_message_json_str = readfile("mock_itoc_teams_message.json")
    expected = json.loads(teams_message_json_str)
    feedback = Feedback.model_validate(MOCK_ITOC_FEEDBACK_BODY)
    actual = send_test_feedback_service.compose_message(
        feedback, MessageTemplates.ITOC_FEEDBACK_TEST_TEAMS
    )
    assert actual == expected


def test_send_itoc_feedback_via_teams(send_test_feedback_service, mock_post):
    teams_message_json_str = readfile("mock_itoc_teams_message.json")
    teams_message = json.loads(teams_message_json_str)
    feedback = Feedback.model_validate(MOCK_ITOC_FEEDBACK_BODY)

    headers = {"Content-type": "application/json"}

    send_test_feedback_service.send_itoc_feedback_via_teams(feedback)

    mock_post.assert_called_with(
        url=MOCK_ITOC_TEAMS_WEBHOOK, json=teams_message, headers=headers
    )


def test_send_teams_message_logs_error_on_failure(
    send_test_feedback_service, mock_post, caplog
):
    feedback = Feedback.model_validate(MOCK_ITOC_FEEDBACK_BODY)
    response = Response()
    response.status_code = 500
    mock_post.return_value = response

    expected_log = "ITOC test feedback failed via teams."

    send_test_feedback_service.send_itoc_feedback_via_teams(feedback)

    actual = caplog.messages[-1]

    assert actual == expected_log
