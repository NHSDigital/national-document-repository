from enum import StrEnum


class MetadataReport(StrEnum):
    NhsNumber = "NhsNumber"
    UploadStatus = "UploadStatus"
    Reason = "Reason"
    PdsOdsCode = "PdsOdsCode"
    UploaderOdsCode = "UploaderOdsCode"
    FilePath = "FilePath"
    StoredFileName = "StoredFileName"
    Date = "Date"
    Timestamp = "Timestamp"
    ID = "ID"
    RegisteredAtUploaderPractice = "RegisteredAtUploaderPractice"
