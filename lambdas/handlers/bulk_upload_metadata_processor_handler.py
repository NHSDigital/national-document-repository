from enums.lloyd_george_pre_process_format import LloydGeorgePreProcessFormat
from services.bulk_upload.metadata_general_preprocessor import (
    MetadataGeneralPreprocessor,
)
from services.bulk_upload.metadata_usb_preprocessor import (
    MetadataUsbPreprocessorService,
)
from services.bulk_upload_metadata_processor_service import (
    BulkUploadMetadataProcessorService,
)
from utils.audit_logging_setup import LoggingService
from utils.decorators.ensure_env_var import ensure_environment_variables
from utils.decorators.handle_lambda_exceptions import handle_lambda_exceptions
from utils.decorators.override_error_check import override_error_check
from utils.decorators.set_audit_arg import set_request_context_for_logging

logger = LoggingService(__name__)


@set_request_context_for_logging
@override_error_check
@ensure_environment_variables(
    names=["STAGING_STORE_BUCKET_NAME", "METADATA_SQS_QUEUE_URL"]
)
@handle_lambda_exceptions
def lambda_handler(event, _context):
    practice_directory = event.get("practiceDirectory", "")

    raw_pre_format_type = event.get(
        "preFormatType", LloydGeorgePreProcessFormat.GENERAL
    )

    formatter_service_class = get_formatter_service(raw_pre_format_type)
    if not practice_directory:
        logger.error(
            "Failed to start metadata processing due to missing practice directory"
        )
        return

    logger.info(
        f"Starting metadata processing for practice directory: {practice_directory}"
    )

    metadata_formatter_service = formatter_service_class(practice_directory)
    metadata_service = BulkUploadMetadataProcessorService(metadata_formatter_service)
    metadata_service.process_metadata()


def get_formatter_service(raw_pre_format_type):
    try:
        pre_format_type = LloydGeorgePreProcessFormat(raw_pre_format_type)
        if pre_format_type == LloydGeorgePreProcessFormat.GENERAL:
            logger.info("Using general preFormatType")
            return MetadataGeneralPreprocessor
        elif pre_format_type == LloydGeorgePreProcessFormat.USB:
            logger.info("Using usb preFormatType")
            return MetadataUsbPreprocessorService
    except ValueError:
        logger.warning(
            f"Invalid preFormatType: '{raw_pre_format_type}', defaulting to {LloydGeorgePreProcessFormat.GENERAL}."
        )
        return MetadataGeneralPreprocessor
