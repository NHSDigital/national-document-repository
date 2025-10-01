import os

from enums.repository_role import RepositoryRole
from services.base.dynamo_service import DynamoDBService
from utils.audit_logging_setup import LoggingService
from utils.exceptions import AuthorisationException
from utils.request_context import request_context
from utils.utilities import redact_id_to_last_4_chars

logger = LoggingService(__name__)


class ManageUserSessionAccess:
    def __init__(self):
        self.db_service = DynamoDBService()

        self.session_table_name = os.getenv("AUTH_SESSION_TABLE_NAME")
        self.permitted_field = "AllowedNHSNumbers"
        self.deceased_field = "DeceasedNHSNumbers"

    def find_login_session(self, ndr_session_id: str):
        logger.info(
            f"Retrieving session for session ID ending in: {redact_id_to_last_4_chars(ndr_session_id)}"
        )
        query_response = self.db_service.query_table(
            table_name=self.session_table_name,
            search_key="NDRSessionId",
            search_condition=ndr_session_id,
        )

        if query_response and len(query_response) > 0:
            current_session = query_response[0]
            return current_session
        raise AuthorisationException(
            f"Unable to find session for session ID ending in: {redact_id_to_last_4_chars(ndr_session_id)}"
        )

    def update_auth_session_with_permitted_search(
        self,
        nhs_number: str,
        write_to_deceased_column: bool,
        user_role: RepositoryRole = None,
    ):
        ndr_session_id = request_context.authorization.get("ndr_session_id")
        current_session = self.find_login_session(ndr_session_id)

        allowed_nhs_numbers = current_session.get(self.permitted_field, "")
        deceased_nhs_numbers = current_session.get(self.deceased_field, "")
        logger.info("Searching Auth session table for existing NHS number")
        if nhs_number in allowed_nhs_numbers:
            logger.info(
                "Permitted search, NHS number already exists in allowed NHS numbers"
            )
            return

        if write_to_deceased_column:
            self.update_auth_session_table_with_new_nhs_number(
                field_name=self.deceased_field,
                nhs_number=nhs_number,
                existing_nhs_numbers=deceased_nhs_numbers,
                ndr_session_id=ndr_session_id,
            )
        if not write_to_deceased_column or user_role == RepositoryRole.PCSE.value:
            self.update_auth_session_table_with_new_nhs_number(
                field_name=self.permitted_field,
                nhs_number=nhs_number,
                existing_nhs_numbers=allowed_nhs_numbers,
                ndr_session_id=ndr_session_id,
            )
        logger.info("Permitted search, NHS number will be added")

    def update_auth_session_table_with_new_nhs_number(
        self,
        field_name: str,
        nhs_number: str,
        existing_nhs_numbers: str,
        ndr_session_id: str,
    ):
        updated_fields = self.create_updated_permitted_search_fields(
            field_name=field_name,
            nhs_number=nhs_number,
            existing_nhs_numbers=existing_nhs_numbers,
        )

        self.db_service.update_item(
            table_name=self.session_table_name,
            key_pair={"NDRSessionId": ndr_session_id},
            updated_fields=updated_fields,
        )

    def create_updated_permitted_search_fields(
        self, field_name, nhs_number: str, existing_nhs_numbers: str
    ) -> dict[str, str]:
        if existing_nhs_numbers:
            existing_nhs_numbers_str = f"{existing_nhs_numbers},{nhs_number}"
            updated_fields = {field_name: existing_nhs_numbers_str}
        else:
            updated_fields = {field_name: nhs_number}

        return updated_fields
