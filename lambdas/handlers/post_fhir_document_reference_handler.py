from services.post_fhir_document_reference_service import (
    PostFhirDocumentReferenceService,
)
from utils.audit_logging_setup import LoggingService
from utils.decorators.handle_lambda_exceptions import handle_lambda_exceptions_fhir
from utils.lambda_exceptions import CreateDocumentRefException
from utils.lambda_response import ApiGatewayResponse

logger = LoggingService(__name__)


@handle_lambda_exceptions_fhir
def lambda_handler(event, context):
    """
    Handler for processing FHIR Document Reference requests.

    This lambda accepts a FHIR Document Reference object, validates it,
    stores metadata in DynamoDB, and either stores the binary content in S3
    or creates a pre-signed URL for uploading the file.

    Args:
        event: AWS Lambda event object
        context: AWS Lambda context object

    Returns:
        HTTP response with FHIR Document Reference object
    """
    try:
        logger.info("Processing FHIR document reference request")

        fhir_doc_ref_service = PostFhirDocumentReferenceService()

        fhir_response = fhir_doc_ref_service.process_fhir_document_reference(
            event.get("body"), event.get("requestContext")
        )

        return ApiGatewayResponse(
            status_code=200, body=fhir_response, methods="POST"
        ).create_api_gateway_response()

    except CreateDocumentRefException as exception:
        logger.error(f"Error processing FHIR document reference: {str(exception)}")
        return ApiGatewayResponse(
            status_code=exception.status_code,
            body=exception.error.create_error_response().create_error_fhir_response(
                exception.error.value.get("fhir_coding")
            ),
            methods="POST",
        ).create_api_gateway_response()
