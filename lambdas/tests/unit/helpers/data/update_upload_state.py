import json

from enums.metadata_field_names import DocumentReferenceMetadataFields
from enums.supported_document_types import SupportedDocumentTypes
from tests.unit.conftest import TEST_FILE_KEY

Fields = DocumentReferenceMetadataFields

MOCK_DOCUMENT_REFERENCE = TEST_FILE_KEY

MOCK_LG_DOCTYPE = SupportedDocumentTypes.LG.value
MOCK_LG_DOCUMENTS_REQUEST = {
    "files": [
        {
            "reference": TEST_FILE_KEY,
            "type": SupportedDocumentTypes.LG.value,
            "fields": {Fields.UPLOADING.value: "true"},
        }
    ]
}

MOCK_ARF_DOCTYPE = SupportedDocumentTypes.ARF.value
MOCK_ARF_DOCUMENTS_REQUEST = {
    "files": [
        {
            "reference": TEST_FILE_KEY,
            "type": SupportedDocumentTypes.ARF.value,
            "fields": {Fields.UPLOADING.value: "true"},
        }
    ]
}

MOCK_ALL_DOCUMENTS_REQUEST = {
    "files": [
        {
            "reference": TEST_FILE_KEY,
            "type": SupportedDocumentTypes.ALL.value,
            "fields": {Fields.UPLOADING.value: "true"},
        }
    ]
}

MOCK_NO_DOCTYPE_REQUEST = {
    "files": [
        {
            "reference": TEST_FILE_KEY,
            "type": "",
            "fields": {Fields.UPLOADING.value: "true"},
        }
    ]
}
MOCK_NO_REFERENCE_REQUEST = {
    "files": [
        {
            "reference": TEST_FILE_KEY,
            "type": "",
            "fields": {Fields.UPLOADING.value: "true"},
        }
    ]
}

MOCK_NO_FIELDS_REQUEST = {
    "files": [
        {
            "reference": TEST_FILE_KEY,
            "type": "",
            "fields": {},
        }
    ]
}

MOCK_NO_FILES_REQUEST = {"test": "test"}

MOCK_BOTH_DOCTYPES = SupportedDocumentTypes.ALL.value

MOCK_VALID_LG_EVENT = {
    "httpMethod": "POST",
    "body": json.dumps(MOCK_LG_DOCUMENTS_REQUEST),
}

MOCK_VALID_ARF_EVENT = {
    "httpMethod": "POST",
    "body": json.dumps(MOCK_ARF_DOCUMENTS_REQUEST),
}

MOCK_INVALID_ALL_EVENT = {
    "httpMethod": "POST",
    "body": json.dumps(MOCK_ALL_DOCUMENTS_REQUEST),
}

MOCK_INVALID_BODY_EVENT = {"httpMethod": "POST", "body": "test"}

MOCK_NO_BODY_EVENT = {"httpMethod": "POST", "test": "test"}
