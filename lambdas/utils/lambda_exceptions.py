from enums.lambda_error import LambdaError


class LambdaException(Exception):
    def __init__(self, status_code, error: LambdaError):
        self.status_code = status_code
        self.error = error
        self.message = error.value["message"]
        self.err_code = error.value["err_code"]

    def __eq__(self, other):
        return (
            self.__class__ == other.__class__
            and self.status_code == other.status_code
            and self.message == other.message
            and self.err_code == other.err_code
        )


class CreateDocumentRefException(LambdaException):
    pass


class SearchPatientException(LambdaException):
    pass


class InvalidDocTypeException(LambdaException):
    pass


class LoginRedirectException(LambdaException):
    pass


class DocumentManifestJobServiceException(LambdaException):
    pass


class LoginException(LambdaException):
    pass


class LGStitchServiceException(LambdaException):
    pass


class DocumentRefSearchException(LambdaException):
    pass


class DocumentDeletionServiceException(LambdaException):
    pass


class SendFeedbackException(LambdaException):
    pass


class FeatureFlagsException(LambdaException):
    pass


class VirusScanResultException(LambdaException):
    pass


class UploadConfirmResultException(LambdaException):
    pass


class UpdateUploadStateException(LambdaException):
    pass


class GenerateManifestZipException(LambdaException):
    pass


class CloudFrontEdgeException(LambdaException):
    pass


class GetFhirDocumentReferenceException(LambdaException):
    pass


class OdsReportException(LambdaException):
    pass


class AccessAuditException(LambdaException):
    pass


class PdfStitchingException(LambdaException):
    pass

class UpdateFhirDocumentReferenceException(LambdaException):
    pass
