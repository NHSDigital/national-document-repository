from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator
from pydantic_core import PydanticCustomError

METADATA_FILENAME = "metadata.csv"
NHS_NUMBER_FIELD_NAME = "NHS-NO"
ODS_CODE = "GP-PRACTICE-CODE"
NHS_NUMBER_PLACEHOLDER = "0000000000"


def to_upper_case_with_hyphen(field_name: str) -> str:
    return field_name.upper().replace("_", "-")


class MetadataBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_upper_case_with_hyphen,
        validate_by_name=True,
        populate_by_name=True,
    )

    file_path: str = Field(alias="FILEPATH")
    nhs_number: Optional[str] = Field(
        alias=NHS_NUMBER_FIELD_NAME, exclude=True, default=None
    )
    gp_practice_code: str
    scan_date: str

    @field_validator("gp_practice_code")
    @classmethod
    def ensure_gp_practice_code_non_empty(
        cls, gp_practice_code: str, info: ValidationInfo
    ) -> str:
        if not gp_practice_code:
            patient_nhs_number = info.data.get("nhs_number", "")
            raise PydanticCustomError(
                "MissingGPPracticeCode",
                "missing GP-PRACTICE-CODE for patient {patient_nhs_number}",
                {"patient_nhs_number": patient_nhs_number},
            )
        return gp_practice_code


class SqsMetadata(MetadataBase):
    stored_file_name: str = Field(alias="STORED-FILE-NAME")


class MetadataFile(MetadataBase):
    page_count: str = Field(alias="PAGE COUNT")
    section: str
    sub_section: Optional[str]
    scan_id: str
    user_id: str
    upload: str


class StagingSqsMetadata(BaseModel):
    model_config = ConfigDict(validate_by_name=True)

    nhs_number: str = Field(default=NHS_NUMBER_PLACEHOLDER, alias=NHS_NUMBER_FIELD_NAME)
    files: list[SqsMetadata]
    retries: int = 0

    @field_validator("nhs_number")
    @classmethod
    def validate_nhs_number(cls, nhs_number: str) -> str:
        if nhs_number and nhs_number.isdigit():
            return nhs_number

        return NHS_NUMBER_PLACEHOLDER
