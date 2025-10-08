import json
import os
from typing import Optional

from botocore.exceptions import ClientError
from pydantic import Field, ValidationError
from enums.lambda_error import LambdaError
from enums.snomed_codes import SnomedCodes
from enums.supported_document_types import SupportedDocumentTypes
from models.document_reference import DocumentReference, UploadRequestDocument
from models.fhir.R4.fhir_document_reference import Attachment, DocumentReferenceInfo
from services.base.dynamo_service import DynamoDBService
from services.base.s3_service import S3Service
from services.base.ssm_service import SSMService
from services.document_deletion_service import DocumentDeletionService
from services.document_service import DocumentService
from services.put_fhir_document_reference_service import PutFhirDocumentReferenceService
from utils import request_context
from utils.audit_logging_setup import LoggingService
from utils.common_query_filters import NotDeleted
from utils.constants.ssm import UPLOAD_PILOT_ODS_ALLOWED_LIST
from utils.exceptions import InvalidNhsNumberException, LGInvalidFilesException, PatientNotFoundException, PdsTooManyRequestsException
from utils.lambda_exceptions import UpdateDocumentRefException
from utils.lloyd_george_validator import getting_patient_info_from_pds, validate_lg_files


FAILED_UPDATE_REFERENCE_MESSAGE = "Update document reference failed"
PROVIDED_DOCUMENT_SUPPORTED_MESSAGE = "Provided document is supported"
UPDATE_REFERENCE_SUCCESS_MESSAGE = "Update reference was successful"
UPDATE_REFERENCE_FAILED_MESSAGE = "Update reference was unsuccessful"
PRESIGNED_URL_ERROR_MESSAGE = (
    "An error occurred when updating pre-signed url for document reference"
)

logger = LoggingService(__name__)

class UpdateDocumentReferenceService:
    def __init__(self):
        update_document_aws_role_arn = os.getenv("PRESIGNED_ASSUME_ROLE")
        self.s3_service = S3Service(custom_aws_role=update_document_aws_role_arn)
        self.dynamo_service = DynamoDBService()
        self.document_service = DocumentService()
        self.document_deletion_service = DocumentDeletionService()
        self.ssm_service = SSMService()

        self.lg_dynamo_table = os.getenv("LLOYD_GEORGE_DYNAMODB_NAME")
        self.arf_dynamo_table = os.getenv("DOCUMENT_STORE_DYNAMODB_NAME")
        self.staging_bucket_name = os.getenv("STAGING_STORE_BUCKET_NAME")
        self.upload_sub_folder = "user_upload"

    def update_document_reference_request(
        self, nhs_number: str, documents_list: list[dict]
    ):
        lg_documents: list[UploadRequestDocument] = []
        url_responses = {}
        update_request_documents = self.parse_documents_list(documents_list) # model validate

        has_lg_document = any(
            document.docType == SupportedDocumentTypes.LG
            for document in update_request_documents
        )

        try:
            snomed_code_type = None
            patient_ods_code = ""
            if has_lg_document:
                pds_patient_details = getting_patient_info_from_pds(nhs_number)
                patient_ods_code = (
                    pds_patient_details.get_ods_code_or_inactive_status_for_gp()
                )
                ods_allowed = self.check_if_ods_code_is_in_pilot(patient_ods_code)
                if not ods_allowed:
                    raise UpdateDocumentRefException(
                        404, LambdaError.CreateDocRefOdsCodeNotAllowed
                    )

                if isinstance(request_context.authorization, dict):
                    user_ods_code = request_context.authorization.get(
                        "selected_organisation", {}
                    ).get("org_ods_code", "")

            # LG_MOCK_EVENT_BODY = {
            #     "resourceType": "DocumentReference",
            #     "subject": {"identifier": {"value": TEST_NHS_NUMBER}},
            #     "content": [{"attachment": LG_FILE_LIST}],
            #     "created": "2023-10-02T15:55:30.650Z",
            # }

            # LG_FILE_LIST
            # "fileName": f"1of3_Lloyd_George_Record_[Joe Bloggs]_[{TEST_NHS_NUMBER}]_[25-12-2019].pdf",
            # "contentType": "application/pdf",
            # "docType": "LG",
            # "clientId": "uuid1",

            for validated_doc in update_request_documents:
                # potentially fetch the doc ref instead of creating a new one
                # document_reference = self.update_document_reference( 
                #     nhs_number, patient_ods_code, validated_doc, snomed_code_type
                # )

                match validated_doc.docType:
                    case SupportedDocumentTypes.LG:
                        lg_documents.append(validated_doc)
                        snomed_code_type = SnomedCodes.LLOYD_GEORGE.value
                    case _:
                        logger.error(
                            f"{LambdaError.CreateDocInvalidType.to_str()}",
                            {"Result": UPDATE_REFERENCE_FAILED_MESSAGE},
                        )
                        raise UpdateDocumentRefException(
                            400, LambdaError.CreateDocInvalidType
                        )

                # fhir_doc = ""
                # NEED TO GENERATE THIS DYNAMICALLY FROM existing DocumentReference
                # single attachment (not a list of files)
                # add currentFinalVersion

                attachment_details = Attachment(
                    title = validated_doc.fileName,
                    # creation = document_reference.document_scan_creation
                    #     or document_reference.created // ???
                )

                doc_ref_info = DocumentReferenceInfo(
                    nhs_number = nhs_number,
                    # snomed_code_doc_type = SnomedCodes.find_by_code(
                    #     document_reference.document_snomed_code_type
                    # ),
                    snomed_code_doc_type = snomed_code_type,
                    attachment = attachment_details,
                    author = user_ods_code
                )

                # need to extract the id from the request path and send it down to base service (instead of validated_doc.clientId)
                fhir_doc_ref = doc_ref_info.create_fhir_document_reference_object_basic(validated_doc.clientId)

                fhir_doc_ref_service = PutFhirDocumentReferenceService()

                fhir_response = fhir_doc_ref_service.process_fhir_document_reference(
                    fhir_doc_ref.model_dump_json()
                )
                fhir_response_data = json.loads(fhir_response)
                url_responses[validated_doc.clientId] = fhir_response_data["content"][0]["attachment"]["url"]

            if lg_documents:
                validate_lg_files(lg_documents, pds_patient_details)
                self.check_existing_lloyd_george_records_and_remove_failed_upload(
                    nhs_number
                )

            return url_responses

        except PatientNotFoundException:
            raise UpdateDocumentRefException(404, LambdaError.SearchPatientNoPDS)

        except (
            InvalidNhsNumberException,
            LGInvalidFilesException,
            PdsTooManyRequestsException,
        ) as e:
            logger.error(
                f"{LambdaError.CreateDocFiles.to_str()} :{str(e)}",
                {"Result": FAILED_UPDATE_REFERENCE_MESSAGE},
            )
            raise UpdateDocumentRefException(400, LambdaError.CreateDocFiles)

    def check_if_ods_code_is_in_pilot(self, ods_code) -> bool:
        pilot_ods_codes = self.get_allowed_list_of_ods_codes_for_upload_pilot()
        return ods_code in pilot_ods_codes

    def parse_documents_list(
        self, document_list: list[dict]
    ) -> list[UploadRequestDocument]:
        update_request_document_list = []
        for document in document_list:
            try:
                validated_doc: UploadRequestDocument = (
                    UploadRequestDocument.model_validate(document)
                )
                update_request_document_list.append(validated_doc)
            except ValidationError as e:
                logger.error(
                    f"{LambdaError.CreateDocNoParse.to_str()} :{str(e)}",
                    {"Result": FAILED_UPDATE_REFERENCE_MESSAGE},
                )
                raise UpdateDocumentRefException(400, LambdaError.CreateDocNoParse)

        return update_request_document_list
    
    def prepare_pre_signed_url(self, document_reference: DocumentReference):
        try:
            s3_response = self.s3_service.create_upload_presigned_url(
                document_reference.s3_bucket_name, document_reference.s3_file_key
            )

            return s3_response

        except ClientError as e:
            logger.error(
                f"{LambdaError.CreateDocPresign.to_str()}: {str(e)}",
                {"Result": PRESIGNED_URL_ERROR_MESSAGE},
            )
            raise UpdateDocumentRefException(500, LambdaError.CreateDocPresign)

    def check_existing_lloyd_george_records_and_remove_failed_upload(
        self,
        nhs_number: str,
    ) -> None:
        logger.info("Looking for previous records for this patient...")

        previous_records = (
            self.document_service.fetch_available_document_references_by_type(
                nhs_number=nhs_number,
                doc_type=SupportedDocumentTypes.LG,
                query_filter=NotDeleted,
            )
        )
        if not previous_records:
            logger.info(
                "No record was found for this patient. Will continue to create doc ref."
            )
            return

        # self.stop_if_all_records_uploaded(previous_records)
        self.stop_if_upload_is_in_process(previous_records)
        self.remove_records_of_failed_upload(self.lg_dynamo_table, previous_records)

    def stop_if_upload_is_in_process(self, previous_records: list[DocumentReference]):
        if any(
            self.document_service.is_upload_in_process(document)
            for document in previous_records
        ):
            logger.error(
                "Records are in the process of being uploaded. Will not process the new upload.",
                {"Result": UPDATE_REFERENCE_FAILED_MESSAGE},
            )
            raise UpdateDocumentRefException(423, LambdaError.UploadInProgressError)

    # we should not be stopping perhaps
    def stop_if_all_records_uploaded(self, previous_records: list[DocumentReference]):
        all_records_uploaded = all(record.uploaded for record in previous_records)
        if all_records_uploaded:
            logger.info(
                "The patient already has a full set of record. "
                "We should not be processing the new Lloyd George record upload."
            )
            logger.error(
                f"{LambdaError.CreateDocRecordAlreadyInPlace.to_str()}",
                {"Result": UPDATE_REFERENCE_FAILED_MESSAGE},
            )
            raise UpdateDocumentRefException(
                422, LambdaError.CreateDocRecordAlreadyInPlace
            )
    def remove_records_of_failed_upload(
        self,
        table_name: str,
        failed_upload_records: list[DocumentReference],
    ):
        logger.info(
            "Found previous records of failed upload. "
            "Will delete those records before creating new document references."
        )

        logger.info("Deleting files from s3...")
        for record in failed_upload_records:
            s3_bucket_name = record.s3_bucket_name
            file_key = record.s3_file_key
            self.s3_service.delete_object(s3_bucket_name, file_key)

        logger.info("Deleting dynamodb record...")
        self.document_service.hard_delete_metadata_records(
            table_name=table_name, document_references=failed_upload_records
        )

        logger.info("Previous failed records are deleted.")

    def get_allowed_list_of_ods_codes_for_upload_pilot(self) -> list[str]:
        logger.info(
            "Starting ssm request to retrieve allowed list of ODS codes for Upload Pilot"
        )
        response = self.ssm_service.get_ssm_parameter(UPLOAD_PILOT_ODS_ALLOWED_LIST)
        if not response:
            logger.warning("No ODS codes found in allowed list for Upload Pilot")
        return response