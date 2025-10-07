from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

METADATA_FILENAME = "metadata.csv"
NHS_NUMBER_FIELD_NAME = "NHS-NO"
ODS_CODE = "GP-PRACTICE-CODE"
NHS_NUMBER_PLACEHOLDER = "0000000000"


def to_upper_case_with_hyphen(field_name: str) -> str:
    return field_name.upper().replace("_", "-")


class MetadataBase(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        populate_by_name=True,
    )

    file_path: str = Field(alias="FILEPATH")
    gp_practice_code: str
    scan_date: str

    @model_validator(mode="after")
    @classmethod
    def ensure_gp_practice_code_non_empty(cls, model):
        gp_code = model.gp_practice_code
        nhs_number = getattr(model, "nhs_number", "<unknown>")

        if not gp_code:
            raise PydanticCustomError(
                "MissingGPPracticeCode",
                "missing GP-PRACTICE-CODE for patient {patient_nhs_number}",
                {"patient_nhs_number": nhs_number},
            )

        return model


class BulkUploadQueueMetadata(MetadataBase):
    stored_file_name: str


class MetadataFile(MetadataBase):
    model_config = ConfigDict(
        alias_generator=to_upper_case_with_hyphen,
    )
    nhs_number: Optional[str] = Field(alias=NHS_NUMBER_FIELD_NAME, default=None)
    page_count: Optional[str] = Field(default=None, alias="PAGE COUNT")
    section: str = None
    sub_section: Optional[str] = None
    scan_id: Optional[str] = None
    user_id: Optional[str] = None
    upload: str


class StagingSqsMetadata(BaseModel):
    nhs_number: str
    files: list[BulkUploadQueueMetadata]
    retries: int = 0

    @field_validator("nhs_number")
    @classmethod
    def validate_nhs_number(cls, nhs_number: str) -> str:
        if nhs_number and nhs_number.isdigit():
            return nhs_number

        return NHS_NUMBER_PLACEHOLDER
