from enum import Enum


class FhirIssueCoding(Enum):
    INVALID = ("invalid", "Invalid Content")
    FORBIDDEN = ("forbidden", "Forbidden")
    NOT_FOUND = ("not-found", "Not Found")
    EXCEPTION = ("exception", "Exception")
    UNKNOWN = ("unknown", "Unknown User")
    CONFLICT = ("conflict", "Edit Version Conflict")

    @property
    def code(self):
        return self.value[0]

    @property
    def display(self):
        return self.value[1]

    @property
    def system(self):
        return "http://hl7.org/fhir/issue-type"


class UKCoreSpineError(Enum):
    ACCESS_DENIED = ("ACCESS_DENIED", "Access has been denied to process this request")
    RESOURCE_NOT_FOUND = ("RESOURCE_NOT_FOUND", "Resource not found")
    INVALID_RESOURCE_ID = ("INVALID_RESOURCE_ID", "Invalid resource ID")
    INVALID_SEARCH_DATA = ("INVALID_SEARCH_DATA", "Invalid search data")
    MISSING_VALUE = ("MISSING_VALUE", "Missing value")
    INVALID_VALUE = ("INVALID_VALUE", "Invalid value")
    VALIDATION_ERROR = ("VALIDATION_ERROR", "Validation error")

    @property
    def code(self):
        return self.value[0]

    @property
    def display(self):
        return self.value[1]

    @property
    def system(self):
        return "https://fhir.hl7.org.uk/CodeSystem/UKCore-SpineErrorOrWarningCode"
