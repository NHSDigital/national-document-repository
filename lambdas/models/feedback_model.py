import html

from pydantic import BaseModel, ConfigDict, Field, field_validator, validate_email
from pydantic.alias_generators import to_camel


class Feedback(BaseModel):
    model_config = ConfigDict(validate_by_name=True, alias_generator=to_camel)

    feedback_content: str
    experience: str = Field(alias="howSatisfied")
    respondent_email: str = Field(default="")
    respondent_name: str = Field(default="")

    @field_validator(
        "feedback_content", "experience", "respondent_email", "respondent_name"
    )
    @classmethod
    def sanitise_string(cls, value: str) -> str:
        # run a html entity encode on incoming values to avoid malicious html injection
        return html.escape(value)

    @field_validator("respondent_email")
    @classmethod
    def validate_email_and_allow_blank(cls, email: str) -> str:
        if email == "":
            return email
        return validate_email(email)[1]
