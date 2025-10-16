class PatientNotFoundException(Exception):
    pass


class InvalidResourceIdException(Exception):
    pass


class InvalidNhsNumberException(Exception):
    pass


class OAuthErrorException(Exception):
    pass


class NrlApiException(Exception):
    pass


class PdsErrorException(Exception):
    pass


class PdsTooManyRequestsException(Exception):
    pass


class AuthorisationException(Exception):
    pass


class TooManyOrgsException(Exception):
    pass


class OrganisationNotFoundException(Exception):
    pass


class OdsErrorException(Exception):
    pass


class DynamoServiceException(Exception):
    pass


class DocumentServiceException(Exception):
    pass


class MissingEnvVarException(Exception):
    pass


class InvalidParamException(Exception):
    pass


class FileProcessingException(Exception):
    pass


class LGFileTypeException(ValueError):
    """One or more of the files do not match the required file type."""

    pass


class LGInvalidFilesException(Exception):
    pass


class InvalidMessageException(Exception):
    pass


class InvalidDocumentReferenceException(Exception):
    pass


class PatientRecordAlreadyExistException(Exception):
    pass


class UserNotAuthorisedException(Exception):
    pass


class VirusScanNoResultException(Exception):
    pass


class DocumentInfectedException(Exception):
    pass


class VirusScanFailedException(Exception):
    pass


class S3FileNotFoundException(Exception):
    pass


class TagNotFoundException(Exception):
    pass


class LogoutFailureException(Exception):
    pass


class BulkUploadException(Exception):
    pass


class OidcApiException(Exception):
    pass


class LoginException(Exception):
    pass


class BulkUploadMetadataException(Exception):
    pass


class FhirResourceNotFound(Exception):
    pass


class FileUploadInProgress(Exception):
    pass


class NoAvailableDocument(Exception):
    pass


class LogsQueryException(Exception):
    pass


class StatisticDataNotFoundException(Exception):
    pass


class PdsResponseValidationException(Exception):
    pass


class InvalidFileNameException(Exception):
    pass


class MetadataPreprocessingException(Exception):
    pass


class TransactionConflictException(Exception):
    pass
