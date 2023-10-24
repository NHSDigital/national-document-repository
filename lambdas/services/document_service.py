import logging
import os
from datetime import datetime, timezone

from enums.metadata_field_names import DocumentReferenceMetadataFields
from enums.s3_lifecycle_tags import S3LifecycleDays, S3LifecycleTags
from enums.supported_document_types import SupportedDocumentTypes
from models.document_reference import DocumentReference
from services.dynamo_service import DynamoDBService
from services.s3_service import S3Service

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class DocumentService(DynamoDBService):
    def __init__(self):
        super().__init__()
        self.s3_service = S3Service()

    def fetch_available_document_references_by_type(
        self, nhs_number: str, doc_types: str
    ) -> list[DocumentReference]:
        arf_documents = []
        lg_documents = []

        delete_filter = {DocumentReferenceMetadataFields.DELETED.value: ""}

        if SupportedDocumentTypes.ARF.name in doc_types:
            logger.info("Retrieving ARF documents")
            arf_documents = self.fetch_documents_from_table_with_filter(
                nhs_number,
                os.environ["DOCUMENT_STORE_DYNAMODB_NAME"],
                attr_filter=delete_filter,
            )
        if SupportedDocumentTypes.LG.name in doc_types:
            logger.info("Retrieving Lloyd George documents")
            lg_documents = self.fetch_documents_from_table_with_filter(
                nhs_number,
                os.environ["LLOYD_GEORGE_DYNAMODB_NAME"],
                attr_filter=delete_filter,
            )

        return arf_documents + lg_documents

    def fetch_documents_from_table(
        self, nhs_number: str, table: str
    ) -> list[DocumentReference]:
        documents = []
        response = self.query_with_requested_fields(
            table_name=table,
            index_name="NhsNumberIndex",
            search_key="NhsNumber",
            search_condition=nhs_number,
            requested_fields=DocumentReferenceMetadataFields.list(),
        )

        for item in response["Items"]:
            document = DocumentReference.model_validate(item)
            documents.append(document)
        return documents

    def fetch_documents_from_table_with_filter(
        self, nhs_number: str, table: str, attr_filter: dict
    ) -> list[DocumentReference]:
        documents = []

        response = self.query_with_requested_fields(
            table_name=table,
            index_name="NhsNumberIndex",
            search_key="NhsNumber",
            search_condition=nhs_number,
            requested_fields=DocumentReferenceMetadataFields.list(),
            filtered_fields=attr_filter,
        )

        for item in response["Items"]:
            document = DocumentReference.model_validate(item)
            documents.append(document)
        return documents

    def delete_documents(
        self,
        table_name: str,
        document_references: list[DocumentReference],
        type_of_delete: str,
    ):
        deletion_date = datetime.now(timezone.utc)

        if type_of_delete == S3LifecycleTags.DEATH_DELETE.value:
            ttl_days = S3LifecycleDays.DEATH_DELETE
        else:
            ttl_days = S3LifecycleDays.SOFT_DELETE

        ttl_seconds = ttl_days * 24 * 60 * 60
        document_reference_ttl = int(deletion_date.timestamp() + ttl_seconds)

        update_fields = {
            DocumentReferenceMetadataFields.DELETED.value: deletion_date.strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),
            DocumentReferenceMetadataFields.TTL.value: document_reference_ttl,
        }

        logger.info(f"Deleting items in table: {table_name}")

        for reference in document_references:
            self.s3_service.create_object_tag(
                file_key=reference.get_file_key(),
                s3_bucket_name=reference.get_file_bucket(),
                tag_key=str(S3LifecycleTags.SOFT_DELETE.value),
                tag_value=str(S3LifecycleTags.SOFT_DELETE_VAL.value),
            )

            self.update_item(table_name, reference.id, updated_fields=update_fields)
