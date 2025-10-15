from enum import StrEnum, auto
from enums.lambda_error import LambdaError
from utils.audit_logging_setup import LoggingService
from utils.lambda_exceptions import InvalidDocTypeException

logger = LoggingService(__name__)


class MtlsCommonNames(StrEnum):
    PDM = auto()

    @classmethod
    def allowed_names(cls) -> dict["MtlsCommonNames", list[str]]:
        return {
            cls.PDM: [
                "ndrclient.main.int.pdm.national.nhs.uk",
                "client.dev.ndr.national.nhs.uk",
            ]
        }

    @classmethod
    def from_common_name(cls, common_name: str) -> "MtlsCommonNames | None":
        for doc_type, names in cls.allowed_names().items():
            if common_name in names:
                return doc_type
        logger.error(f"mTLS common name {common_name} - is not supported")
        raise InvalidDocTypeException(400, LambdaError.DocTypeInvalid)
