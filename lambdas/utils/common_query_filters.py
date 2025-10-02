from enums.dynamo_filter import AttributeOperator
from enums.virus_scan_result import VirusScanResult
from utils.dynamo_query_filter_builder import DynamoQueryFilterBuilder


def get_not_deleted_filter(filter_builder: DynamoQueryFilterBuilder):
    filter_builder.add_condition("Deleted", AttributeOperator.EQUAL, "")
    delete_filter_expression = filter_builder.build()
    filter_builder.add_condition("Deleted", AttributeOperator.NOT_EXISTS)
    delete_does_not_exist_filter_expression = filter_builder.build()
    return delete_filter_expression | delete_does_not_exist_filter_expression


def get_upload_complete_filter(filter_builder: DynamoQueryFilterBuilder):
    filter_builder.add_condition("Uploaded", AttributeOperator.EQUAL, True)
    upload_filter_expression = filter_builder.build()
    filter_not_deleted = get_not_deleted_filter(filter_builder)
    return upload_filter_expression & filter_not_deleted


def get_upload_incomplete_filter(filter_builder: DynamoQueryFilterBuilder):
    filter_builder.add_condition("Uploaded", AttributeOperator.EQUAL, False)
    upload_filter_expression = filter_builder.build()
    filter_not_deleted = get_not_deleted_filter(filter_builder)
    return upload_filter_expression & filter_not_deleted


def get_clean_files_filter(filter_builder: DynamoQueryFilterBuilder):
    filter_builder.add_condition(
        "VirusScannerResult", AttributeOperator.EQUAL, VirusScanResult.CLEAN.value
    )
    clean_filter_expression = filter_builder.build()
    filter_not_deleted = get_not_deleted_filter(filter_builder)
    return clean_filter_expression & filter_not_deleted


def get_current_files_filter(filter_builder: DynamoQueryFilterBuilder):
    filter_builder.add_condition("Status", AttributeOperator.EQUAL, "current")
    clean_filter_expression = filter_builder.build()
    filter_not_deleted = get_not_deleted_filter(filter_builder)
    return clean_filter_expression & filter_not_deleted


def get_doc_status_preliminary_filter(filter_builder: DynamoQueryFilterBuilder):
    filter_builder.add_condition("DocStatus", AttributeOperator.EQUAL, "preliminary")
    doc_status_filter_expression = filter_builder.build()
    filter_not_deleted = get_not_deleted_filter(filter_builder)
    return doc_status_filter_expression & filter_not_deleted

def get_doc_status_final_filter(filter_builder: DynamoQueryFilterBuilder):
    filter_builder.add_condition("DocStatus", AttributeOperator.EQUAL, "final")
    doc_status_filter_expression = filter_builder.build()
    filter_not_deleted = get_not_deleted_filter(filter_builder)
    return doc_status_filter_expression & filter_not_deleted

def not_document_id(document_id: str):
    filter_builder = DynamoQueryFilterBuilder()
    filter_builder.add_condition("DocumentId", AttributeOperator.NOT_EQUAL, document_id)
    return filter_builder.build()

NotDeleted = get_not_deleted_filter(DynamoQueryFilterBuilder())

UploadCompleted = get_upload_complete_filter(DynamoQueryFilterBuilder())

UploadIncomplete = get_upload_incomplete_filter(DynamoQueryFilterBuilder())

CleanFiles = get_clean_files_filter(DynamoQueryFilterBuilder())

CurrentStatusFile = get_current_files_filter(DynamoQueryFilterBuilder())

PreliminaryStatus = get_doc_status_preliminary_filter(DynamoQueryFilterBuilder())

FinalStatusFilter = get_doc_status_final_filter(DynamoQueryFilterBuilder())
