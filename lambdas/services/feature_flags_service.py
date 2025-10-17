import os

import requests
from enums.feature_flags import FeatureFlags
from enums.lambda_error import LambdaError
from models.feature_flags import FeatureFlag
from pydantic import ValidationError
from requests.exceptions import JSONDecodeError
from services.base.ssm_service import SSMService
from utils.audit_logging_setup import LoggingService
from utils.constants.ssm import UPLOAD_PILOT_ODS_ALLOWED_LIST
from utils.lambda_exceptions import FeatureFlagsException
from utils.request_context import request_context

logger = LoggingService(__name__)


class FeatureFlagService:
    def __init__(self):
        app_config_port = 2772
        self.app_config_url = (
            f"http://localhost:{app_config_port}"
            + f'/applications/{os.environ["APPCONFIG_APPLICATION"]}'
            + f'/environments/{os.environ["APPCONFIG_ENVIRONMENT"]}'
            + f'/configurations/{os.environ["APPCONFIG_CONFIGURATION"]}'
        )
        self.ssm_service = SSMService()

    @staticmethod
    def request_app_config_data(url: str):
        config_data = requests.get(url)
        try:
            data = config_data.json()
        except JSONDecodeError as e:
            logger.error(
                str(e),
                {"Result": "Error when retrieving feature flag from AppConfig profile"},
            )
            raise FeatureFlagsException(
                error=LambdaError.FeatureFlagParseError,
                status_code=config_data.status_code,
            )

        if config_data.status_code == 200:
            return data
        if config_data.status_code == 400:
            logger.error(
                str(data),
                {"Result": "Error when retrieving feature flag from AppConfig profile"},
            )
            raise FeatureFlagsException(
                error=LambdaError.FeatureFlagNotFound,
                status_code=404,
            )
        else:
            logger.error(
                str(data),
                {"Result": "Error when retrieving feature flag from AppConfig profile"},
            )
            raise FeatureFlagsException(
                error=LambdaError.FeatureFlagFailure,
                status_code=config_data.status_code,
            )

    def get_feature_flags(self) -> dict:
        logger.info("Retrieving all feature flags")

        url = self.app_config_url
        response = self.request_app_config_data(url)

        try:
            feature_flags = FeatureFlag(feature_flags=response)
            formatted_flags = feature_flags.format_flags()

            if not self.check_if_ods_code_is_in_pilot():
                for flag in formatted_flags:
                    if flag in [
                        FeatureFlags.UPLOAD_LLOYD_GEORGE_WORKFLOW_ENABLED,
                        FeatureFlags.UPLOAD_LAMBDA_ENABLED,
                    ]:
                        formatted_flags[flag] = False

            return formatted_flags
        except ValidationError as e:
            logger.error(
                str(e),
                {"Result": "Error when retrieving feature flag from AppConfig profile"},
            )
            raise FeatureFlagsException(
                error=LambdaError.FeatureFlagParseError,
                status_code=500,
            )

    def get_feature_flags_by_flag(self, flag: str):
        logger.info(f"Retrieving feature flag: {flag}")

        config_url = self.app_config_url
        url = config_url + f"?flag={flag}"

        response = self.request_app_config_data(url)

        try:
            feature_flag = FeatureFlag(feature_flags={flag: response})
            formatted_feature_flag = feature_flag.format_flags()

            if (
                flag
                in [
                    FeatureFlags.UPLOAD_LLOYD_GEORGE_WORKFLOW_ENABLED,
                    FeatureFlags.UPLOAD_LAMBDA_ENABLED,
                    FeatureFlags.ADD_DOCUMENT_ENABLED,
                ]
                and not self.check_if_ods_code_is_in_pilot()
            ):
                formatted_feature_flag[flag] = False

            return formatted_feature_flag
        except ValidationError as e:
            logger.error(
                str(e),
                {"Result": "Error when retrieving feature flag from AppConfig profile"},
            )
            raise FeatureFlagsException(
                error=LambdaError.FeatureFlagParseError,
                status_code=500,
            )

    def get_allowed_list_of_ods_codes_for_upload_pilot(self) -> list[str]:
        logger.info(
            "Starting ssm request to retrieve allowed list of ODS codes for Upload Pilot"
        )
        response = self.ssm_service.get_ssm_parameter(UPLOAD_PILOT_ODS_ALLOWED_LIST)
        if not response:
            logger.warning("No ODS codes found in allowed list for Upload Pilot")
            return []
        return response.split(",")

    def check_if_ods_code_is_in_pilot(self) -> bool:
        ods_code = ""

        if isinstance(request_context.authorization, dict):
            ods_code = request_context.authorization.get(
                "selected_organisation", {}
            ).get("org_ods_code", "")

        if not ods_code:
            return False
        pilot_ods_codes = self.get_allowed_list_of_ods_codes_for_upload_pilot()

        return ods_code in pilot_ods_codes
