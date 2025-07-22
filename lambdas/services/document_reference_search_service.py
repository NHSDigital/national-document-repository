import json
import os
from json import JSONDecodeError

from botocore.exceptions import ClientError
from enums.dynamo_filter import AttributeOperator
from enums.lambda_error import LambdaError
from enums.metadata_field_names import DocumentReferenceMetadataFields
from enums.snomed_codes import SnomedCodes
from models.document_reference import DocumentReference
from models.fhir.R4.bundle import Bundle, BundleEntry
from models.fhir.R4.fhir_document_reference import Attachment, DocumentReferenceInfo
from pydantic import ValidationError
from services.document_service import DocumentService
from utils.audit_logging_setup import LoggingService
from utils.common_query_filters import NotDeleted, UploadCompleted
from utils.dynamo_query_filter_builder import DynamoQueryFilterBuilder
from utils.exceptions import DynamoServiceException
from utils.lambda_exceptions import DocumentRefSearchException

logger = LoggingService(__name__)


class DocumentReferenceSearchService(DocumentService):
    def get_document_references(
        self, nhs_number: str, return_fhir: bool = False, additional_filters=None
    ):
        """
        Fetch document references for a given NHS number.

        :param nhs_number: The NHS number to search for.
        :param return_fhir: If True, return FHIR DocumentReference objects.
        :param additional_filters: Additional filters to apply to the search.
        :return: List of document references or FHIR DocumentReferences.
        """
        try:
            list_of_table_names = self._get_table_names()
            results = self._search_tables_for_documents(
                nhs_number, list_of_table_names, return_fhir, additional_filters
            )
            return results
        except (
            JSONDecodeError,
            ValidationError,
            ClientError,
            DynamoServiceException,
        ) as e:
            logger.error(
                f"{LambdaError.DocRefClient.to_str()}: {str(e)}",
                {"Result": "Document reference search failed"},
            )
            raise DocumentRefSearchException(500, LambdaError.DocRefClient)

    def _get_table_names(self) -> list[str]:
        try:
            return json.loads(os.environ["DYNAMODB_TABLE_LIST"])
        except JSONDecodeError as e:
            logger.error(f"Failed to decode table list: {str(e)}")
            raise

    def _search_tables_for_documents(
        self, nhs_number: str, table_names: list[str], return_fhir: bool, filters=None
    ):
        document_resources = []
        for table_name in table_names:
            logger.info(f"Searching for results in {table_name}")
            if filters:
                filter_expression = self._build_filter_expression(filters)
            else:
                filter_expression = UploadCompleted
            documents = self.fetch_documents_from_table_with_nhs_number(
                nhs_number, table_name, query_filter=filter_expression
            )
            self._validate_upload_status(documents)
            document_resources.extend(
                self._process_documents(documents, return_fhir=return_fhir)
            )
        if not document_resources:
            return None
        logger.info(f"Found {len(document_resources)} document references")

        if not return_fhir:
            return document_resources

        entries = []
        for doc_resource in document_resources:
            entry = BundleEntry(resource=doc_resource)
            entries.append(entry)

        bundle = Bundle(
            type="searchset",
            total=len(entries),
            entry=entries,
        ).model_dump(exclude_none=True)

        return bundle

    def _validate_upload_status(self, documents: list[DocumentReference]):
        if self.is_upload_in_process(documents):
            logger.error(
                "Records are in the process of being uploaded. Will not process the new upload.",
                {"Result": "Document reference search failed"},
            )
            raise DocumentRefSearchException(423, LambdaError.UploadInProgressError)

    def _process_documents(
        self, documents: list[DocumentReference], return_fhir: bool
    ) -> list[dict]:
        results = []
        for document in documents:
            if not document.file_size:
                document.file_size = self.s3_service.get_file_size(
                    s3_bucket_name=document.s3_bucket_name,
                    object_key=document.s3_file_key,
                )

            if return_fhir:
                fhir_response = self.create_document_reference_fhir_response(document)
                results.append(fhir_response)
            else:
                document_model = self._build_document_model(document)
                results.append(document_model)
        return results

    def _build_document_model(self, document: DocumentReference) -> dict:
        document_formatted = document.model_dump_camel_case(
            exclude_none=True,
            include={
                "id",
                "file_name",
                "created",
                "virus_scanner_result",
                "file_size",
            },
        )
        return document_formatted

    def _build_filter_expression(self, filter_values: dict[str, str]):
        filter_builder = DynamoQueryFilterBuilder()
        for filter_key, filter_value in filter_values.items():
            if filter_key == "custodian":
                filter_builder.add_condition(
                    attribute=str(DocumentReferenceMetadataFields.CURRENT_GP_ODS.value),
                    attr_operator=AttributeOperator.EQUAL,
                    filter_value=filter_value,
                )
            elif filter_key == "file_type":
                # placeholder for future filtering
                pass

        filter_builder.add_condition(
            attribute=str(DocumentReferenceMetadataFields.UPLOADED.value),
            attr_operator=AttributeOperator.EQUAL,
            filter_value=True,
        )
        filter_expression = filter_builder.build() & NotDeleted
        return filter_expression

    def create_document_reference_fhir_response(
        self,
        document_reference: DocumentReference,
    ) -> dict:
        document_retrieve_endpoint = os.getenv("DOCUMENT_RETRIEVE_ENDPOINT_APIM", "")
        document_details = Attachment(
            title=document_reference.file_name,
            creation=document_reference.document_scan_creation
            or document_reference.created,
            url=document_retrieve_endpoint
            + "/"
            + SnomedCodes.LLOYD_GEORGE.value.code
            + "~"
            + document_reference.id,
        )
        fhir_document_reference = (
            DocumentReferenceInfo(
                nhs_number=document_reference.nhs_number,
                attachment=document_details,
                custodian=document_reference.current_gp_ods,
                snomed_code_doc_type=SnomedCodes.find_by_code(
                    document_reference.document_snomed_code_type
                ),
            )
            .create_fhir_document_reference_object(document_reference)
            .model_dump(exclude_none=True)
        )
        return fhir_document_reference
