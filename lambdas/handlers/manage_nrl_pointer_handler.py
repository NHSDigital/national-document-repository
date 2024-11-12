import json

from models.nrl_fhir_document_reference import FhirDocumentReference
from models.nrl_sqs_message import NrlSqsMessage
from services.base.ssm_service import SSMService
from services.nrl_api_service import NrlApiService
from utils.audit_logging_setup import LoggingService
from utils.decorators.ensure_env_var import ensure_environment_variables
from utils.decorators.handle_lambda_exceptions import handle_lambda_exceptions
from utils.decorators.set_audit_arg import set_request_context_for_logging
from utils.request_context import request_context

logger = LoggingService(__name__)


@set_request_context_for_logging
@ensure_environment_variables(
    names=[
        "APPCONFIG_APPLICATION",
        "APPCONFIG_CONFIGURATION",
        "APPCONFIG_ENVIRONMENT",
        "NRL_API_ENDPOINT",
    ]
)
@handle_lambda_exceptions
def lambda_handler(event, context):
    logger.info(f"Received event: {event}")
    sqs_messages = event.get("Records", [])
    nrl_api_service = NrlApiService(SSMService)
    actions_options = {
        "POST": nrl_api_service.create_new_pointer,
        "UPDATE": nrl_api_service.update_pointer,
        "DELETE": nrl_api_service.delete_pointer,
    }
    for sqs_message in sqs_messages:
        sqs_message = json.loads(sqs_message["body"])
        nrl_message = NrlSqsMessage(**sqs_message)
        NrlSqsMessage.model_validate(nrl_message)
        request_context.patient_nhs_no = nrl_message.nhs_number
        c = nrl_message.model_dump(by_alias=True)
        document = FhirDocumentReference(**c).build_fhir_dict()
        actions_options[sqs_messages.get("action", "POST")](document)
