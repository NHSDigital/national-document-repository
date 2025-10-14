from datetime import datetime
from typing import Optional

from enums.metadata_report import MetadataReport
from enums.patient_ods_inactive_status import PatientOdsInactiveStatus
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_pascal
from utils.audit_logging_setup import LoggingService
from utils.utilities import create_reference_id

logger = LoggingService(__name__)


class BulkUploadReport(BaseModel):
    model_config = ConfigDict(alias_generator=to_pascal, validate_by_name=True)
    id: str = Field(alias=MetadataReport.ID, default_factory=create_reference_id)
    nhs_number: str = Field(alias=MetadataReport.NhsNumber)
    upload_status: str = Field(alias=MetadataReport.UploadStatus)
    timestamp: int = Field(
        alias=MetadataReport.Timestamp,
        default_factory=lambda: int(datetime.now().timestamp()),
    )
    date: str = Field(
        alias=MetadataReport.Date,
        default_factory=lambda: date_string_yyyymmdd(datetime.now()),
    )
    file_path: str = Field(alias=MetadataReport.FilePath)
    stored_file_name: Optional[str] = Field(
        alias=MetadataReport.StoredFileName, default=None
    )
    pds_ods_code: str = Field(alias=MetadataReport.PdsOdsCode)
    uploader_ods_code: str = Field(alias=MetadataReport.UploaderOdsCode)
    reason: Optional[str] = Field(default="", alias=MetadataReport.Reason)

    def get_registered_at_uploader_practice_status(self) -> str:
        return (
            self.pds_ods_code
            if self.pds_ods_code in PatientOdsInactiveStatus.list()
            else str(self.uploader_ods_code == self.pds_ods_code)
        )


def date_string_yyyymmdd(time_now: datetime) -> str:
    return time_now.strftime("%Y-%m-%d")
