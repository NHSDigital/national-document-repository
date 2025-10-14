import json
import os

import requests
from enums.message_templates import MessageTemplates
from enums.supported_document_types import logger
from jinja2 import Template
from models.feedback_model import Feedback
from requests.exceptions import HTTPError


class SendTestFeedbackService:

    def process_feedback(self, feedback: Feedback):
        self.send_itoc_feedback_via_slack(feedback)
        self.send_itoc_feedback_via_teams(feedback)

    def send_itoc_feedback_via_slack(self, feedback: Feedback):
        logger.info("Sending ITOC test feedback via slack")
        headers = {
            "Content-type": "application/json; charset=utf-8",
            "Authorization": "Bearer " + os.environ["ITOC_TESTING_SLACK_BOT_TOKEN"],
        }

        body = {
            "blocks": self.compose_message(
                feedback, MessageTemplates.ITOC_FEEDBACK_TEST_SLACK
            ),
            "channel": os.environ["ITOC_TESTING_CHANNEL_ID"],
        }
        try:
            response = requests.post(
                url="https://slack.com/api/chat.postMessage", json=body, headers=headers
            )
            response.raise_for_status()
            logger.info("Successfully sent ITOC test feedback via slack.")
        except HTTPError as e:
            logger.error(e)
            logger.error("Failed to send ITOC test feedback via slack.")

    def send_itoc_feedback_via_teams(self, feedback: Feedback):
        logger.info("Sending ITOC test feedback via teams")
        try:
            payload = self.compose_message(
                feedback, MessageTemplates.ITOC_FEEDBACK_TEST_TEAMS
            )

            headers = {"Content-type": "application/json"}

            response = requests.post(
                url=os.environ["ITOC_TESTING_TEAMS_WEBHOOK"],
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            logger.info("ITOC test feedback successfully sent via teams.")
        except HTTPError as e:
            logger.error(e)
            logger.error("ITOC test feedback failed via teams.")

    def compose_message(self, feedback: Feedback, messaging_template: str):
        logger.info("Composing ITOC test feedback message...")
        with open(messaging_template, "r") as f:
            template_content = f.read()

        template = Template(template_content)

        context = {
            "name": feedback.respondent_name,
            "experience": feedback.experience,
            "feedback": feedback.feedback_content,
        }

        rendered_json = template.render(context)
        return json.loads(rendered_json)
