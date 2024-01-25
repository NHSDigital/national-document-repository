from html import escape

from models.config import to_camel
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Feedback(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    feedback_content: str
    experience: str = Field(alias="howSatisfied")
    respondent_email: str
    respondent_name: str

    @field_validator(
        "feedback_content", "experience", "respondent_email", "respondent_name"
    )
    @classmethod
    def sanitise_string(cls, value: str) -> str:
        # run a html entity encode on incoming values to avoid malicious html injection
        return escape(value)
