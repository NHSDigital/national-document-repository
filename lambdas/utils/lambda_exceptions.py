from utils.error_response import ExceptionError


class LambdaException(Exception):
    def __init__(self, status_code, error: ExceptionError):
        self.status_code = status_code
        self.error = error


class CreateDocumentRefException(LambdaException):
    pass


class SearchPatientException(LambdaException):
    pass


class InvalidDocTypeException(LambdaException):
    pass


class LoginRedirectException(LambdaException):
    pass


class DocumentManifestServiceException(LambdaException):
    pass


class LoginException(LambdaException):
    pass


class LGStitchServiceException(LambdaException):
    pass


class DocumentRefSearchException(LambdaException):
    pass


class DocumentDeletionServiceException(LambdaException):
    pass
