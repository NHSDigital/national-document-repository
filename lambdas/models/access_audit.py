import re
from datetime import datetime
from typing import Any

from enums.access_audit_request_type import AccessAuditRequestType
from enums.deceased_access_reason import DeceasedAccessReason
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_pascal


class AccessAuditReason(BaseModel):
    model_config = ConfigDict(validate_by_name=True, alias_generator=to_pascal)
    nhs_number: str = Field(exclude=True)
    request_type: AccessAuditRequestType = Field(exclude=True)
    user_session_id: str
    user_id: str
    user_ods_code: str
    timestamp: int = Field(
        default_factory=lambda: int(datetime.now().timestamp()),
    )
    reason_codes: set[str]
    custom_reason: str | None = None

    @computed_field(alias="ID")
    def id(self) -> str:
        return f"{self.user_session_id}#{self.timestamp}"

    @computed_field()
    def type(self) -> str:
        return f"LloydGeorge#{self.nhs_number}#{self.request_type.additional_value}"

    @field_validator("request_type", mode="before")
    @classmethod
    def validate_request_type(cls, value):
        if value not in AccessAuditRequestType.list():
            raise ValueError("Invalid request type")
        return AccessAuditRequestType(value)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def reason_codes(cls, value):
        validate_reasons = set()
        for reason_code in value:
            if reason_code in DeceasedAccessReason.list():
                validate_reasons.add(DeceasedAccessReason(reason_code).additional_value)
        if not validate_reasons:
            raise ValueError("No valid reason code provided")
        return validate_reasons

    @field_validator("custom_reason")
    @classmethod
    def sanitise_custom_reason(cls, value):
        """
        Sanitise the custom reason text to prevent DynamoDB-specific injection issues.
        """
        if value is None:
            return None

        # Remove control characters that could affect JSON parsing
        value = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", value)

        # Clean up potentially malicious placeholders used in DynamoDB expressions
        # DynamoDB uses :name for expression attribute values
        value = re.sub(r"(:[\w]+)", lambda m: m.group(0).replace(":", "﹕"), value)

        # DynamoDB uses #name for expression attribute names
        value = re.sub(r"(#[\w]+)", lambda m: m.group(0).replace("#", "＃"), value)

        # Replace $ (sometimes used in NoSQL injections) with safe character
        value = value.replace("$", "＄")

        max_length = 10000
        if len(value) > max_length:
            raise ValueError("Invalid custom reason text")

        return value

    @model_validator(mode="before")
    @classmethod
    def check_custom_reason(cls, data: Any) -> Any:
        if (
            DeceasedAccessReason.OTHER.value in data["reason_codes"]
            and not data["custom_reason"]
        ):
            raise ValueError("Missing custom reason")
        return data
