class PatientNotFoundException(Exception):
    pass


class InvalidResourceIdException(Exception):
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


class DynamoDbException(Exception):
    pass


class ManifestDownloadException(Exception):
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


class InvalidMessageException(Exception):
    pass


class InvalidDocumentReferenceException(Exception):
    pass


class PatientAlreadyExistException(Exception):
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
