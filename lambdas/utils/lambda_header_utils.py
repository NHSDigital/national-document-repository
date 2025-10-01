from typing import Optional
from enums.lambda_error import LambdaError
from enums.mtls import MtlsCommonNames
from utils.audit_logging_setup import LoggingService
from utils.lambda_exceptions import CreateDocumentRefException

logger = LoggingService(__name__)


def validate_common_name_in_mtls(headers: dict) -> Optional[MtlsCommonNames]:
    subject = headers.get("x-amzn-mtls-clientcert-subject", "")
    if "CN=" not in subject:
        return None

    for part in subject.split(","):
        if part.strip().startswith("CN="):
            cn_value = part.strip().split("=", 1)[1].lower()
            try:
                return MtlsCommonNames(cn_value)
            except ValueError:
                # Not a valid enum member
                logger.error(f"mTLS common name {cn_value} - is not supported")
                raise CreateDocumentRefException(400, LambdaError.CreateDocInvalidType)
    return None
