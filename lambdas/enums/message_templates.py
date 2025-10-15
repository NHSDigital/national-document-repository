from enum import StrEnum


class MessageTemplates(StrEnum):
    ITOC_FEEDBACK_TEST_SLACK = "./models/templates/itoc_slack_feedback_blocks.json"
    ITOC_FEEDBACK_TEST_TEAMS = "./models/templates/itoc_feedback_teams_message.json"
