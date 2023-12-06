import os
from enum import Enum
from typing import List

from utils.audit_logging_setup import LoggingService
from utils.exceptions import InvalidDocTypeException

logger = LoggingService(__name__)


class SupportedDocumentTypes(Enum):
    ARF = "ARF"
    LG = "LG"
    ALL = "ALL"

    @staticmethod
    def list():
        return [SupportedDocumentTypes.ARF, SupportedDocumentTypes.LG]

    @staticmethod
    def list_names() -> List[str]:
        return [str(doc_type.value) for doc_type in SupportedDocumentTypes.list()]

    @staticmethod
    def get_from_field_name(value: str):
        if value in SupportedDocumentTypes.list_names():
            return value
        return None

    def get_dynamodb_table_name(self) -> str:
        """
        Get the dynamodb table name related to a specific doc_type

        example usage:
            SupportedDocumentTypes.ARF.get_dynamodb_table_name()
            (returns "ndr*_DocumentReferenceMetadata")

        result:
            "ndr*_DocumentReferenceMetadata"

        Eventually we could replace all os.environ["XXX_DYNAMODB_NAME"] calls with this method,
        so that the logic of resolving table names are controlled in one place.
        """
        try:
            match self:
                case SupportedDocumentTypes.ARF:
                    return os.environ["DOCUMENT_STORE_DYNAMODB_NAME"]
                case SupportedDocumentTypes.LG:
                    return os.environ["LLOYD_GEORGE_DYNAMODB_NAME"]
                case _:
                    logger.error(
                        f"Failed to resolve dynamodb table name for doc_type {self.value}"
                    )
                    raise InvalidDocTypeException(
                        status_code=500,
                        message=f"Failed to resolve dynamodb table name for doc_type {self.value}",
                    )

        except KeyError as e:
            logger.error(e)
            logger.error(
                f"An error occurred due to missing environment variable for doc_type {self.value}"
            )
            raise InvalidDocTypeException(
                status_code=500,
                message=f"Failed to resolve dynamodb table name for doc_type {self.value}",
            )
