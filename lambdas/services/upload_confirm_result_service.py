import os
import uuid

from botocore.exceptions import ClientError
from enums.lambda_error import LambdaError
from enums.metadata_field_names import DocumentReferenceMetadataFields
from enums.nrl_sqs_upload import NrlActionTypes
from enums.snomed_codes import SnomedCodes
from enums.supported_document_types import SupportedDocumentTypes
from models.fhir.R4.fhir_document_reference import Attachment
from models.sqs.nrl_sqs_message import NrlSqsMessage
from services.base.dynamo_service import DynamoDBService
from services.base.s3_service import S3Service
from services.base.sqs_service import SQSService
from services.document_service import DocumentService
from utils.audit_logging_setup import LoggingService
from utils.common_query_filters import CleanFiles, NotDeleted
from utils.lambda_exceptions import UploadConfirmResultException

logger = LoggingService(__name__)


class UploadConfirmResultService:
    def __init__(self, nhs_number):
        self.dynamo_service = DynamoDBService()
        self.document_service = DocumentService()
        self.sqs_service = SQSService()
        self.s3_service = S3Service()
        self.nhs_number = nhs_number
        self.staging_bucket = os.environ["STAGING_STORE_BUCKET_NAME"]
        self.nrl_queue_url = os.environ["NRL_SQS_URL"]

    def process_documents(self, documents: dict):
        lg_table_name = os.environ["LLOYD_GEORGE_DYNAMODB_NAME"]
        lg_bucket_name = os.environ["LLOYD_GEORGE_BUCKET_NAME"]
        arf_bucket_name = os.environ["DOCUMENT_STORE_BUCKET_NAME"]
        arf_table_name = os.environ["DOCUMENT_STORE_DYNAMODB_NAME"]
        arf_document_references: list[str] = documents.get(
            SupportedDocumentTypes.ARF.value
        )
        lg_document_references: list[str] = documents.get(
            SupportedDocumentTypes.LG.value
        )

        if not arf_document_references and not lg_document_references:
            logger.error("Document object is missing a document type")
            raise UploadConfirmResultException(
                400, LambdaError.UploadConfirmResultProps
            )

        try:
            if arf_document_references:
                self.verify_virus_scan_result(
                    doc_type=SupportedDocumentTypes.ARF,
                    document_references=arf_document_references,
                )

                self.move_files_and_update_dynamo(
                    arf_document_references,
                    arf_bucket_name,
                    arf_table_name,
                    SupportedDocumentTypes.ARF,
                )

            if lg_document_references:
                self.verify_virus_scan_result(
                    doc_type=SupportedDocumentTypes.LG,
                    document_references=lg_document_references,
                )
                self.validate_number_of_documents(
                    SupportedDocumentTypes.LG, lg_document_references
                )
                self.move_files_and_update_dynamo(
                    lg_document_references,
                    lg_bucket_name,
                    lg_table_name,
                    SupportedDocumentTypes.LG,
                )

                if len(lg_document_references) == 1:
                    logger.info("Sending message to NRL queue.")
                    self.send_message_to_nrl_queue(lg_document_references[0])
                else:
                    logger.info(
                        "Did not create NRL pointer, more than one document uploaded."
                    )

        except ClientError as e:
            logger.error(f"Error with one of our services: {str(e)}")
            raise UploadConfirmResultException(
                500, LambdaError.UploadConfirmResultAWSFailure
            )

    def move_files_and_update_dynamo(
        self,
        document_references: list,
        bucket_name: str,
        table_name: str,
        doc_type: str,
    ):
        self.copy_files_from_staging_bucket(document_references, bucket_name, doc_type)

        logger.info(
            "Files successfully copied, deleting files from staging bucket and updating dynamo db table"
        )

        for document_reference in document_references:
            self.delete_file_from_staging_bucket(document_reference, doc_type)
            self.update_dynamo_table(table_name, document_reference, bucket_name)

    def copy_files_from_staging_bucket(
        self, document_references: list, bucket_name: str, doc_type: str
    ):
        logger.info("Copying files from staging bucket")

        for document_reference in document_references:
            dest_file_key = f"{self.nhs_number}/{document_reference}"
            source_file_key = (
                f"user_upload/{doc_type}/{self.nhs_number}/{document_reference}"
            )

            self.s3_service.copy_across_bucket(
                source_bucket=self.staging_bucket,
                source_file_key=source_file_key,
                dest_bucket=bucket_name,
                dest_file_key=dest_file_key,
            )

    def delete_file_from_staging_bucket(self, document_reference: str, doc_type):
        file_key = f"user_upload/{doc_type}/{self.nhs_number}/{document_reference}"

        self.s3_service.delete_object(self.staging_bucket, file_key)

    def update_dynamo_table(
        self, table_name: str, document_reference: str, bucket_name: str
    ):
        file_location = f"s3://{bucket_name}/{self.nhs_number}/{document_reference}"
        file_size = self.s3_service.get_file_size(bucket_name, file_location)
        self.dynamo_service.update_item(
            table_name=table_name,
            key_pair={DocumentReferenceMetadataFields.ID.value: document_reference},
            updated_fields={
                "Uploaded": True,
                "Uploading": False,
                "FileLocation": file_location,
                "DocStatus": "final",
                "Size": file_size,
            },
        )

    def validate_number_of_documents(
        self, doc_type: SupportedDocumentTypes, document_references: list
    ):
        logger.info(
            "Checking number of document references in list matches number of documents in dynamo table"
        )

        items = self.document_service.fetch_available_document_references_by_type(
            nhs_number=self.nhs_number, doc_type=doc_type, query_filter=NotDeleted
        )

        if len(items) != len(document_references):
            logger.error(
                "Number of document references not equal to number of documents in dynamo table for this nhs number"
            )
            raise UploadConfirmResultException(
                400, LambdaError.UploadConfirmResultBadRequest
            )

    def verify_virus_scan_result(
        self, doc_type: SupportedDocumentTypes, document_references: list[str]
    ):
        all_clean_records = (
            self.document_service.fetch_available_document_references_by_type(
                nhs_number=self.nhs_number, doc_type=doc_type, query_filter=CleanFiles
            )
        )
        ids_of_clean_records = [record.id for record in all_clean_records]
        all_incoming_doc_ref_are_clean = set(document_references).issubset(
            ids_of_clean_records
        )

        if not all_incoming_doc_ref_are_clean:
            raise UploadConfirmResultException(
                400, LambdaError.UploadConfirmResultFilesNotClean
            )

    def send_message_to_nrl_queue(self, document_reference):

        document_api_endpoint = (
            os.environ.get("APIM_API_URL")
            + "/DocumentReference/"
            + SnomedCodes.LLOYD_GEORGE.value.code
            + "~"
            + document_reference
        )
        doc_details = Attachment(
            url=document_api_endpoint,
        )
        nrl_sqs_message = NrlSqsMessage(
            nhs_number=self.nhs_number,
            action=NrlActionTypes.CREATE,
            attachment=doc_details,
        )
        self.sqs_service.send_message_fifo(
            queue_url=self.nrl_queue_url,
            message_body=nrl_sqs_message.model_dump_json(exclude_none=True),
            group_id=f"nrl_sqs_{uuid.uuid4()}",
        )
        logger.info("Message sent to NRL queue.")
