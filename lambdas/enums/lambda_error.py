from enum import Enum
from typing import Optional

from enums.fhir.fhir_issue_type import FhirIssueCoding, UKCoreSpineError
from utils.error_response import ErrorResponse
from utils.request_context import request_context


class LambdaError(Enum):
    MISSING_POST = "Missing POST request body"
    MISSING_KEY = "An error occurred due to missing key"
    RETRIEVE_DOCUMENTS = "Unable to retrieve documents for patient"

    def create_error_response(
        self, params: Optional[dict] = None, **kwargs
    ) -> ErrorResponse:
        err_code = self.value["err_code"]
        message = self.value["message"]
        if "%" in message and params:
            message = message % params
        interaction_id = getattr(request_context, "request_id", None)
        error_response = ErrorResponse(
            err_code=err_code, message=message, interaction_id=interaction_id, **kwargs
        )
        return error_response

    def to_str(self) -> str:
        return f"[{self.value['err_code']}] {self.value['message']}"

    def create_error_body(self, params: Optional[dict] = None, **kwargs) -> str:
        return self.create_error_response(params, **kwargs).create()

    """
    Errors for SearchPatientException
    """

    SearchPatientMissing = {
        "err_code": "SP_4001",
        "message": "Missing user details",
        "fhir_coding": UKCoreSpineError.MISSING_VALUE,
    }
    SearchPatientNoPDS = {
        "err_code": "SP_4002",
        "message": "Patient does not exist for given NHS number",
        "fhir_coding": UKCoreSpineError.RESOURCE_NOT_FOUND,
    }
    SearchPatientNoAuth = {
        "err_code": "SP_4003",
        "message": "You do not have access to this patient's record",
        "fhir_coding": UKCoreSpineError.ACCESS_DENIED,
    }
    SearchPatientNoId = {
        "err_code": "SP_4004",
        "message": "An error occurred while searching for patient",
        "fhir_coding": FhirIssueCoding.EXCEPTION,
    }
    SearchPatientNoParse = {
        "err_code": "SP_4005",
        "message": "Failed to parse PDS data",
        "fhir_coding": UKCoreSpineError.VALIDATION_ERROR,
    }

    """
       Errors for CreateDocumentRefException
    """
    CreateDocNoBody = {"err_code": "CDR_4001", "message": "Missing event body"}
    CreateDocPayload = {"err_code": "CDR_4002", "message": "Invalid json in body"}
    CreateDocProps = {
        "err_code": "CDR_4003",
        "message": "Request body missing some properties",
    }
    CreateDocFiles = {"err_code": "CDR_4004", "message": "Invalid files or id"}
    CreateDocNoParse = {
        "err_code": "CDR_4005",
        "message": "Failed to parse document upload request data",
        "fhir_coding": UKCoreSpineError.VALIDATION_ERROR,
    }
    CreateDocNoType = {
        "err_code": "CDR_4006",
        "message": "Failed to parse document upload request data due to missing document type",
        "fhir_coding": UKCoreSpineError.MISSING_VALUE,
    }
    CreateDocInvalidType = {
        "err_code": "CDR_4007",
        "message": "Failed to parse document upload request data due to invalid document type",
        "fhir_coding": UKCoreSpineError.INVALID_VALUE,
    }
    CreateDocRecordAlreadyInPlace = {
        "err_code": "CDR_4008",
        "message": "The patient already has a full set of record.",
    }
    CreateDocRefOdsCodeNotAllowed = {
        "err_code": "CDR_4009",
        "message": "ODS code does not match any of the allowed.",
    }
    CreateDocPresign = {
        "err_code": "CDR_5001",
        "message": "An error occurred when creating pre-signed url for document reference",
    }
    CreateDocUploadInternalError = {
        "err_code": "CDR_5002",
        "message": "An error occurred when creating pre-signed url for document reference",
    }
    CreatePatientSearchInvalid = {
        "err_code": "CDR_5003",
        "message": "Failed to validate patient",
        "fhir_coding": UKCoreSpineError.VALIDATION_ERROR,
    }

    """
       Errors for InvalidDocTypeException
    """
    DocTypeDB = {
        "err_code": "DT_5001",
        "message": "Failed to resolve dynamodb table name for this document",
    }

    """
       Errors for LoginRedirectException
    """
    RedirectClient = {
        "err_code": "LR_5001",
        "message": "Unsuccessful redirect",
    }

    """
       Errors for LoginException
    """
    LoginNoState = {
        "err_code": "LIN_4001",
        "message": "No auth err_code and/or state in the query string parameters",
    }
    LoginBadState = {
        "err_code": "LIN_4002",
        "message": "Unrecognised state value",
    }

    LoginBadAuth = {
        "err_code": "LIN_4003",
        "message": "Cannot log user in, expected information from CIS2 is missing",
    }
    LoginNoOrg = {
        "err_code": "LIN_4004",
        "message": "No org found for given ODS err_code",
    }
    LoginNullOrgs = {"err_code": "LIN_4005", "message": "No orgs found for user"}
    LoginNoRole = {
        "err_code": "LIN_4006",
        "message": "Unable to remove used state value",
    }
    LoginClient = {
        "err_code": "LIN_5001",
        "message": "Unrecognised state value",
    }
    LoginNoContact = {
        "err_code": "LIN_5002",
        "message": "Issue when contacting CIS2",
    }
    LoginOds = {"err_code": "LIN_5003", "message": "Bad response from ODS API"}
    LoginStateFault = {
        "err_code": "LIN_5004",
        "message": "Unable to remove used state value",
    }
    LoginNoSSM = {
        "err_code": "LIN_5005",
        "message": "SSM parameter values for GP admin/clinical or PCSE roles may not exist",
    }
    LoginAdminSSM = {
        "err_code": "LIN_5006",
        "message": "SSM parameter values for GP admin role may not exist",
    }
    LoginClinicalSSM = {
        "err_code": "LIN_5007",
        "message": "SSM parameter values for GP clinical user role may not exist",
    }
    LoginPcseSSM = {
        "err_code": "LIN_5008",
        "message": "SSM parameter values for PCSE user role may not exist",
    }
    LoginGpOrgRoleCode = {
        "err_code": "LIN_5009",
        "message": "SSM parameter value for GP organisation role code may not exist",
    }
    LoginPcseOdsCode = {
        "err_code": "LIN_5010",
        "message": "SSM parameter value for PCSE ODS code may not exist",
    }
    LoginItocOdsCodes = {
        "err_code": "LIN_5011",
        "message": "SSM parameter value for ITOC ODS code may not exist",
    }

    """
       Errors for DocumentManifestJobServiceException
    """
    ManifestNoDocs = {
        "err_code": "DMS_4001",
        "message": "No documents found for given NHS number and document type",
    }
    ManifestMissingBody = {
        "err_code": "DMS_4002",
        "message": MISSING_POST,
    }
    ManifestFilterDocumentReferences = {
        "err_code": "DMS_4003",
        "message": "Selected document references do not match any documents stored for this patient",
    }
    ManifestMissingJobId = {
        "err_code": "DMS_4004",
        "message": MISSING_KEY,
    }
    ManifestMissingJob = {
        "err_code": "DMS_4005",
        "message": "No Document Manifest found",
    }
    ManifestValidation = {
        "err_code": "DMS_5001",
        "message": "Failed to validate zip trace model from dynamo event",
    }
    ManifestFailure = {
        "err_code": "DMS_5002",
        "message": "Failed to create document manifest",
    }

    """
       Errors for LGStitchServiceException
    """
    StitchNotFound = {
        "err_code": "LGS_4001",
        "message": "Lloyd george record not found for patient",
    }
    StitchNoService = {
        "err_code": "LGS_5001",
        "message": RETRIEVE_DOCUMENTS,
    }
    StitchClient = {
        "err_code": "LGS_5002",
        "message": "Unable to return stitched pdf file due to internal error",
    }
    StitchDB = {
        "err_code": "LGS_5003",
        "message": RETRIEVE_DOCUMENTS,
    }
    StitchValidation = {
        "err_code": "LGS_5004",
        "message": RETRIEVE_DOCUMENTS,
    }
    StitchCloudFront = {
        "err_code": "LGS_5005",
        "message": "CloudFront format url failure",
    }
    StitchDBValidation = {
        "err_code": "LGS_5006",
        "message": "Failed to validate stitch trace model from dynamo event",
    }

    """
       Errors for DocumentRefSearchException
    """
    DocRefClient = {
        "err_code": "DRS_5001",
        "message": "An error occurred when searching for available documents",
        "fhir_coding": FhirIssueCoding.EXCEPTION,
    }

    """
       Errors for DocumentDeletionServiceException
    """
    DocDelInvalidStreamEvent = {
        "err_code": "DDS_4001",
        "message": "Failed to delete document object",
    }
    DocDelObjectFailure = {
        "err_code": "DDS_4002",
        "message": "Failed to delete document object",
    }
    DocDelClient = {
        "err_code": "DDS_5001",
        "message": "Failed to delete documents",
    }

    """
       Errors for Send Feedback lambda 
    """
    FeedbackMissingBody = {
        "err_code": "SFB_4001",
        "message": MISSING_POST,
    }

    FeedbackInvalidBody = {
        "err_code": "SFB_4002",
        "message": "Invalid POST request body",
    }

    FeedbackSESFailure = {
        "err_code": "SFB_5001",
        "message": "Error occur when sending email by SES",
    }

    FeedbackFetchParamFailure = {
        "err_code": "SFB_5002",
        "message": "Failed to fetch parameters for sending email from SSM param store",
    }

    """
       Errors for Feature Flags lambda 
    """
    FeatureFlagNotFound = {
        "err_code": "FFL_4001",
        "message": "Feature flag/s may not exist in AppConfig profile",
    }

    FeatureFlagParseError = {
        "err_code": "FFL_5001",
        "message": "Failed to parse feature flag/s from AppConfig response",
    }

    FeatureFlagFailure = {
        "err_code": "FFL_5002",
        "message": "Failed to retrieve feature flag/s from AppConfig profile",
    }

    FeatureFlagDisabled = {
        "err_code": "FFL_5003",
        "message": "Feature is not enabled",
    }

    """
       Errors for Virus Scan lambda 
    """
    VirusScanNoBody = {"err_code": "VSR_4001", "message": "Missing event body"}
    VirusScanUnclean = {
        "err_code": "VSR_4002",
        "message": "Virus scanner failed",
    }
    VirusScanNoDocumentType = {
        "err_code": "VSR_4003",
        "message": "Document reference is missing a document type",
    }
    VirusScanTokenRequest = {
        "err_code": "VSR_5001",
        "message": "Virus scanner failed to fetch token",
    }
    VirusScanNoToken = {
        "err_code": "VSR_5002",
        "message": "Virus scanner failed to create new token",
    }
    VirusScanFailedRequest = {
        "err_code": "VSR_5003",
        "message": "Virus scanner failed request",
    }
    VirusScanAWSFailure = {
        "err_code": "VSR_5004",
        "message": "Error occurred with an AWS service",
    }

    """
       Errors for Upload Confirm Result lambda 
    """
    UploadConfirmResultMissingParams = {
        "err_code": "UC_4001",
        "message": "Missing GET request query parameters",
    }

    UploadConfirmResultFilesNotClean = {
        "err_code": "UC_4005",
        "message": "Some of the given document references are not referring to clean files",
    }
    UploadConfirmResultAWSFailure = {
        "err_code": "UC_5004",
        "message": "Error occurred with an AWS service",
    }

    """
       Errors for Generate Manifest Zip lambda 
    """

    JobIdNotFound = {
        "err_code": "GMZ_4001",
        "message": "Could not locate job id in DynamoDB",
    }

    DuplicateJobId = {
        "err_code": "GMZ_4002",
        "message": "Multiple items found with job id",
    }

    FailedToQueryDynamo = {"err_code": "GMZ_5001", "message": "Dynamo client error"}
    ZipServiceClientError = {
        "err_code": "GMZ_5002",
        "message": "Failed to generate document manifest",
    }
    """
       Errors for Update Upload State lambda 
    """
    UpdateUploadStateMissingBody = {
        "err_code": "US_4001",
        "message": "Missing request body",
    }
    UpdateUploadStateValidation = {
        "err_code": "US_4002",
        "message": "Missing fields",
    }
    UpdateUploadStateDocType = {
        "err_code": "US_4003",
        "message": "Doctype invalid",
    }
    UpdateUploadStateKey = {
        "err_code": "US_4004",
        "message": "Key or type error on request",
    }
    UpdateUploadStateInvalidBody = {
        "err_code": "US_4005",
        "message": "Invalid request body",
    }
    UpdateUploadStateFieldType = {
        "err_code": "US_4006",
        "message": "Invalid field type",
    }
    UpdateUploadStateClient = {
        "err_code": "US_5001",
        "message": "Dynamo client error",
    }
    """
       Errors for fhir get document reference lambda 
    """
    DocumentReferenceNotFound = {
        "err_code": "NRL_DR_4041",
        "message": "Document reference not found",
        "fhir_coding": UKCoreSpineError.RESOURCE_NOT_FOUND,
    }
    DocumentReferenceGeneralError = {
        "err_code": "NRL_DR_4002",
        "message": "An error occurred while fetching the document",
        "fhir_coding": FhirIssueCoding.EXCEPTION,
    }
    DocumentReferenceUnauthorised = {
        "err_code": "NRL_DR_4011",
        "message": "The user was not able to be authenticated",
        "fhir_coding": UKCoreSpineError.ACCESS_DENIED,
    }
    DocumentReferenceMissingParameters = {
        "err_code": "NRL_DR_4001",
        "message": "Missing request parameters",
        "fhir_coding": UKCoreSpineError.MISSING_VALUE,
    }

    DocumentReferenceForbidden = {
        "err_code": "NRL_DR_4031",
        "message": "User is unauthorised to view record",
        "fhir_coding": UKCoreSpineError.ACCESS_DENIED,
    }
    """
       Errors for get ods report lambda 
    """
    NoDataFound = {
        "err_code": "OR_4041",
        "message": "No data found for requested ods code",
    }
    UnsupportedFileType = {
        "err_code": "OR_4001",
        "message": "Failed to process unsupported file type",
    }
    """
       Errors for get access audit lambda 
    """
    InvalidReasonInput = {
        "err_code": "AA_4001",
        "message": "Invalid reason code",
    }
    """
       Errors for PDF Stitching lambda 
    """
    MultipartError = {
        "err_code": "PS_4001",
        "message": "Failed to process multipart",
    }
    StitchError = {
        "err_code": "PS_4002",
        "message": "Failed to process PDF stitching",
    }
    StitchRollbackError = {
        "err_code": "PS_5001",
        "message": "Failed to rollback PDF stitching",
    }
    """
        Edge Lambda Errors
    """
    EdgeMalformed = {
        "err_code": "CE_5001",
        "message": "Malformed cloudfront request",
    }

    EdgeNoOrigin = {
        "err_code": "CE_5002",
        "message": "The request is missing an origin",
    }

    EdgeNoQuery = {
        "err_code": "CE_5003",
        "message": "The request is missing a querystring",
    }

    EdgeRequiredQuery = {
        "err_code": "CE_5004",
        "message": "Missing required querystring values",
    }

    EdgeRequiredHeaders = {
        "err_code": "CE_5005",
        "message": "Malformed header structure or missing data",
    }

    EdgeNoClient = {"err_code": "CE_4001", "message": "Document not found"}

    """
       Errors with no exception
    """
    DocDelNull = {
        "err_code": "DDS_4001",
        "message": "No records was found for given patient. No document deleted",
    }
    LoginNoAuth = {
        "err_code": "LIN_4007",
        "message": "No auth err_code and/or state in the query string parameters",
    }
    LogoutClient = {
        "err_code": "OUT_5001",
        "message": "Error logging user out",
    }
    LogoutDecode = {"err_code": "OUT_4001", "message": "Error while decoding JWT"}
    EnvMissing = {
        "err_code": "ENV_5001",
        "message": "An error occurred due to missing environment variable: '%(name)s'",
    }
    DocTypeNull = {"err_code": "VDT_4001", "message": "docType not supplied"}
    DocTypeInvalid = {
        "err_code": "VDT_4002",
        "message": "Invalid document type requested",
    }
    DocTypeKey = {
        "err_code": "VDT_4003",
        "message": MISSING_KEY,
    }
    PatientIdInvalid = {
        "err_code": "PN_4001",
        "message": "Invalid patient number %(number)s",
        "fhir_coding": UKCoreSpineError.INVALID_SEARCH_DATA,
    }
    PatientIdNoKey = {
        "err_code": "PN_4002",
        "message": MISSING_KEY,
        "fhir_coding": UKCoreSpineError.MISSING_VALUE,
    }
    PatientIdMismatch = {
        "err_code": "PN_4003",
        "message": "An error occurred due to patient number mismatch",
    }
    GatewayError = {
        "err_code": "GWY_5001",
        "message": "Failed to utilise AWS client/resource",
    }
    UploadInProgressError = {
        "err_code": "LGL_423",
        "message": "Records are in the process of being uploaded",
        "fhir_coding": FhirIssueCoding.FORBIDDEN,
    }
    IncompleteRecordError = {
        "err_code": "LGL_400",
        "message": "Incomplete record, Failed to create document manifest",
    }
    DynamoInvalidStreamEvent = {
        "err_code": "DBS_4001",
        "message": "Failed to parse DynamoDb event stream",
    }
    SqsInvalidEvent = {
        "err_code": "SQS_4001",
        "message": "Failed to parse SQS event",
    }

    MockError = {
        "message": "Client error",
        "err_code": "AB_XXXX",
        "interaction_id": "88888888-4444-4444-4444-121212121212",
        "fhir_coding": FhirIssueCoding.FORBIDDEN,
    }

    """
       Errors with unhandled exceptions
    """
    InternalServerError = {
        "err_code": "UE_500",
        "message": "An internal server error occurred",
        "fhir_coding": FhirIssueCoding.EXCEPTION,
    }
