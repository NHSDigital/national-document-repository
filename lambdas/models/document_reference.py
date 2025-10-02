import pathlib
from datetime import datetime, timezone
from typing import Literal, Optional

from enums.metadata_field_names import DocumentReferenceMetadataFields
from enums.snomed_codes import SnomedCodes
from enums.supported_document_types import SupportedDocumentTypes
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel, to_pascal

# Constants
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
DEFAULT_CONTENT_TYPE = "application/pdf"
S3_PREFIX = "s3://"
THREE_MINUTES_IN_SECONDS = 60 * 3


class UploadRequestDocument(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    fileName: str
    contentType: str
    docType: SupportedDocumentTypes
    clientId: str


class UploadDocumentReference(BaseModel):
    reference: str = Field(...)
    doc_type: SupportedDocumentTypes = Field(..., alias="type")
    fields: dict[str, bool] = Field(...)


class UploadDocumentReferences(BaseModel):
    files: list[UploadDocumentReference] = Field(...)


class DocumentReference(BaseModel):
    model_config = ConfigDict(
        validate_by_alias=True,
        validate_by_name=True,
        alias_generator=to_pascal,
        use_enum_values=True,
    )

    id: str = Field(..., alias=str(DocumentReferenceMetadataFields.ID.value))
    author: str = Field(default=None)
    content_type: str = Field(default=DEFAULT_CONTENT_TYPE)
    created: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime(DATE_FORMAT)
    )
    document_scan_creation: Optional[str] = Field(
        default_factory=lambda: datetime.date(datetime.now()).isoformat(),
    )
    current_gp_ods: str = Field(default=None)
    custodian: str = Field(default=None)
    deleted: str = Field(default=None)
    doc_status: Literal[
        "registered",
        "partial",
        "preliminary",
        "final",
        "amended",
        "corrected",
        "appended",
        "cancelled",
        "entered-in-error",
        "deprecated",
        "unknown",
        "superseded",
    ] = Field(default="preliminary")
    doc_type: str = Field(default=None, exclude=True)
    document_snomed_code_type: Optional[str] = Field(
        default=SnomedCodes.LLOYD_GEORGE.value.code
    )
    file_location: str = ""
    file_name: str
    file_size: int = Field(default=None)
    last_updated: int = Field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp()),
    )
    nhs_number: str
    s3_bucket_name: str = Field(exclude=True, default=None)
    s3_file_key: str = Field(exclude=True, default=None)
    status: Literal["current", "superseded", "entered-in-error"] = Field(
        default="current"
    )
    sub_folder: str = Field(default=None, exclude=True)
    ttl: Optional[int] = Field(
        alias=str(DocumentReferenceMetadataFields.TTL.value), default=None
    )
    uploaded: bool = Field(default=None)
    uploading: bool = Field(default=None)
    version: str = Field(default="1")
    virus_scanner_result: str = Field(default=None)

    def model_dump_camel_case(self, *args, **kwargs):
        model_dump_results = self.model_dump(*args, **kwargs)
        camel_case_model_dump_results = {}
        for key in model_dump_results:
            camel_case_model_dump_results[to_camel(key)] = model_dump_results[key]
        return camel_case_model_dump_results

    @model_validator(mode="before")
    @classmethod
    def set_location_properties(cls, data, *args, **kwargs):
        """Set S3 location properties based on available data."""
        if "file_location" in data or "FileLocation" in data:
            file_location = data.get("file_location") or data.get("FileLocation")
            bucket, key = cls._parse_s3_location(file_location)
            data["s3_bucket_name"] = bucket
            data["s3_file_key"] = key
        elif "s3_bucket_name" in data:
            data["s3_file_key"] = cls._build_s3_key(data)
            data["file_location"] = cls._build_s3_location(
                data["s3_bucket_name"], data["s3_file_key"]
            )
        return data

    @staticmethod
    def _parse_s3_location(file_location: str) -> list[str]:
        """Parse S3 location into bucket and key components."""
        location_without_prefix = file_location.replace(S3_PREFIX, "")
        return location_without_prefix.split("/", 1)

    @staticmethod
    def _build_s3_key(data: dict) -> str:
        """Build the S3 key from document data."""
        key_parts = []

        if "sub_folder" in data:
            key_parts = data["sub_folder"].split("/")
            if "doc_type" in data:
                key_parts.append(data["doc_type"])

        key_parts.extend([data["nhs_number"], data["id"]])
        s3_key = "/".join(key_parts)

        return s3_key

    @staticmethod
    def _build_s3_location(bucket: str, key: str) -> str:
        """Build a complete S3 location from bucket and key."""
        normalized_key = key[1:] if key.startswith("/") else key
        return f"{S3_PREFIX}{bucket}/{normalized_key}"

    # File path handling methods
    def get_file_name_path(self):
        return pathlib.Path(self.file_name)

    def get_base_name(self):
        return self.get_file_name_path().stem

    def get_file_extension(self):
        return self.get_file_name_path().suffix

    def create_unique_filename(self, duplicates: int):
        return f"{self.get_base_name()}({duplicates}){self.get_file_extension()}"

    # Status methods
    def last_updated_within_three_minutes(self) -> bool:
        three_minutes_ago = (
            datetime.now(timezone.utc).timestamp() - THREE_MINUTES_IN_SECONDS
        )
        return self.last_updated >= three_minutes_ago

    def set_deleted(self) -> None:
        self.deleted = datetime.now(timezone.utc).strftime(DATE_FORMAT)

    def set_virus_scanner_result(self, updated_virus_scanner_result) -> None:
        self.virus_scanner_result = updated_virus_scanner_result

    def set_uploaded_to_true(self):
        self.uploaded = True
