import json
import os
import re
from datetime import datetime, timedelta, timezone
from time import sleep

import boto3
import requests
from botocore.exceptions import ClientError
from enums.alarm_history_field import AlarmHistoryField
from enums.alarm_severity import AlarmSeverity
from enums.alarm_state import AlarmState
from jinja2 import Template
from models.alarm_entry import AlarmEntry
from pydantic import ValidationError
from requests import HTTPError
from services.base.dynamo_service import DynamoDBService
from utils.audit_logging_setup import LoggingService

logger = LoggingService(__name__)


class IMAlertingService:
    REQUEST_TIMEOUT_SECONDS = 60
    # time to wait between alerts - If the severity has changed after this time, we want to show the new severity
    ALARM_OK_WAIT_SECONDS = 180
    ALARM_TTL_TIME_SECONDS = 300
    SLACK_POST_CHAT_API = "https://slack.com/api/chat.postMessage"
    SLACK_UPDATE_CHAT_API = "https://slack.com/api/chat.update"
    SLACK_REACTIONS_API_PREFIX = "https://slack.com/api/reactions."

    def __init__(self, message):
        self.dynamo_service = DynamoDBService()
        self.table_name = os.environ["ALARM_HISTORY_DYNAMODB_NAME"]
        self.webhook_url = os.environ["TEAMS_WEBHOOK_URL"]
        self.confluence_base_url = os.environ["CONFLUENCE_BASE_URL"]
        self.message = message
        self.slack_headers = {
            "Authorization": "Bearer " + os.environ["SLACK_BOT_TOKEN"],
            "Content-type": "application/json; charset=utf-8",
        }

    def handle_alarm_alert(self):
        alarm_state = self.message["NewStateValue"]
        alarm_time = self.message["StateChangeTime"]
        alarm_tags = self.get_all_alarm_tags()
        alarm_name = f"{alarm_tags['alarm_group']} {alarm_tags['alarm_metric']}"
        alarm_history = self.get_alarm_history(alarm_name)

        try:
            if alarm_history:
                self.handle_existing_alarm_history(
                    alarm_history, alarm_state, alarm_name, alarm_time, alarm_tags
                )
            else:
                self.handle_empty_alarm_history(
                    alarm_state, alarm_name, alarm_time, alarm_tags
                )
        except ValidationError:
            logger.error(
                f"Failed to validate the model for the new alarm_entry for alarm: {alarm_name}"
            )

    def handle_existing_alarm_history(
        self, alarm_history, alarm_state, alarm_name, alarm_time, alarm_tags
    ):
        active_alarms = self.find_active_alarm_entries(alarm_history)

        if active_alarms:
            for alarm_entry in active_alarms:
                self.handle_current_alarm_episode(
                    alarm_entry=alarm_entry,
                    alarm_state=alarm_state,
                    tags=alarm_tags,
                )

        elif alarm_state == AlarmState.ALARM:
            logger.info(
                f"All alarm entries for {alarm_name} have expired, creating a new one"
            )
            self.handle_new_alarm_episode(
                alarm_name=alarm_name,
                alarm_time=alarm_time,
                tags=alarm_tags,
            )

        else:
            logger.info(
                f"All alarm entries for {alarm_name} have expired,"
                f" lambda was triggered by non-{AlarmState.ALARM} state change,"
                "This trigger can safely be ignored."
            )

    def find_active_alarm_entries(self, alarm_history):
        return [
            alarm_entry
            for alarm_entry in alarm_history
            if not self.is_episode_expired(alarm_entry)
        ]

    def handle_empty_alarm_history(
        self, alarm_state, alarm_name, alarm_time, alarm_tags
    ):
        logger.info(
            f"No existing alarm history for {alarm_name} - alarm is in {alarm_state} state"
        )

        if alarm_state == AlarmState.ALARM:
            self.handle_new_alarm_episode(
                alarm_name=alarm_name, alarm_time=alarm_time, tags=alarm_tags
            )

    def is_episode_expired(self, alarm_entry: AlarmEntry) -> bool:
        if not alarm_entry.time_to_exist:
            return False

        current_timestamp = datetime.now().timestamp()
        return current_timestamp >= alarm_entry.time_to_exist

    def handle_new_alarm_episode(self, alarm_name: str, alarm_time: str, tags: dict):
        logger.info(
            f"Creating new alarm episode {alarm_name}:{self.create_alarm_timestamp(alarm_time)}"
        )

        new_entry = AlarmEntry(
            alarm_name_metric=alarm_name,
            time_created=self.create_alarm_timestamp(alarm_time),
            last_updated=self.create_alarm_timestamp(alarm_time),
            channel_id=os.environ["SLACK_CHANNEL_ID"],
        )
        AlarmEntry.model_validate(new_entry)
        self.update_alarm_state_history(new_entry, tags)
        self.create_alarm_entry(new_entry)
        self.send_teams_alert(new_entry)
        self.send_initial_slack_alert(new_entry)
        self.send_slack_response(new_entry)

    def handle_current_alarm_episode(
        self, alarm_entry: AlarmEntry, alarm_state: str, tags: dict
    ):
        logger.info(
            f"Updating alarm episode {alarm_entry.alarm_name_metric}:{alarm_entry.time_created}"
        )

        match alarm_state:
            case AlarmState.ALARM:
                logger.info(
                    f"Handling {tags.get('severity', '')} severity alarm action for {alarm_entry.alarm_name_metric}"
                )

                self.update_alarm_state_history(tags=tags, alarm_entry=alarm_entry)
                self.send_teams_alert(alarm_entry)
                self.send_slack_response(alarm_entry)
                self.update_original_slack_message(alarm_entry)
                self.update_alarm_history_table(alarm_entry)
            case AlarmState.OK:
                self.handle_ok_action_trigger(tags=tags, alarm_entry=alarm_entry)

    def create_alarm_entry(self, alarm_entry: AlarmEntry):
        dynamodb_item = alarm_entry.to_dynamo()

        logger.info(
            f"Creating new alarm entry in {self.table_name} table for {alarm_entry.alarm_name_metric}. "
            f"dynamodb entry will be {dynamodb_item}"
        )

        try:
            self.dynamo_service.create_item(
                table_name=self.table_name, item=dynamodb_item
            )
        except ClientError:
            logger.error(
                f"Failed to create new alarm entry in {self.table_name} table for {alarm_entry.alarm_name_metric}"
            )

    def handle_ok_action_trigger(self, tags: dict, alarm_entry: AlarmEntry):
        logger.info(f"Handling OK action trigger for {alarm_entry.alarm_name_metric}")

        if not self.all_alarm_state_ok(tags):
            logger.info(
                "Not all alarms are in OK state. Skipping handling OK action trigger"
            )
            return

        self.wait_for_alarm_stabilisation()

        if self.is_last_updated(alarm_entry):
            logger.info(
                f"All alarms for {alarm_entry.alarm_name_metric} are in OK state, adding TTL."
            )
            self.finalise_ok_alarm_state(alarm_entry)
        else:
            logger.info(
                f"Alarm entry for {alarm_entry.alarm_name_metric} has been updated since reaching OK state"
            )

    """
    We want to wait for a set time (ALARM_OK_WAIT_SECONDS) to allow the alarm's OK state to stabilise before updating 
    the teams & slack alerts to display OK. This will prevent a situation where an alarm temporarily reaches an OK
    state and then immediately triggers a second alert if it transitions back to an ALARM state.
    """

    def wait_for_alarm_stabilisation(self):
        logger.info("Waiting for other alarms to be triggered before setting TTL.")
        sleep(self.ALARM_OK_WAIT_SECONDS)

    def finalise_ok_alarm_state(self, alarm_entry: AlarmEntry):
        alarm_entry.history.append(AlarmSeverity.OK)
        alarm_entry.last_updated = int(datetime.now().timestamp())
        self.add_ttl_to_alarm_entry(alarm_entry)
        self.update_alarm_history_table(alarm_entry)
        self.send_teams_alert(alarm_entry)
        self.send_slack_response(alarm_entry)
        self.update_original_slack_message(alarm_entry)

    def update_alarm_state_history(self, alarm_entry: AlarmEntry, tags: dict):
        severity_value = tags.get("severity")

        if not severity_value:
            logger.error("Missing severity value in alarm tags")
            return

        severity_value = severity_value.upper()

        try:
            alarm_severity = AlarmSeverity[severity_value]
            alarm_entry.history.append(alarm_severity)
        except ValueError:
            logger.error(f"Invalid severity value: {severity_value}")

        alarm_entry.time_to_exist = None
        alarm_entry.last_updated = int(datetime.now().timestamp())

    def get_alarm_history(self, alarm_name: str):
        logger.info(f"Checking if {alarm_name} already exists on alarm table")

        try:
            results = self.dynamo_service.query_table(
                table_name=self.table_name,
                search_key="AlarmNameMetric",
                search_condition=alarm_name,
            )

            return (
                [AlarmEntry.from_dynamo(item) for item in results["Items"]]
                if results
                else []
            )
        except ValidationError:
            logger.error(
                f"Failed to validate the alarm history model for alarm: {alarm_name}"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error while checking if alarm {alarm_name} exists on alarm table. Exception is: {e}"
            )
        return []

    def is_last_updated(self, alarm_entry: AlarmEntry) -> bool:
        try:
            response = self.dynamo_service.get_item(
                table_name=self.table_name,
                key={
                    AlarmHistoryField.ALARMNAMEMETRIC: alarm_entry.alarm_name_metric,
                    AlarmHistoryField.TIMECREATED: alarm_entry.time_created,
                },
            )
            entry_to_compare = AlarmEntry.from_dynamo(response["Item"])

            if alarm_entry.last_updated >= entry_to_compare.last_updated:
                logger.info(
                    f"No other alarm triggered since {alarm_entry.alarm_name_metric}:{alarm_entry.time_created} last updated"
                )
                return True
            else:
                logger.info(
                    f"Another alarm for {alarm_entry.alarm_name_metric}:{alarm_entry.time_created} triggered since last updated"
                )
                return False
        except Exception as e:
            logger.error(
                f"Unexpected error while checking if alarm_entry is last updated. "
                f"Returning False as it's not clear if this is the case. Exception is: {e}"
            )
            return False

    def update_alarm_history_table(self, alarm_entry: AlarmEntry):
        logger.info(
            f"Updating alarm table entry for: {alarm_entry.alarm_name_metric}. Alarm entry will be saved as {alarm_entry}"
        )

        fields_to_update = {
            AlarmHistoryField.HISTORY: alarm_entry.get_alarm_severity_list_as_string(),
            AlarmHistoryField.LASTUPDATED: int(datetime.now().timestamp()),
            AlarmHistoryField.SLACKTIMESTAMP: alarm_entry.slack_timestamp,
            AlarmHistoryField.TIMETOEXIST: alarm_entry.time_to_exist,
        }

        try:
            self.dynamo_service.update_item(
                table_name=self.table_name,
                key_pair={
                    AlarmHistoryField.ALARMNAMEMETRIC: alarm_entry.alarm_name_metric,
                    AlarmHistoryField.TIMECREATED: alarm_entry.time_created,
                },
                updated_fields=fields_to_update,
            )
        except ClientError as e:
            logger.error(
                f"Updating alarm table entry returned client error for alarm {alarm_entry.alarm_name_metric}: {e}"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error updating alarm table entry for alarm {alarm_entry.alarm_name_metric}: {e}"
            )

    def all_alarm_state_ok(self, tags: dict) -> bool:
        tag_filter = self.build_tag_filter(tags)
        logger.info(f"Getting resources with tags: {tag_filter}")

        try:
            client = boto3.client("resourcegroupstaggingapi")
            response = client.get_resources(
                ResourceTypeFilters=["cloudwatch:alarm"], TagFilters=tag_filter
            )

            resources = response["ResourceTagMappingList"]
            arns = [resource["ResourceARN"] for resource in resources]

            alarm_names = self.extract_alarm_names_from_arns(arns)

            cloudwatch_client = boto3.client("cloudwatch")
            cloudwatch_response = cloudwatch_client.describe_alarms(
                AlarmNames=alarm_names,
            )

            return all(
                alarm["StateValue"] == AlarmState.OK
                for alarm in cloudwatch_response["MetricAlarms"]
            )
        except Exception as e:
            logger.error(
                f"Unexpected error while checking alarm state. "
                f"Returning False as it's not clear if the alarm has stabilised or not. Exception is: {e}"
            )
            return False

    def get_all_alarm_tags(self) -> dict:
        logger.info(f"Getting all alarm tags for {self.message['AlarmArn']}")

        tags = {}

        try:
            client = boto3.client("cloudwatch")
            response = client.list_tags_for_resource(
                ResourceARN=self.message["AlarmArn"]
            )

            if response["Tags"]:
                for tag in response["Tags"]:
                    tags[tag["Key"]] = tag["Value"]
        except Exception as e:
            (logger.error(f"Unexpected error while getting alarm tags: {e}"))

        return tags

    def build_tag_filter(self, tags: dict) -> list:
        logger.info("Building tag filter")
        tag_filter = []

        for key, value in tags.items():
            if key == "alarm_group" or key == "alarm_metric":
                tag_filter.append({"Key": key, "Values": [value]})

        return tag_filter

    def extract_alarm_names_from_arns(self, arn_list: list) -> list:
        alarm_names = []
        for arn in arn_list:
            match = re.search(r"alarm:([^:]+)$", arn)
            if not match:
                raise ValueError(f"Invalid alarm ARN format: {arn}")
            alarm_names.append(match.group(1))
        return alarm_names

    def add_ttl_to_alarm_entry(self, alarm_entry: AlarmEntry):
        alarm_entry.time_to_exist = int(
            (
                datetime.now() + timedelta(seconds=self.ALARM_TTL_TIME_SECONDS)
            ).timestamp()
        )

    def create_alarm_timestamp(self, alarm_time: str) -> int:
        return int(datetime.fromisoformat(alarm_time).timestamp())

    def format_time_string(self, time_stamp: int) -> str:
        dt = datetime.fromtimestamp(time_stamp, tz=timezone.utc)
        return dt.strftime("%H:%M:%S %d-%m-%Y %Z")

    def unpack_alarm_history_unicode(self, alarm_history: list[AlarmSeverity]) -> str:
        alarm_history_unicodes = [severity.value for severity in alarm_history]
        return " ".join(alarm_history_unicodes)

    def unpack_alarm_history_emoji_name(
        self, alarm_history: list[AlarmSeverity]
    ) -> str:
        alarm_history_emoji_names = [
            f":{severity.additional_value}:" for severity in alarm_history
        ]
        return " ".join(alarm_history_emoji_names)

    def create_action_url(self, base_url: str, alarm_name: str) -> str:
        search_query = "#:~:text="

        prefixes = [f"{os.environ['WORKSPACE']}_", f"{os.environ['WORKSPACE']}-"]

        for prefix in prefixes:
            alarm_name = alarm_name.replace(prefix, "")

        url_extension = re.sub(r"[-_. ]", "%20", alarm_name)

        return f"{base_url}{search_query}{url_extension}"

    def send_teams_alert(self, alarm_entry: AlarmEntry):
        logger.info(
            f"Sending Microsoft Teams alert for: {alarm_entry.alarm_name_metric}"
        )

        try:
            payload = self.compose_teams_message(alarm_entry)

            headers = {"Content-Type": "application/json"}

            response = requests.post(
                url=self.webhook_url,
                headers=headers,
                data=payload,
                timeout=self.REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            logger.info(
                f"Microsoft Teams alert sent successfully for: {alarm_entry.alarm_name_metric}"
            )

        except HTTPError as e:
            logger.error(
                f"Microsoft Teams webhook returned HTTP error for alarm {alarm_entry.alarm_name_metric}: {e}"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error sending Microsoft Teams alert for alarm {alarm_entry.alarm_name_metric}: {e}"
            )

    def compose_teams_message(self, alarm_entry: AlarmEntry):
        with open(f"{os.getcwd()}/models/templates/teams_alert.json", "r") as f:
            template_content = f.read()

        template = Template(template_content)

        context = {
            "alarm_entry": alarm_entry,
            "alarm_history": self.unpack_alarm_history_unicode(alarm_entry.history),
            "formatted_time": self.format_time_string(alarm_entry.last_updated),
            "action_url": self.create_action_url(
                self.confluence_base_url, alarm_entry.alarm_name_metric
            ),
        }

        return template.render(context)

    def send_initial_slack_alert(self, alarm_entry: AlarmEntry):
        slack_message = {
            "channel": alarm_entry.channel_id,
            "blocks": self.compose_slack_message_blocks(alarm_entry),
        }

        try:
            response = requests.post(
                url=self.SLACK_POST_CHAT_API,
                data=json.dumps(slack_message),
                headers=self.slack_headers,
                timeout=self.REQUEST_TIMEOUT_SECONDS,
            )

            logger.info(f"Slack response: {response.text}")
            response.raise_for_status()
            alarm_entry.slack_timestamp = json.loads(response.content)["ts"]

            self.update_alarm_history_table(alarm_entry)

        except HTTPError as e:
            logger.error(
                f"Initial Slack alert returned HTTP error for alarm {alarm_entry.alarm_name_metric}: {e}"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error sending Initial Slack alert for alarm {alarm_entry.alarm_name_metric}: {e}"
            )

    def send_slack_response(self, alarm_entry: AlarmEntry):
        logger.info(
            f"Sending slack thread response for: {alarm_entry.alarm_name_metric}:{alarm_entry.time_created}"
        )

        slack_message = {
            "channel": alarm_entry.channel_id,
            "thread_ts": alarm_entry.slack_timestamp,
            "blocks": self.compose_slack_message_blocks(alarm_entry),
        }

        try:
            requests.post(
                url=self.SLACK_POST_CHAT_API,
                data=json.dumps(slack_message),
                headers=self.slack_headers,
                timeout=self.REQUEST_TIMEOUT_SECONDS,
            )
        except HTTPError as e:
            logger.error(
                f"Sending Slack response returned HTTP error for alarm {alarm_entry.alarm_name_metric}: {e}"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error sending Slack response for alarm {alarm_entry.alarm_name_metric}: {e}"
            )

    def update_original_slack_message(self, alarm_entry: AlarmEntry):
        try:
            slack_message = {
                "channel": alarm_entry.channel_id,
                "ts": alarm_entry.slack_timestamp,
                "blocks": self.compose_slack_message_blocks(alarm_entry),
            }

            requests.post(
                url=self.SLACK_UPDATE_CHAT_API,
                data=json.dumps(slack_message),
                headers=self.slack_headers,
                timeout=self.REQUEST_TIMEOUT_SECONDS,
            )
        except HTTPError as e:
            logger.error(
                f"Updating original Slack message returned HTTP error for alarm {alarm_entry.alarm_name_metric}: {e}"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error updating original Slack message for alarm {alarm_entry.alarm_name_metric}: {e}"
            )

    def compose_slack_message_blocks(self, alarm_entry: AlarmEntry):
        with open(f"{os.getcwd()}/models/templates/slack_alert_blocks.json", "r") as f:
            template_content = f.read()

        template = Template(template_content)

        context = {
            "alarm_entry": alarm_entry,
            "alarm_history": self.unpack_alarm_history_emoji_name(alarm_entry.history),
            "formatted_time": self.format_time_string(alarm_entry.last_updated),
            "action_url": self.create_action_url(
                self.confluence_base_url, alarm_entry.alarm_name_metric
            ),
        }

        rendered_json = template.render(context)
        return json.loads(rendered_json)

    # To be used when implementing adding reaction to slack message on dynamo entry deletion
    def change_reaction(self, alarm_entry: AlarmEntry, action: str):
        logger.info(
            f"Changing slack reaction for alarm: {alarm_entry.alarm_name_metric}:{alarm_entry.time_created}"
        )

        severity = (
            alarm_entry.history[-2]
            if action == "remove" and len(alarm_entry.history) > 1
            else alarm_entry.history[-1]
        )
        emoji = severity.additional_value

        change_message = {
            "name": emoji,
            "channel": alarm_entry.channel_id,
            "timestamp": alarm_entry.slack_timestamp,
        }

        logger.info(
            f"Changing Slack reaction {action} {emoji} reaction, change message sent to API is {change_message}"
        )

        try:
            change_response = requests.post(
                url=self.SLACK_REACTIONS_API_PREFIX + action,
                json=change_message,
                headers=self.slack_headers,
            )
            logger.info(
                f"{action} {emoji} reaction response: {str(change_response.content)}"
            )
        except HTTPError as e:
            logger.error(
                f"Changing Slack reaction returned HTTP error for alarm {alarm_entry.alarm_name_metric}: {e}"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error changing slack reaction for alarm {alarm_entry.alarm_name_metric}: {e}"
            )
