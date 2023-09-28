class PatientNotFoundException(Exception):
    pass


class InvalidResourceIdException(Exception):
    pass


class PdsErrorException(Exception):
    pass


class DynamoDbException(Exception):
    pass


class ManifestDownloadException(Exception):
    pass


class MissingEnvVarException(Exception):
    pass


class InvalidParamException(Exception):
    pass
