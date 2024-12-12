import os

import requests
from enums.lambda_error import LambdaError
from enums.patient_ods_inactive_status import PatientOdsInactiveStatus
from models.document_reference import DocumentReference
from models.nrl_fhir_document_reference import FhirDocumentReference
from models.nrl_sqs_message import NrlAttachment
from requests.exceptions import HTTPError
from services.base.s3_service import S3Service
from services.base.ssm_service import SSMService
from services.document_service import DocumentService
from utils.audit_logging_setup import LoggingService
from utils.constants.ssm import GP_ADMIN_USER_ROLE_CODES, GP_CLINICAL_USER_ROLE_CODE
from utils.lambda_exceptions import NRLGetDocumentReferenceException
from utils.request_context import request_context
from utils.utilities import format_cloudfront_url, get_pds_service

logger = LoggingService(__name__)


class NRLGetDocumentReferenceService:
    def __init__(self):
        self.table = os.getenv("LLOYD_GEORGE_DYNAMODB_NAME")
        self.ssm_prefix = getattr(request_context, "auth_ssm_prefix", "")
        get_document_presign_url_aws_role_arn = os.getenv("PRESIGNED_ASSUME_ROLE")
        self.cloudfront_url = os.environ.get("CLOUDFRONT_URL")
        self.s3_service = S3Service(
            custom_aws_role=get_document_presign_url_aws_role_arn
        )
        self.ssm_service = SSMService()
        self.pds_service = get_pds_service()
        self.document_service = DocumentService()

    def handle_get_document_reference_request(self, document_id, bearer_token):
        document_reference = self.get_document_references(document_id)
        user_details = self.fetch_user_info(bearer_token)

        if not self.is_user_allowed_to_see_file(user_details, document_reference):
            raise NRLGetDocumentReferenceException(
                403, LambdaError.DocumentReferenceUnauthorised
            )

        presign_url = self.create_document_presigned_url(document_reference)
        response = self.create_document_reference_fhir_response(
            document_reference, presign_url
        )
        return response

    def create_document_reference_fhir_response(
        self, document_reference: DocumentReference, presign_url: str
    ) -> dict:
        document_details = NrlAttachment(
            url=presign_url,
            title=document_reference.file_name,
            creation=document_reference.created,
        )
        fhir_document_reference = FhirDocumentReference(
            nhsNumber=document_reference.nhs_number,
            custodian=document_reference.current_gp_ods,
            attachment=document_details,
        ).build_fhir_dict()
        return fhir_document_reference

    def is_user_allowed_to_see_file(self, user_details, document_reference):
        user_ods_codes_and_roles = self.get_user_roles_and_ods_codes(user_details)

        patient_current_gp_ods_code = self.get_patient_current_gp_ods(
            document_reference.nhs_number
        )

        if self.patient_is_inactive(patient_current_gp_ods_code):
            return False

        if patient_current_gp_ods_code in user_ods_codes_and_roles:
            accepted_roles = self.get_ndr_accepted_role_codes()
            return any(
                role in accepted_roles
                for role in user_ods_codes_and_roles[patient_current_gp_ods_code]
            )

    def fetch_user_info(self, bearer_token) -> dict:
        logger.info(f"Fetching user info with bearer token: {bearer_token}")
        request_url = self.ssm_service.get_ssm_parameter(
            self.ssm_prefix + "OIDC_USER_INFO_URL"
        )

        try:
            response = requests.get(
                url=request_url, headers={"Authorization": f"Bearer {bearer_token}"}
            )
            response.raise_for_status()
            return response.json()

        except HTTPError as error:
            logger.error(f"HTTP error {error.response.content}")
            raise NRLGetDocumentReferenceException(
                400, LambdaError.DocumentReferenceGeneralError
            )

    def get_ndr_accepted_role_codes(self) -> list[str]:
        ssm_parameters = self.ssm_service.get_ssm_parameters(
            parameters_keys=[
                GP_ADMIN_USER_ROLE_CODES,
                GP_CLINICAL_USER_ROLE_CODE,
            ]
        )
        return [role for roles in ssm_parameters.values() for role in roles.split(",")]

    def get_user_roles_and_ods_codes(self, user_info) -> dict[str, list[str]]:
        ods_codes_and_roles = {}
        nrbac_roles = user_info.get("nhsid_nrbac_roles", [])

        for role in nrbac_roles:
            ods_code: str = role["org_code"]
            role_code = self.process_role_code(role["role_code"])
            ods_codes_and_roles.setdefault(ods_code, []).append(role_code)
        return ods_codes_and_roles

    def process_role_code(self, role_codes) -> str:
        for role_code in role_codes.split(":"):
            if role_code.startswith("R"):
                return role_code

    def patient_is_inactive(self, current_gp_ods_code):
        try:
            return current_gp_ods_code in PatientOdsInactiveStatus
        except TypeError:
            return False

    def get_document_references(self, document_id: str) -> DocumentReference:
        documents = self.document_service.fetch_documents_from_table(
            table=self.table,
            search_condition=document_id,
            search_key="ID",
        )
        if len(documents) > 0:
            return documents[0]
        else:
            raise NRLGetDocumentReferenceException(
                404, LambdaError.DocumentReferenceNotFound
            )

    def get_patient_current_gp_ods(self, nhs_number):
        patient_details = self.pds_service.fetch_patient_details(nhs_number)
        return patient_details.general_practice_ods

    def create_document_presigned_url(self, document_reference: DocumentReference):
        bucket_name = document_reference.get_file_bucket()
        file_location = document_reference.get_file_key()
        presign_url_response = self.s3_service.create_download_presigned_url(
            s3_bucket_name=bucket_name,
            file_key=file_location,
        )
        return format_cloudfront_url(presign_url_response, self.cloudfront_url)
