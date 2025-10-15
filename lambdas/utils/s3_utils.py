import os

from enums.lambda_error import LambdaError
from enums.snomed_codes import SnomedCode, SnomedCodes
from utils.audit_logging_setup import LoggingService
from utils.lambda_exceptions import InvalidDocTypeException

logger = LoggingService(__name__)


class DocTypeS3BucketRouter:
    def __init__(self):
        self.lg_s3_bucket = os.getenv("LLOYD_GEORGE_BUCKET_NAME")
        self.pdm_s3_bucket = os.getenv("PDM_BUCKET_NAME")
        self.mapping = {
            SnomedCodes.LLOYD_GEORGE.value.code: self.lg_s3_bucket,
            SnomedCodes.PATIENT_DATA.value.code: self.pdm_s3_bucket,
        }

    def resolve(self, doc_type: SnomedCode) -> str:
        try:
            return self.mapping[doc_type.code]
        except KeyError:
            logger.error(
                f"SNOMED code {doc_type.code} - {doc_type.display_name} is not supported"
            )
            raise InvalidDocTypeException(400, LambdaError.DocTypeInvalid)
