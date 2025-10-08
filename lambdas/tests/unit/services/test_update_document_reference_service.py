from datetime import datetime
import json

import pytest
from enums.snomed_codes import SnomedCodes
from models.document_reference import DocumentReference
from services.document_service import DocumentService
from services.put_fhir_document_reference_service import PutFhirDocumentReferenceService
from services.update_document_reference_service import UpdateDocumentReferenceService
from tests.unit.helpers.data.create_document_reference import (
    LG_FILE_LIST,
    PARSED_LG_FILE_LIST,
)
from tests.unit.conftest import (
    EXPECTED_PARSED_PATIENT_BASE_CASE as mock_pds_patient_details,
    TEST_UUID,
)
from tests.unit.helpers.data.test_documents import create_test_doc_store_refs
from utils import request_context
from utils.constants.ssm import UPLOAD_PILOT_ODS_ALLOWED_LIST

from lambdas.enums.supported_document_types import SupportedDocumentTypes
from lambdas.tests.unit.conftest import (
    TEST_CURRENT_GP_ODS,
    TEST_NHS_NUMBER,
)

NA_STRING = "Not Test Important"

MOCK_ALLOWED_ODS_CODES_LIST_PILOT = {
    "Parameter": {
        "Name": UPLOAD_PILOT_ODS_ALLOWED_LIST,
        "Type": "StringList",
        "Value": "PI001,PI002,PI003",
        "Version": 123,
        "Selector": "string",
        "SourceResult": "string",
        "LastModifiedDate": datetime(2015, 1, 1),
        "ARN": "string",
        "DataType": "string",
    },
}


@pytest.fixture
def mock_update_doc_ref_service(mocker, set_env):
    mocker.patch("services.base.s3_service.IAMService")
    mocker.patch("services.update_document_reference_service.S3Service")
    mocker.patch("services.update_document_reference_service.DocumentService")
    mocker.patch("services.update_document_reference_service.DynamoDBService")
    mocker.patch("services.update_document_reference_service.DocumentDeletionService")
    mocker.patch("services.update_document_reference_service.SSMService")

    update_doc_ref_service = UpdateDocumentReferenceService()
    yield update_doc_ref_service

@pytest.fixture
def mock_pds_service_fetch(mocker):
    mock_service_object = mocker.MagicMock()
    mocker.patch(
        "services.put_fhir_document_reference_service.get_pds_service",
        return_value=mock_service_object,
    )
    mock_service_object.fetch_patient_details.return_value = mock_pds_patient_details


# @pytest.fixture
# def mock_put_fhir_doc_ref_service(set_env, mocker, mock_pds_service_fetch):
#     mock_put_s3 = mocker.patch("services.put_fhir_document_reference_service.S3Service")
#     mock_put_dynamo = mocker.patch("services.put_fhir_document_reference_service.DynamoDBService")
#     mock_put_document_service = mocker.patch("services.put_fhir_document_reference_service.DocumentService")
#     service = PutFhirDocumentReferenceService()
#     service.s3_service = mock_put_s3.return_value
#     service.dynamo_service = mock_put_dynamo.return_value
#     service.document_service = mock_put_document_service.return_value
#     yield service

@pytest.fixture
def mock_put_fhir_doc_ref_service(set_env, mocker, mock_pds_service_fetch, setup_request_context):
    mock_s3 = mocker.patch("services.put_fhir_document_reference_service.S3Service")
    mock_dynamo = mocker.patch(
        "services.put_fhir_document_reference_service.DynamoDBService"
    )
    mock_document_service = mocker.patch("services.put_fhir_document_reference_service.DocumentService")
    service = PutFhirDocumentReferenceService()
    service.s3_service = mock_s3.return_value
    service.dynamo_service = mock_dynamo.return_value
    service.document_service = mock_document_service.return_value

    yield service

@pytest.fixture
def setup_request_context():
    request_context.authorization = {
        "ndr_session_id": TEST_UUID,
        "nhs_user_id": "test-user-id",
        "selected_organisation": {"org_ods_code": "test-ods-code"},
    }
    yield
    request_context.authorization = {}

@pytest.fixture()
def mock_check_existing_lloyd_george_records_and_remove_failed_upload(
    mock_update_doc_ref_service, mocker
):
    yield mocker.patch.object(
        mock_update_doc_ref_service,
        "check_existing_lloyd_george_records_and_remove_failed_upload",
    )


@pytest.fixture()
def mock_validate_lg_files(mocker, mock_getting_patient_info_from_pds):
    yield mocker.patch("services.update_document_reference_service.validate_lg_files")


@pytest.fixture()
def mock_getting_patient_info_from_pds(mocker, mock_pds_patient):
    yield mocker.patch(
        "services.update_document_reference_service.getting_patient_info_from_pds",
        return_value=mock_pds_patient,
    )

@pytest.fixture()
def mock_prepare_pre_signed_url(mock_update_doc_ref_service, mocker):
    yield mocker.patch.object(mock_update_doc_ref_service, "prepare_pre_signed_url")

@pytest.fixture()
def mock_process_fhir_document_reference(mocker):
    yield mocker.patch(
        "services.put_fhir_document_reference_service.PutFhirDocumentReferenceService.process_fhir_document_reference",
        return_value =
            json.dumps(
                {
                    "content": [
                        {
                            "attachment": {
                                "url": "https://test-bucket.s3.amazonaws.com/"
                            }
                        }
                    ]
                }
            )
    )

@pytest.fixture
def get_allowed_list_of_ods_codes_for_upload_pilot(mock_update_doc_ref_service, mocker):
    return mocker.patch.object(
        mock_update_doc_ref_service, "get_allowed_list_of_ods_codes_for_upload_pilot"
    )

def test_update_document_reference_request_with_lg_list_happy_path(
    mock_update_doc_ref_service,
    mock_put_fhir_doc_ref_service,
    mocker,
    mock_validate_lg_files,
    mock_check_existing_lloyd_george_records_and_remove_failed_upload,
    mock_pds_patient,
    get_allowed_list_of_ods_codes_for_upload_pilot,
    mock_process_fhir_document_reference,
):
    # document_references = []
    # side_effects = []

    # for (
    #     index,
    #     file,
    # ) in enumerate(LG_FILE_LIST):
    #     document_references.append(
    #         DocumentReference(
    #             author=NA_STRING,
    #             nhs_number=TEST_NHS_NUMBER,
    #             s3_bucket_name=NA_STRING,
    #             id=NA_STRING,
    #             content_type=NA_STRING,
    #             file_name=file["fileName"],
    #             doc_type=SupportedDocumentTypes.LG,
    #             document_snomed_code_type=SnomedCodes.LLOYD_GEORGE.value.code,
    #         )
    #     )
    #     side_effects.append(document_references[index])

    # mock_update_document_reference.side_effect = side_effects
    get_allowed_list_of_ods_codes_for_upload_pilot.return_value = [TEST_CURRENT_GP_ODS]

    mock_presigned_url_response = "https://test-bucket.s3.amazonaws.com/"

    mock_put_fhir_doc_ref_service.s3_service.create_put_presigned_url.return_value = (
        mock_presigned_url_response
    )

    version_number = 1
    documents = create_test_doc_store_refs()
    documents[0].version = str(version_number)
    mock_put_fhir_doc_ref_service.document_service.fetch_documents_from_table.return_value = documents

    mock_update_doc_ref_service.update_document_reference_request(
        TEST_NHS_NUMBER, LG_FILE_LIST
    )

    # mock_update_document_reference.assert_has_calls(
    #     [
    #         mocker.call(
    #             TEST_NHS_NUMBER,
    #             TEST_CURRENT_GP_ODS,
    #             validated_doc,
    #             SnomedCodes.LLOYD_GEORGE.value.code,
    #         )
    #         for validated_doc in PARSED_LG_FILE_LIST
    #     ],
    #     any_order=True,
    # )

    # mock_create_reference_in_dynamodb.assert_called_once()
    # mock_validate_lg_files.assert_called_with(document_references, mock_pds_patient)
    # mock_check_existing_lloyd_george_records_and_remove_failed_upload.assert_called_with(
    #     TEST_NHS_NUMBER
    # )