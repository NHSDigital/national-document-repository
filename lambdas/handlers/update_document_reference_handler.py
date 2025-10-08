import json
import os
import sys
from json import JSONDecodeError

from enums.feature_flags import FeatureFlags
from enums.lambda_error import LambdaError
from enums.logging_app_interaction import LoggingAppInteraction
from services.feature_flags_service import FeatureFlagService
from services.update_document_reference_service import UpdateDocumentReferenceService
from utils.audit_logging_setup import LoggingService
from utils.decorators.ensure_env_var import ensure_environment_variables
from utils.decorators.handle_lambda_exceptions import handle_lambda_exceptions
from utils.decorators.override_error_check import override_error_check
from utils.decorators.set_audit_arg import set_request_context_for_logging
from utils.decorators.validate_patient_id import validate_patient_id
from utils.lambda_exceptions import FeatureFlagsException, UpdateDocumentRefException
from utils.lambda_response import ApiGatewayResponse
from utils.request_context import request_context

sys.path.append(os.path.join(os.path.dirname(__file__)))

logger = LoggingService(__name__)


@validate_patient_id
@set_request_context_for_logging
@ensure_environment_variables(
    names=[
        "APPCONFIG_APPLICATION",
        "APPCONFIG_CONFIGURATION",
        "APPCONFIG_ENVIRONMENT",
        "DOCUMENT_STORE_DYNAMODB_NAME",
        "LLOYD_GEORGE_DYNAMODB_NAME",
        "STAGING_STORE_BUCKET_NAME",
        "DOCUMENT_STORE_BUCKET_NAME",
        "PRESIGNED_ASSUME_ROLE",
    ]
)
@override_error_check
@handle_lambda_exceptions
def lambda_handler(event, context):
    request_context.app_interaction = LoggingAppInteraction.UPDATE_RECORD.value

    feature_flag_service = FeatureFlagService()
    upload_flag_name = FeatureFlags.UPLOAD_LAMBDA_ENABLED.value
    add_document_flag_name = FeatureFlags.ADD_DOCUMENT_ENABLED.value

    upload_lambda_enabled_flag_object = feature_flag_service.get_feature_flags_by_flag(
        upload_flag_name
    )
    add_document_enabled_flag_object = feature_flag_service.get_feature_flags_by_flag(
        add_document_flag_name
    )

    if not upload_lambda_enabled_flag_object[upload_flag_name]:
        logger.info("Upload Lambda feature flag not enabled, event will not be processed")
        raise FeatureFlagsException(404, LambdaError.FeatureFlagDisabled)

    if not add_document_enabled_flag_object[add_document_flag_name]:
        logger.info("Add Document feature flag not enabled, event will not be processed")
        raise FeatureFlagsException(404, LambdaError.FeatureFlagDisabled)
    
    logger.info("Starting document reference update process")
    nhs_number_query_string = event["queryStringParameters"]["patientId"]

    nhs_number_body, doc_list = processing_event_details(event)

    if nhs_number_body != nhs_number_query_string:
        logger.warning(
            "Received nhs number query string does not match event's body nhs number"
        )
        raise UpdateDocumentRefException(400, LambdaError.PatientIdMismatch)
    request_context.patient_nhs_no = nhs_number_query_string

    logger.info("Processed update documents from request")
    update_doc_ref_service = UpdateDocumentReferenceService()

    # this will be doing just the further checks and PUT FHIR SERVICE CALL
    url_responses = update_doc_ref_service.update_document_reference_request(
        nhs_number_query_string, doc_list
    )

    # for fhir_doc_ref in fhir_document_references:
    #     print(fhir_doc_ref['url'])
    # expected next version to be somewhere here

    # call the base service with whatever is required for the base service logic

    return ApiGatewayResponse(
        200, json.dumps(url_responses), "PUT"
    ).create_api_gateway_response()


def processing_event_details(event):
    failed_message = "Update document reference failed"
    # '{"resourceType": "DocumentReference", "subject": {"identifier": {"value": "9000000009"}}, "content": [{"attachment": [{"fileName": "1of3_Lloyd_George_Record_[Joe Bloggs]_[9000000009]_[25-12-2019].pdf", "contentType": "application/pdf", "docType": "LG", "clientId": "uuid1"}, {"fileName": "2of3_Lloyd_George_Record_[Joe Bloggs]_[9000000009]_[25-12-2019].pdf", "contentType": "application/pdf", "docType": "LG", "clientId": "uuid2"}, {"fileName": "3of3_Lloyd_George_Record_[Joe Bloggs]_[9000000009]_[25-12-2019].pdf", "contentType": "application/pdf", "docType": "LG", "clientId": "uuid3"}]}], "created": "2023-10-02T15:55:30.650Z"}'
    try:
        body = json.loads(event["body"])
        nhs_number = body["subject"]["identifier"]["value"]

        if not body or not isinstance(body, dict):
            logger.error(
                f"{LambdaError.CreateDocNoBody.to_str()}",
                {"Result": failed_message},
            )
            raise UpdateDocumentRefException(400, LambdaError.CreateDocNoBody)

        doc_list = body["content"][0]["attachment"]
        return nhs_number, doc_list

    except (JSONDecodeError, AttributeError) as e:
        logger.error(
            f"{LambdaError.CreateDocPayload.to_str()}: {str(e)}",
            {"Result": failed_message},
        )
        raise UpdateDocumentRefException(400, LambdaError.CreateDocPayload)
    except (KeyError, TypeError) as e:
        logger.error(
            f"{LambdaError.CreateDocProps.to_str()}: {str(e)}",
            {"Result": failed_message},
        )
        raise UpdateDocumentRefException(400, LambdaError.CreateDocProps)
