import json
from enum import Enum


class ErrorResponse:
    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        self.message = message

    def create(self) -> str:
        return json.dumps({"message": self.message, "err_code": self.error_code})

    def __eq__(self, other):
        return self.error_code == other.error_code and self.message == other.message


class LambdaError(Enum):
    """
    Errors for SearchPatientException
    """

    SearchPatientMissing = {"code": "SP_1001", "message": "Missing user details"}
    SearchPatientNoPDS = {
        "code": "SP_1002",
        "message": "Patient does not exist for given NHS number",
    }
    SearchPatientNoAuth = {
        "code": "SP_1003",
        "message": "Patient does not exist for given NHS number",
    }
    SearchPatientNoId = {
        "code": "SP_1004",
        "message": "An error occurred while searching for patient",
    }
    SearchPatientNoParse = {"code": "SP_1005", "message": "Failed to parse PDS data"}

    """
       Errors for CreateDocumentRefException
    """
    CreateDocNoBody = {"code": "CDR_1001", "message": "Missing event body"}
    CreateDocPayload = {"code": "CDR_1002", "message": "Invalid json in body"}
    CreateDocProps = {
        "code": "CDR_1003",
        "message": "Request body missing some properties",
    }
    CreateDocFiles = {"code": "CDR_1004", "message": "Invalid files or id"}
    CreateDocNoParse = {
        "code": "CDR_1005",
        "message": "Failed to parse document upload request data",
    }
    CreateDocNoType = {
        "code": "CDR_1006",
        "message": "Failed to parse document upload request data",
    }
    CreateDocInvalidType = {
        "code": "CDR_1007",
        "message": "Failed to parse document upload request data",
    }
    CreateDocPresign = {"code": "CDR_5001", "message": "Internal error"}
    CreateDocUpload = {"code": "CDR_5002", "message": "Internal error"}

    """
       Errors for InvalidDocTypeException
    """
    DocTypeDB = {
        "code": "DT_5001",
        "message": "Failed to resolve dynamodb table name for this document",
    }

    """
       Errors for LoginException
    """
    LoginNoState = {
        "code": "LIN_1001",
        "message": "No auth code and/or state in the query string parameters",
    }
    LoginBadState = {
        "code": "LIN_2001",
        "message": "Unrecognised state value",
    }

    LoginBadAuth = {
        "code": "LIN_2002",
        "message": "Cannot log user in, expected information from CIS2 is missing",
    }
    LoginNoOrg = {"code": "LIN_2003", "message": "No org found for given ODS code"}
    LoginNullOrgs = {"code": "LIN_2004", "message": "No orgs found for user"}
    LoginNoRole = {"code": "LIN_2005", "message": "Unable to remove used state value"}
    LoginValidate = {
        "code": "LIN_5001",
        "message": "Unrecognised state value",
    }
    LoginNoContact = {
        "code": "LIN_5002",
        "message": "Issue when contacting CIS2",
    }
    LoginOds = {"code": "LIN_5003", "message": "Bad response from ODS API"}
    LoginStateFault = {
        "code": "LIN_5004",
        "message": "Unable to remove used state value",
    }
    LoginBadSSM = {
        "code": "LIN_5005",
        "message": "Failed to find SSM parameter value for user role",
    }
    LoginNoSSM = {
        "code": "LIN_5006",
        "message": "Failed to find SSM parameter value for user role",
    }
    LoginSmartSSM = {
        "code": "LIN_5007",
        "message": "Failed to find SSM parameter value for user role",
    }
    LoginPcseSSM = {
        "code": "LIN_5008",
        "message": "Failed to find SSM parameter value for user role",
    }
    LoginGpSSM = {
        "code": "LIN_5009",
        "message": "Failed to find SSM parameter value for user role",
    }
    LoginPcseODS = {
        "code": "LIN_5010",
        "message": "SSM parameter values for PSCE ODS code may not exist",
    }

    """
       Errors for DocumentManifestServiceException
    """
    ManifestNoDocs = {
        "code": "DMS_4001",
        "message": "No documents found for given NHS number and document type",
    }
    ManifestValidation = {
        "code": "DMS_5001",
        "message": "Failed to parse document reference from from DynamoDb response",
    }
    ManifestDB = {
        "code": "DMS_5002",
        "message": "Failed to create document manifest",
    }
    ManifestClient = {
        "code": "DMS_5003",
        "message": "Failed to create document manifest",
    }

    """
       Errors for LGStitchServiceException
    """
    StitchNotFound = {
        "code": "LGS_4001",
        "message": "Lloyd george record not found for patient",
    }
    StitchNoService = {
        "code": "LGS_5001",
        "message": "Unable to retrieve documents for patient",
    }
    StitchNoClient = {
        "code": "LGS_5002",
        "message": "Unable to return stitched pdf file due to internal error",
    }
    StitchClient = {
        "code": "LGS_5003",
        "message": "Unable to retrieve documents for patient",
    }
    StitchFailed = {
        "code": "LGS_5004",
        "message": "Unable to retrieve documents for patient",
    }

    """
       Errors for DocumentRefSearchException
    """
    DocRefClient = {
        "code": "DRS_5001",
        "message": "An error occurred when searching for available documents",
    }

    """
       Errors for DocumentDeletionServiceException
    """
    DocDelClient = {
        "code": "DDS_5001",
        "message": "Failed to delete documents",
    }

    """
       Errors with no exception
    """
    DocDelNull = {
        "code": "DDS_4001",
        "message": "Failed to delete documents",
    }
    LoginNoAuth = {
        "code": "LIN_1002",
        "message": "No auth code and/or state in the query string parameters",
    }
    LogoutClient = {
        "code": "OUT_5001",
        "message": "Error logging user out",
    }
    LogoutAuth = {"code": "OUT_4001", "message": "Invalid Authorization header"}
    EnvMissing = {
        "code": "ENV_5001",
        "message": "An error occurred due to missing environment variable: '%name%'",
    }
    DocTypeNull = {"code": "VDT_4001", "message": "docType not supplied"}
    DocTypeInvalid = {"code": "VDT_4002", "message": "Invalid document type requested"}
    DocTypeKey = {"code": "VDT_4003", "message": "An error occurred due to missing key"}
    PatientIdInvalid = {"code": "PN_4001", "message": "Invalid patient number %number%"}
    PatientIdNoKey = {
        "code": "PN_4002",
        "message": "An error occurred due to missing key",
    }
    GatewayError = {
        "code": "GWY_5001",
        "message": "Failed to utilise AWS client/resource",
    }
