import json
import os
import uuid

import requests
from requests.adapters import HTTPAdapter
from services.base.nhs_oauth_service import NhsOauthService
from urllib3 import Retry
from utils.audit_logging_setup import LoggingService

logger = LoggingService(__name__)


class NrlApiService(NhsOauthService):
    def __init__(self, ssm_service):
        super().__init__(ssm_service)
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            backoff_factor=1,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.endpoint = os.getenv("NRL_API_ENDPOINT")
        self.session = requests.Session()
        self.session.mount("https://", adapter)
        self.end_user_ods_code = os.getenv("NRL_END_USER_ODS_CODE", "")
        self.headers = {
            "Authorization": f"Bearer {self.create_access_token()}",
            "NHSD-End-User-Organisation-ODS": self.end_user_ods_code,
        }

    def create_new_pointer(self, body):
        self.set_x_request_id()
        headers = self.headers
        headers["Accept"] = "application/json"
        response = self.session.post(
            url=self.endpoint, headers=headers, json=json.loads(body)
        )
        response.raise_for_status()

    def update_pointer(self):
        self.set_x_request_id()

    def delete_pointer(self):
        self.set_x_request_id()

    def set_x_request_id(self):
        self.headers["X-Request-ID"] = str(uuid.uuid4())
