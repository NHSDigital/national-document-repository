from enum import Enum


class LoggingAppInteraction(Enum):
    LOGIN = "Login"
    EDGE_PRESIGN = "CloudFront Edge Presign"
    PATIENT_SEARCH = "Patient search"
    VIEW_PATIENT = "View Patient"
    VIEW_LG_RECORD = "View LG record"
    DOWNLOAD_RECORD = "Download a record"
    DELETE_RECORD = "Delete a record"
    UPLOAD_RECORD = "Upload a record"
    UPDATE_RECORD = "Update a record"
    STITCH_RECORD = "Stitch a record"
    ODS_REPORT = "Download an ODS report"
    LOGOUT = "Logout"
    SEND_FEEDBACK = "Send feedback"
    FEATURE_FLAGS = "Feature flags"
    VIRUS_SCAN = "Virus Scan"
    UPLOAD_CONFIRMATION = "Upload confirmation"
    UPDATE_UPLOAD_STATE = "Update upload state"
