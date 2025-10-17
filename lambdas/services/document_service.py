import os
import io
import binascii
import base64
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Attr, ConditionBase
from enums.metadata_field_names import DocumentReferenceMetadataFields
from enums.supported_document_types import SupportedDocumentTypes
from models.document_reference import DocumentReference
from pydantic import ValidationError
from services.base.dynamo_service import DynamoDBService
from services.base.s3_service import S3Service
from utils.audit_logging_setup import LoggingService
from utils.common_query_filters import NotDeleted
from utils.dynamo_utils import filter_uploaded_docs_and_recently_uploading_docs
from utils.exceptions import (
    DocumentServiceException,
    FileUploadInProgress,
    NoAvailableDocument,
    InvalidResourceIdException,
    PatientNotFoundException,
    PdsErrorException,
)
from botocore.exceptions import ClientError
from enums.snomed_codes import SnomedCode, SnomedCodes
from models.fhir.R4.fhir_document_reference import (
    DocumentReference as FhirDocumentReference,
)
from utils.utilities import create_reference_id, get_pds_service, validate_nhs_number
from enums.patient_ods_inactive_status import PatientOdsInactiveStatus
from utils.ods_utils import PCSE_ODS_CODE
from models.fhir.R4.fhir_document_reference import SNOMED_URL
from utils.common_query_filters import CurrentStatusFile
from models.pds_models import PatientDetails

logger = LoggingService(__name__)


class DocumentService:
    def __init__(self):
        presigned_aws_role_arn = os.getenv("PRESIGNED_ASSUME_ROLE")
        self.s3_service = S3Service(custom_aws_role=presigned_aws_role_arn)
        self.dynamo_service = DynamoDBService()

        self.lg_dynamo_table = os.getenv("LLOYD_GEORGE_DYNAMODB_NAME")
        self.arf_dynamo_table = os.getenv("DOCUMENT_STORE_DYNAMODB_NAME")
        self.staging_bucket_name = os.getenv("STAGING_STORE_BUCKET_NAME")

    def fetch_available_document_references_by_type(
        self,
        nhs_number: str,
        doc_type: SupportedDocumentTypes,
        query_filter: Attr | ConditionBase,
    ) -> list[DocumentReference]:
        table_name = doc_type.get_dynamodb_table_name()

        return self.fetch_documents_from_table_with_nhs_number(
            nhs_number, table_name, query_filter=query_filter
        )

    def fetch_documents_from_table_with_nhs_number(
        self, nhs_number: str, table: str, query_filter: Attr | ConditionBase = None
    ) -> list[DocumentReference]:
        documents = self.fetch_documents_from_table(
            table=table,
            index_name="NhsNumberIndex",
            search_key="NhsNumber",
            search_condition=nhs_number,
            query_filter=query_filter,
        )

        return documents

    def fetch_documents_from_table(
        self,
        table: str,
        search_condition: str,
        search_key: str,
        index_name: str = None,
        query_filter: Attr | ConditionBase = None,
    ) -> list[DocumentReference]:
        documents = []
        exclusive_start_key = None

        while True:
            response = self.dynamo_service.query_table_by_index(
                table_name=table,
                index_name=index_name,
                search_key=search_key,
                search_condition=search_condition,
                query_filter=query_filter,
                exclusive_start_key=exclusive_start_key,
            )

            for item in response["Items"]:
                try:
                    document = DocumentReference.model_validate(item)
                    documents.append(document)
                except ValidationError as e:
                    logger.error(f"Validation error on document: {item}")
                    logger.error(f"{e}")
                    continue
            if "LastEvaluatedKey" in response:
                exclusive_start_key = response["LastEvaluatedKey"]
            else:
                break
        return documents

    def get_nhs_numbers_based_on_ods_code(self, ods_code: str) -> list[str]:
        documents = self.fetch_documents_from_table(
            table=os.environ["LLOYD_GEORGE_DYNAMODB_NAME"],
            index_name="OdsCodeIndex",
            search_key=DocumentReferenceMetadataFields.CURRENT_GP_ODS.value,
            search_condition=ods_code,
            query_filter=NotDeleted,
        )
        nhs_numbers = list({document.nhs_number for document in documents})
        return nhs_numbers

    def delete_document_references(
        self,
        table_name: str,
        document_references: list[DocumentReference],
        document_ttl_days: int,
    ):
        deletion_date = datetime.now(timezone.utc)

        ttl_seconds = document_ttl_days * 24 * 60 * 60
        document_reference_ttl = int(deletion_date.timestamp() + ttl_seconds)

        logger.info(f"Deleting items in table: {table_name}")

        for reference in document_references:
            reference.doc_status = "deprecated"
            reference.deleted = deletion_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            reference.ttl = document_reference_ttl

            update_fields = reference.model_dump(
                by_alias=True,
                exclude_none=True,
                include={"doc_status", "deleted", "ttl"},
            )
            self.dynamo_service.update_item(
                table_name=table_name,
                key_pair={DocumentReferenceMetadataFields.ID.value: reference.id},
                updated_fields=update_fields,
            )

    def delete_document_object(self, bucket: str, key: str):
        file_exists = self.s3_service.file_exist_on_s3(
            s3_bucket_name=bucket, file_key=key
        )

        if not file_exists:
            raise DocumentServiceException("Document does not exist in S3")

        logger.info(
            f"Located file `{key}` in `{bucket}`, attempting S3 object deletion"
        )
        self.s3_service.delete_object(s3_bucket_name=bucket, file_key=key)

        file_exists = self.s3_service.file_exist_on_s3(
            s3_bucket_name=bucket, file_key=key
        )

        if file_exists:
            raise DocumentServiceException("Document located in S3 after deletion")

    def update_document(
        self,
        table_name: str,
        document_reference: DocumentReference,
        update_fields_name: set[str] = None,
    ):
        self.dynamo_service.update_item(
            table_name=table_name,
            key_pair={DocumentReferenceMetadataFields.ID.value: document_reference.id},
            updated_fields=document_reference.model_dump(
                exclude_none=True, by_alias=True, include=update_fields_name
            ),
        )

    def hard_delete_metadata_records(
        self, table_name: str, document_references: list[DocumentReference]
    ):
        logger.info(f"Deleting items in table: {table_name} (HARD DELETE)")
        primary_key_name = DocumentReferenceMetadataFields.ID.value
        for reference in document_references:
            primary_key_value = reference.id
            deletion_key = {primary_key_name: primary_key_value}
            self.dynamo_service.delete_item(table_name, deletion_key)

    @staticmethod
    def is_upload_in_process(record: DocumentReference):
        return (
            not record.uploaded
            and record.uploading
            and record.last_updated_within_three_minutes()
            and record.doc_status != "final"
        )

    def get_available_lloyd_george_record_for_patient(
        self, nhs_number
    ) -> list[DocumentReference]:
        filter_expression = filter_uploaded_docs_and_recently_uploading_docs()
        available_docs = self.fetch_available_document_references_by_type(
            nhs_number,
            SupportedDocumentTypes.LG,
            query_filter=filter_expression,
        )

        file_in_progress_message = (
            "The patients Lloyd George record is in the process of being uploaded"
        )
        if not available_docs:
            raise NoAvailableDocument()
        for document in available_docs:
            if document.uploading and not document.uploaded:
                raise FileUploadInProgress(file_in_progress_message)
        return available_docs

    def get_batch_document_references_by_id(
        self, document_ids: list[str], doc_type: SupportedDocumentTypes
    ) -> list[DocumentReference]:
        table_name = doc_type.get_dynamodb_table_name()
        response = self.dynamo_service.batch_get_items(
            table_name=table_name, key_list=document_ids
        )

        found_docs = [DocumentReference.model_validate(item) for item in response]
        return found_docs

    def store_binary_in_s3(
        self, document_reference: DocumentReference, binary_content: bytes
    ) -> None:
        """Store binary content in S3"""
        try:
            binary_file = io.BytesIO(base64.b64decode(binary_content, validate=True))
            self.s3_service.upload_file_obj(
                file_obj=binary_file,
                s3_bucket_name=document_reference.s3_bucket_name,
                file_key=document_reference.s3_file_key,
            )
            logger.info(
                f"Successfully stored binary content in S3: {document_reference.s3_file_key}"
            )
        except (binascii.Error, ValueError) as e:
            logger.error(f"Failed to decode base64: {str(e)}")
            raise DocumentServiceException(f"Failed to decode base64: {str(e)}")
        except MemoryError as e:
            logger.error(f"File too large to process: {str(e)}")
            raise DocumentServiceException(f"File too large to process: {str(e)}")
        except ClientError as e:
            logger.error(f"Failed to store binary in S3: {str(e)}")
            raise DocumentServiceException(f"Failed to store binary in S3: {str(e)}")
        except (OSError, IOError) as e:
            logger.error(f"I/O error when processing binary content: {str(e)}")
            raise DocumentServiceException(f"I/O error when processing binary content: {str(e)}")

    def create_s3_presigned_url(self, document_reference: DocumentReference) -> str:
        """Create a pre-signed URL for uploading a file"""
        try:
            response = self.s3_service.create_put_presigned_url(
                document_reference.s3_bucket_name, document_reference.s3_file_key
            )
            logger.info(
                f"Successfully created pre-signed URL for {document_reference.s3_file_key}"
            )
            return response
        except ClientError as e:
            logger.error(f"Failed to create pre-signed URL: {str(e)}")
            raise DocumentServiceException(f"Failed to create pre-signed URL: {str(e)}")
    
    def create_document_reference(
        self,
        nhs_number: str,
        doc_type: SnomedCode,
        fhir_doc: FhirDocumentReference,
        current_gp_ods: str,
        version: str
    ) -> DocumentReference:
        """Create a document reference model"""
        document_id = create_reference_id()

        custodian = fhir_doc.custodian.identifier.value if fhir_doc.custodian else None
        if not custodian:
            custodian = (
                current_gp_ods
                if current_gp_ods not in PatientOdsInactiveStatus.list()
                else PCSE_ODS_CODE
            )
        document_reference = DocumentReference(
            id=document_id,
            nhs_number=nhs_number,
            current_gp_ods=current_gp_ods,
            custodian=custodian,
            s3_bucket_name=self.staging_bucket_name,
            author=fhir_doc.author[0].identifier.value,
            content_type=fhir_doc.content[0].attachment.contentType,
            file_name=fhir_doc.content[0].attachment.title,
            document_snomed_code_type=doc_type.code,
            doc_status="preliminary",
            status="current",
            sub_folder="user_upload",
            version=version,
        )

        return document_reference
    
    def get_document_reference(self, document_id: str, table) -> DocumentReference:
        documents = self.fetch_documents_from_table(
            table=table,
            search_condition=document_id,
            search_key="ID",
            query_filter=CurrentStatusFile,
        )
        if len(documents) > 0:
            logger.info("Document found for given id")
            return documents[0]
        else:
            raise DocumentServiceException(f"Did not find any documents for document ID {document_id}")

    def extract_nhs_number_from_fhir(self, fhir_doc: FhirDocumentReference) -> str:
        """Extract NHS number from FHIR document"""
        # Extract NHS number from subject.identifier where the system identifier is NHS number
        if (
            fhir_doc.subject
            and fhir_doc.subject.identifier
            and fhir_doc.subject.identifier.system
            == "https://fhir.nhs.uk/Id/nhs-number"
        ):
            return fhir_doc.subject.identifier.value

        raise DocumentServiceException("NHS number not found in FHIR document reference")

    def determine_document_type(self, fhir_doc: FhirDocumentReference) -> SnomedCode:
        """Determine the document type based on SNOMED code in the FHIR document"""
        if fhir_doc.type and fhir_doc.type.coding:
            for coding in fhir_doc.type.coding:
                if coding.system == SNOMED_URL:
                    if coding.code == SnomedCodes.LLOYD_GEORGE.value.code:
                        return SnomedCodes.LLOYD_GEORGE.value
                else:
                    logger.error(f"SNOMED code {coding.code} - {coding.display} is not supported")
                    raise DocumentServiceException(f"SNOMED code {coding.code} - {coding.display} is not supported")
        logger.error("SNOMED code not found in FHIR document")
        raise DocumentServiceException("SNOMED code not found in FHIR document")

    def get_dynamo_table_for_doc_type(self, doc_type: SnomedCode) -> str:
        """Get the appropriate DynamoDB table name based on a document type"""
        if doc_type == SnomedCodes.LLOYD_GEORGE.value:
            return self.lg_dynamo_table
        else:
            return self.arf_dynamo_table

    def save_document_reference_to_dynamo(
        self, table_name: str, document_reference: DocumentReference
    ) -> None:
        """Save document reference to DynamoDB"""
        try:
            self.dynamo_service.create_item(
                table_name,
                document_reference.model_dump(exclude_none=True, by_alias=True),
            )
            logger.info(f"Successfully created document reference in {table_name}")
        except ClientError as e:
            logger.error(f"Failed to create document reference: {str(e)}")
            raise DocumentServiceException(f"Failed to create document reference: {str(e)}")
        
    def check_nhs_number_with_pds(self, nhs_number: str) -> PatientDetails:
        try:
            validate_nhs_number(nhs_number)
            pds_service = get_pds_service()
            return pds_service.fetch_patient_details(nhs_number)
        except (
            PatientNotFoundException,
            InvalidResourceIdException,
            PdsErrorException,
        ) as e:
            logger.error(f"Error occurred when fetching patient details: {str(e)}")
            raise DocumentServiceException(f"Error occurred when fetching patient details: {str(e)}")