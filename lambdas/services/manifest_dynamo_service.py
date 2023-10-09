import logging
import os

from enums.supported_document_types import SupportedDocumentTypes
from services.dynamo_service import DynamoDBService
from enums.metadata_field_names import DocumentReferenceMetadataFields
from models.document import Document
from utils.exceptions import DynamoDbException

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class ManifestDynamoService(DynamoDBService):

    def discover_uploaded_documents(
            self, nhs_number: str, doc_type: SupportedDocumentTypes
    ) -> list[Document]:
        documents = []
        if doc_type == SupportedDocumentTypes.ARF:
            document_table = os.environ["DOCUMENT_STORE_DYNAMODB_NAME"]
        elif doc_type == SupportedDocumentTypes.LG:
            document_table = os.environ["LLOYD_GEORGE_DYNAMODB_NAME"]
        else:
            return documents
        response = self.query_service(
            document_table,
            "NhsNumberIndex",
            "NhsNumber",
            nhs_number,
            [
                DocumentReferenceMetadataFields.FILE_NAME,
                DocumentReferenceMetadataFields.FILE_LOCATION,
                DocumentReferenceMetadataFields.VIRUS_SCAN_RESULT,
            ],
        )

        for item in response["Items"]:
            document = Document(
                nhs_number=nhs_number,
                file_name=item[DocumentReferenceMetadataFields.FILE_NAME.field_name],
                virus_scanner_result=item[
                    DocumentReferenceMetadataFields.VIRUS_SCAN_RESULT.field_name
                ],
                file_location=item[
                    DocumentReferenceMetadataFields.FILE_LOCATION.field_name
                ],
            )
            documents.append(document)
        return documents
