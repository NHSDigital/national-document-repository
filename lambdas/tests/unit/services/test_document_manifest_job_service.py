from unittest.mock import call

import pytest
from enums.dynamo_filter import AttributeOperator
from enums.lambda_error import LambdaError
from enums.supported_document_types import SupportedDocumentTypes
from enums.trace_status import TraceStatus
from freezegun import freeze_time
from models.zip_trace import DocumentManifestJob, DocumentManifestZipTrace
from services.document_manifest_job_service import DocumentManifestJobService
from tests.unit.conftest import (
    MOCK_ZIP_OUTPUT_BUCKET,
    MOCK_ZIP_TRACE_TABLE,
    TEST_DOCUMENT_LOCATION,
    TEST_FILE_KEY,
    TEST_NHS_NUMBER,
    TEST_UUID,
)
from tests.unit.helpers.data.s3_responses import MOCK_PRESIGNED_URL_RESPONSE
from tests.unit.helpers.data.test_documents import (
    create_test_doc_store_refs,
    create_test_lloyd_george_doc_store_refs,
)
from utils.common_query_filters import UploadCompleted
from utils.dynamo_query_filter_builder import DynamoQueryFilterBuilder
from utils.lambda_exceptions import DocumentManifestJobServiceException

TEST_DOC_STORE_DOCUMENT_REFS = create_test_doc_store_refs()
TEST_LLOYD_GEORGE_DOCUMENT_REFS = create_test_lloyd_george_doc_store_refs()
TEST_DOC_REFERENCE_IDs = [
    "3d8683b9-1665-40d2-8499-6e8302d507ff",
    "4d8683b9-1665-40d2-8499-6e8302d507ff",
    "5d8683b9-1665-40d2-8499-6e8302d507ff",
]

TEST_FILES_TO_DOWNLOAD = {
    TEST_LLOYD_GEORGE_DOCUMENT_REFS[0]
    .file_location: TEST_LLOYD_GEORGE_DOCUMENT_REFS[0]
    .file_name,
    TEST_LLOYD_GEORGE_DOCUMENT_REFS[1]
    .file_location: TEST_LLOYD_GEORGE_DOCUMENT_REFS[1]
    .file_name,
    TEST_LLOYD_GEORGE_DOCUMENT_REFS[2]
    .file_location: TEST_LLOYD_GEORGE_DOCUMENT_REFS[2]
    .file_name,
}

TEST_ZIP_TRACE_DATA = {
    "ID": TEST_UUID,
    "JobId": TEST_UUID,
    "Created": "2024-01-01T12:00:00Z",
    "FilesToDownload": TEST_FILES_TO_DOWNLOAD,
    "JobStatus": TraceStatus.PENDING,
    "NhsNumber": TEST_NHS_NUMBER,
    "ZipFileLocation": "",
}


@pytest.fixture
def manifest_service(mocker, set_env):
    mocker.patch("boto3.client")
    mocker.patch("services.base.iam_service.IAMService")

    service = DocumentManifestJobService()
    mocker.patch.object(service, "s3_service")
    mocker.patch.object(service, "dynamo_service")
    mocker.patch.object(service, "document_service")
    yield service


@pytest.fixture
def mock_document_service(mocker, manifest_service):
    mock_document_service = manifest_service.document_service
    mocker.patch.object(
        mock_document_service, "fetch_available_document_references_by_type"
    )
    yield mock_document_service


@pytest.fixture
def mock_s3_service(mocker, manifest_service):
    mock_s3_service = manifest_service.s3_service
    mocker.patch.object(mock_s3_service, "create_download_presigned_url")
    mock_s3_service.create_download_presigned_url.return_value = (
        MOCK_PRESIGNED_URL_RESPONSE
    )
    mocker.patch.object(mock_s3_service, "file_exist_on_s3")
    yield mock_s3_service


@pytest.fixture
def mock_dynamo_service(mocker, manifest_service):
    mock_dynamo_service = manifest_service.dynamo_service
    mocker.patch.object(mock_dynamo_service, "create_item")
    mocker.patch.object(mock_dynamo_service, "query_table_by_index")
    yield mock_dynamo_service


@pytest.fixture
def mock_filter_documents_by_reference(mocker, manifest_service):
    yield mocker.patch.object(manifest_service, "filter_documents_by_reference")


@pytest.fixture
def mock_handle_duplicate_document_filenames(mocker, manifest_service):
    yield mocker.patch.object(manifest_service, "handle_duplicate_document_filenames")


@pytest.fixture
def mock_write_zip_trace(mocker, manifest_service):
    yield mocker.patch.object(manifest_service, "write_zip_trace")


@pytest.fixture
def mock_create_presigned_url(mocker, manifest_service):
    yield mocker.patch.object(
        manifest_service, "create_document_manifest_presigned_url"
    )


@pytest.fixture
def mock_query_zip_trace(mocker, manifest_service):
    yield mocker.patch.object(manifest_service, "query_zip_trace")


@pytest.fixture
def mock_query_filter(mocker):
    query_filter = mocker.patch("utils.common_query_filters.UploadCompleted")
    query_filter.return_value = UploadCompleted
    yield query_filter.return_value


@pytest.fixture
def mock_filter_expression():
    filter_builder = DynamoQueryFilterBuilder()
    filter_expression = filter_builder.add_condition(
        attribute="NhsNumber",
        attr_operator=AttributeOperator.EQUAL,
        filter_value=TEST_NHS_NUMBER,
    ).build()
    yield filter_expression


def test_create_document_manifest_job_raises_exception(
    manifest_service, mock_document_service
):
    mock_document_service.fetch_available_document_references_by_type.return_value = []

    with pytest.raises(DocumentManifestJobServiceException) as e:
        manifest_service.create_document_manifest_job(
            nhs_number=TEST_NHS_NUMBER, doc_types=[SupportedDocumentTypes.ARF]
        )

    assert e.value == DocumentManifestJobServiceException(
        404, LambdaError.ManifestNoDocs
    )


def test_create_document_manifest_job_for_arf(
    manifest_service,
    mock_query_filter,
    mock_document_service,
    mock_filter_documents_by_reference,
    mock_handle_duplicate_document_filenames,
    mock_uuid,
    mock_write_zip_trace,
):
    mock_document_service.fetch_available_document_references_by_type.return_value = (
        TEST_DOC_STORE_DOCUMENT_REFS
    )
    mock_handle_duplicate_document_filenames.return_value = TEST_DOC_STORE_DOCUMENT_REFS
    mock_write_zip_trace.return_value = TEST_UUID

    expected = TEST_UUID

    response = manifest_service.create_document_manifest_job(
        nhs_number=TEST_NHS_NUMBER, doc_types=[SupportedDocumentTypes.ARF]
    )

    mock_document_service.fetch_available_document_references_by_type.assert_called_once_with(
        nhs_number=TEST_NHS_NUMBER,
        doc_type=SupportedDocumentTypes.ARF,
        query_filter=mock_query_filter,
    )
    mock_filter_documents_by_reference.assert_not_called()
    mock_write_zip_trace.assert_called_once_with(
        {
            TEST_DOC_STORE_DOCUMENT_REFS[0]
            .file_location: TEST_DOC_STORE_DOCUMENT_REFS[0]
            .file_name,
            TEST_DOC_STORE_DOCUMENT_REFS[1]
            .file_location: TEST_DOC_STORE_DOCUMENT_REFS[1]
            .file_name,
            TEST_DOC_STORE_DOCUMENT_REFS[2]
            .file_location: TEST_DOC_STORE_DOCUMENT_REFS[2]
            .file_name,
        },
        TEST_NHS_NUMBER,
    )
    assert response == expected


def test_create_document_manifest_job_for_lg(
    manifest_service,
    mock_query_filter,
    mock_document_service,
    mock_filter_documents_by_reference,
    mock_handle_duplicate_document_filenames,
    mock_uuid,
    mock_write_zip_trace,
):
    mock_document_service.fetch_available_document_references_by_type.return_value = (
        TEST_LLOYD_GEORGE_DOCUMENT_REFS
    )
    mock_handle_duplicate_document_filenames.return_value = (
        TEST_LLOYD_GEORGE_DOCUMENT_REFS
    )
    mock_write_zip_trace.return_value = TEST_UUID
    expected = TEST_UUID

    response = manifest_service.create_document_manifest_job(
        nhs_number=TEST_NHS_NUMBER, doc_types=[SupportedDocumentTypes.LG]
    )

    mock_document_service.fetch_available_document_references_by_type.assert_called_once_with(
        nhs_number=TEST_NHS_NUMBER,
        doc_type=SupportedDocumentTypes.LG,
        query_filter=mock_query_filter,
    )
    mock_filter_documents_by_reference.assert_not_called()
    mock_write_zip_trace.assert_called_once_with(
        {
            TEST_LLOYD_GEORGE_DOCUMENT_REFS[0]
            .file_location: TEST_LLOYD_GEORGE_DOCUMENT_REFS[0]
            .file_name,
            TEST_LLOYD_GEORGE_DOCUMENT_REFS[1]
            .file_location: TEST_LLOYD_GEORGE_DOCUMENT_REFS[1]
            .file_name,
            TEST_LLOYD_GEORGE_DOCUMENT_REFS[2]
            .file_location: TEST_LLOYD_GEORGE_DOCUMENT_REFS[2]
            .file_name,
        },
        TEST_NHS_NUMBER,
    )
    assert response == expected


def test_create_document_manifest_job_for_both(
    manifest_service,
    mock_query_filter,
    mock_document_service,
    mock_filter_documents_by_reference,
    mock_handle_duplicate_document_filenames,
    mock_uuid,
    mock_write_zip_trace,
):
    manifest_service.document_service.fetch_available_document_references_by_type.side_effect = [
        TEST_LLOYD_GEORGE_DOCUMENT_REFS,
        TEST_DOC_STORE_DOCUMENT_REFS,
    ]
    mock_handle_duplicate_document_filenames.return_value = (
        TEST_LLOYD_GEORGE_DOCUMENT_REFS + TEST_DOC_STORE_DOCUMENT_REFS
    )
    mock_write_zip_trace.return_value = TEST_UUID

    expected = TEST_UUID
    expected_calls = [
        call(
            nhs_number=TEST_NHS_NUMBER,
            doc_type=SupportedDocumentTypes.LG,
            query_filter=mock_query_filter,
        ),
        call(
            nhs_number=TEST_NHS_NUMBER,
            doc_type=SupportedDocumentTypes.ARF,
            query_filter=mock_query_filter,
        ),
    ]

    response = manifest_service.create_document_manifest_job(
        nhs_number=TEST_NHS_NUMBER,
        doc_types=[SupportedDocumentTypes.LG, SupportedDocumentTypes.ARF],
    )

    mock_document_service.fetch_available_document_references_by_type.assert_has_calls(
        expected_calls
    )
    mock_filter_documents_by_reference.assert_not_called()
    mock_write_zip_trace.assert_called_once_with(
        {
            TEST_LLOYD_GEORGE_DOCUMENT_REFS[0]
            .file_location: TEST_LLOYD_GEORGE_DOCUMENT_REFS[0]
            .file_name,
            TEST_LLOYD_GEORGE_DOCUMENT_REFS[1]
            .file_location: TEST_LLOYD_GEORGE_DOCUMENT_REFS[1]
            .file_name,
            TEST_LLOYD_GEORGE_DOCUMENT_REFS[2]
            .file_location: TEST_LLOYD_GEORGE_DOCUMENT_REFS[2]
            .file_name,
            TEST_DOC_STORE_DOCUMENT_REFS[0]
            .file_location: TEST_DOC_STORE_DOCUMENT_REFS[0]
            .file_name,
            TEST_DOC_STORE_DOCUMENT_REFS[1]
            .file_location: TEST_DOC_STORE_DOCUMENT_REFS[1]
            .file_name,
            TEST_DOC_STORE_DOCUMENT_REFS[2]
            .file_location: TEST_DOC_STORE_DOCUMENT_REFS[2]
            .file_name,
        },
        TEST_NHS_NUMBER,
    )
    assert response == expected


def test_create_document_manifest_job_for_arf_with_doc_references(
    manifest_service,
    mock_query_filter,
    mock_document_service,
    mock_filter_documents_by_reference,
    mock_handle_duplicate_document_filenames,
    mock_uuid,
    mock_write_zip_trace,
):
    mock_document_service.fetch_available_document_references_by_type.return_value = (
        TEST_DOC_STORE_DOCUMENT_REFS
    )
    mock_filter_documents_by_reference.return_value = TEST_DOC_STORE_DOCUMENT_REFS
    mock_handle_duplicate_document_filenames.return_value = TEST_DOC_STORE_DOCUMENT_REFS
    mock_write_zip_trace.return_value = TEST_UUID

    expected = TEST_UUID

    response = manifest_service.create_document_manifest_job(
        nhs_number=TEST_NHS_NUMBER,
        doc_types=[SupportedDocumentTypes.ARF],
        selected_document_references=TEST_DOC_REFERENCE_IDs,
    )

    mock_document_service.fetch_available_document_references_by_type.assert_called_once_with(
        nhs_number=TEST_NHS_NUMBER,
        doc_type=SupportedDocumentTypes.ARF,
        query_filter=mock_query_filter,
    )
    mock_filter_documents_by_reference.assert_called_once_with(
        selected_document_references=TEST_DOC_REFERENCE_IDs,
    )
    mock_write_zip_trace.assert_called_once_with(
        {
            TEST_DOC_STORE_DOCUMENT_REFS[0]
            .file_location: TEST_DOC_STORE_DOCUMENT_REFS[0]
            .file_name,
            TEST_DOC_STORE_DOCUMENT_REFS[1]
            .file_location: TEST_DOC_STORE_DOCUMENT_REFS[1]
            .file_name,
            TEST_DOC_STORE_DOCUMENT_REFS[2]
            .file_location: TEST_DOC_STORE_DOCUMENT_REFS[2]
            .file_name,
        },
        TEST_NHS_NUMBER,
    )
    assert response == expected


def test_create_document_manifest_job_for_lg_with_doc_references(
    manifest_service,
    mock_query_filter,
    mock_document_service,
    mock_filter_documents_by_reference,
    mock_handle_duplicate_document_filenames,
    mock_uuid,
    mock_write_zip_trace,
):
    mock_document_service.fetch_available_document_references_by_type.return_value = (
        TEST_LLOYD_GEORGE_DOCUMENT_REFS
    )
    mock_filter_documents_by_reference.return_value = TEST_LLOYD_GEORGE_DOCUMENT_REFS
    mock_handle_duplicate_document_filenames.return_value = (
        TEST_LLOYD_GEORGE_DOCUMENT_REFS
    )
    mock_write_zip_trace.return_value = TEST_UUID

    expected = TEST_UUID

    response = manifest_service.create_document_manifest_job(
        nhs_number=TEST_NHS_NUMBER,
        doc_types=[SupportedDocumentTypes.LG],
        selected_document_references=TEST_DOC_REFERENCE_IDs,
    )

    mock_document_service.fetch_available_document_references_by_type.assert_called_once_with(
        nhs_number=TEST_NHS_NUMBER,
        doc_type=SupportedDocumentTypes.LG,
        query_filter=mock_query_filter,
    )
    mock_filter_documents_by_reference.assert_called_once_with(
        selected_document_references=TEST_DOC_REFERENCE_IDs,
    )
    mock_write_zip_trace.assert_called_once_with(
        {
            TEST_LLOYD_GEORGE_DOCUMENT_REFS[0]
            .file_location: TEST_LLOYD_GEORGE_DOCUMENT_REFS[0]
            .file_name,
            TEST_LLOYD_GEORGE_DOCUMENT_REFS[1]
            .file_location: TEST_LLOYD_GEORGE_DOCUMENT_REFS[1]
            .file_name,
            TEST_LLOYD_GEORGE_DOCUMENT_REFS[2]
            .file_location: TEST_LLOYD_GEORGE_DOCUMENT_REFS[2]
            .file_name,
        },
        TEST_NHS_NUMBER,
    )
    assert response == expected


def test_create_document_manifest_job_for_both_with_doc_references(
    manifest_service,
    mock_query_filter,
    mock_document_service,
    mock_filter_documents_by_reference,
    mock_handle_duplicate_document_filenames,
    mock_uuid,
    mock_write_zip_trace,
):
    manifest_service.document_service.fetch_available_document_references_by_type.side_effect = [
        TEST_LLOYD_GEORGE_DOCUMENT_REFS,
        TEST_DOC_STORE_DOCUMENT_REFS,
    ]
    mock_filter_documents_by_reference.return_value = (
        TEST_LLOYD_GEORGE_DOCUMENT_REFS + TEST_DOC_STORE_DOCUMENT_REFS
    )
    mock_handle_duplicate_document_filenames.return_value = (
        TEST_LLOYD_GEORGE_DOCUMENT_REFS + TEST_DOC_STORE_DOCUMENT_REFS
    )
    mock_write_zip_trace.return_value = TEST_UUID

    expected = TEST_UUID
    expected_calls = [
        call(
            nhs_number=TEST_NHS_NUMBER,
            doc_type=SupportedDocumentTypes.LG,
            query_filter=mock_query_filter,
        ),
        call(
            nhs_number=TEST_NHS_NUMBER,
            doc_type=SupportedDocumentTypes.ARF,
            query_filter=mock_query_filter,
        ),
    ]

    response = manifest_service.create_document_manifest_job(
        nhs_number=TEST_NHS_NUMBER,
        doc_types=[SupportedDocumentTypes.LG, SupportedDocumentTypes.ARF],
        selected_document_references=TEST_DOC_REFERENCE_IDs,
    )

    mock_document_service.fetch_available_document_references_by_type.assert_has_calls(
        expected_calls
    )
    mock_filter_documents_by_reference.assert_called_once_with(
        selected_document_references=TEST_DOC_REFERENCE_IDs,
    )
    mock_write_zip_trace.assert_called_once_with(
        {
            TEST_LLOYD_GEORGE_DOCUMENT_REFS[0]
            .file_location: TEST_LLOYD_GEORGE_DOCUMENT_REFS[0]
            .file_name,
            TEST_LLOYD_GEORGE_DOCUMENT_REFS[1]
            .file_location: TEST_LLOYD_GEORGE_DOCUMENT_REFS[1]
            .file_name,
            TEST_LLOYD_GEORGE_DOCUMENT_REFS[2]
            .file_location: TEST_LLOYD_GEORGE_DOCUMENT_REFS[2]
            .file_name,
            TEST_DOC_STORE_DOCUMENT_REFS[0]
            .file_location: TEST_DOC_STORE_DOCUMENT_REFS[0]
            .file_name,
            TEST_DOC_STORE_DOCUMENT_REFS[1]
            .file_location: TEST_DOC_STORE_DOCUMENT_REFS[1]
            .file_name,
            TEST_DOC_STORE_DOCUMENT_REFS[2]
            .file_location: TEST_DOC_STORE_DOCUMENT_REFS[2]
            .file_name,
        },
        TEST_NHS_NUMBER,
    )
    assert response == expected


def test_filter_documents_by_reference_valid_multiple(manifest_service):
    manifest_service.documents = TEST_DOC_STORE_DOCUMENT_REFS
    expected = TEST_DOC_STORE_DOCUMENT_REFS[:-1]

    response = manifest_service.filter_documents_by_reference(
        selected_document_references=TEST_DOC_REFERENCE_IDs[:-1],
    )

    assert expected == response


def test_filter_documents_by_reference_valid_singular(manifest_service):
    manifest_service.documents = TEST_DOC_STORE_DOCUMENT_REFS
    expected = [TEST_DOC_STORE_DOCUMENT_REFS[0]]

    response = manifest_service.filter_documents_by_reference(
        selected_document_references=[TEST_DOC_REFERENCE_IDs[0]],
    )

    assert expected == response


def test_filter_documents_by_reference_raises_exception(manifest_service):
    manifest_service.documents = TEST_DOC_STORE_DOCUMENT_REFS
    with pytest.raises(DocumentManifestJobServiceException) as e:
        manifest_service.filter_documents_by_reference(
            selected_document_references=["invalid_reference"],
        )

    assert e.value == DocumentManifestJobServiceException(
        400, LambdaError.ManifestFilterDocumentReferences
    )


def test_handle_duplicate_document_filenames_no_duplicates(manifest_service):
    manifest_service.documents = TEST_LLOYD_GEORGE_DOCUMENT_REFS
    manifest_service.documents[0].file_name = "test.pdf"
    manifest_service.documents[1].file_name = "test2.pdf"
    manifest_service.documents[2].file_name = "test3.pdf"

    manifest_service.handle_duplicate_document_filenames()

    assert manifest_service.documents[0].file_name == "test.pdf"
    assert manifest_service.documents[1].file_name == "test2.pdf"
    assert manifest_service.documents[2].file_name == "test3.pdf"


def test_handle_duplicate_document_filenames_duplicates(manifest_service):
    manifest_service.documents = TEST_LLOYD_GEORGE_DOCUMENT_REFS
    manifest_service.documents[0].file_name = "test.pdf"
    manifest_service.documents[1].file_name = "test.pdf"
    manifest_service.documents[2].file_name = "test.pdf"

    manifest_service.handle_duplicate_document_filenames()

    assert manifest_service.documents[0].file_name == "test.pdf"
    assert manifest_service.documents[1].file_name == "test(2).pdf"
    assert manifest_service.documents[2].file_name == "test(3).pdf"


@freeze_time("2024-01-01T12:00:00Z")
def test_write_zip_trace_valid(manifest_service, mock_dynamo_service, mock_uuid):
    expected = TEST_UUID

    actual = manifest_service.write_zip_trace(TEST_FILES_TO_DOWNLOAD, TEST_NHS_NUMBER)

    mock_dynamo_service.create_item.assert_called_with(
        MOCK_ZIP_TRACE_TABLE,
        TEST_ZIP_TRACE_DATA,
    )

    assert expected == actual


def test_query_document_manifest_job_status_pending(
    manifest_service, mock_query_zip_trace, mock_uuid
):

    test_zip_trace = DocumentManifestZipTrace.model_validate(TEST_ZIP_TRACE_DATA)
    mock_query_zip_trace.return_value = test_zip_trace

    expected = DocumentManifestJob(job_status=TraceStatus.PENDING, url="")

    actual = manifest_service.query_document_manifest_job(TEST_UUID, TEST_NHS_NUMBER)

    assert actual == expected


def test_query_document_manifest_job_status_processing(
    manifest_service, mock_query_zip_trace, mock_uuid
):
    TEST_ZIP_TRACE_DATA["JobStatus"] = TraceStatus.PROCESSING
    test_zip_trace = DocumentManifestZipTrace.model_validate(TEST_ZIP_TRACE_DATA)
    mock_query_zip_trace.return_value = test_zip_trace

    expected = DocumentManifestJob(job_status=TraceStatus.PROCESSING, url="")

    actual = manifest_service.query_document_manifest_job(TEST_UUID, TEST_NHS_NUMBER)

    assert actual == expected


def test_query_document_manifest_job_status_completed(
    manifest_service,
    mock_query_zip_trace,
    mock_uuid,
    mock_s3_service,
    mock_create_presigned_url,
):
    TEST_ZIP_TRACE_DATA["JobStatus"] = TraceStatus.COMPLETED
    TEST_ZIP_TRACE_DATA["ZipFileLocation"] = TEST_DOCUMENT_LOCATION
    test_zip_trace = DocumentManifestZipTrace.model_validate(TEST_ZIP_TRACE_DATA)

    mock_query_zip_trace.return_value = test_zip_trace
    mock_create_presigned_url.return_value = TEST_DOCUMENT_LOCATION

    expected = DocumentManifestJob(
        job_status=TraceStatus.COMPLETED, url=TEST_DOCUMENT_LOCATION
    )

    actual = manifest_service.query_document_manifest_job(TEST_UUID, TEST_NHS_NUMBER)

    assert actual == expected


def test_query_document_manifest_job_status_failed(
    manifest_service, mock_query_zip_trace, mock_s3_service
):
    TEST_ZIP_TRACE_DATA["JobStatus"] = TraceStatus.FAILED
    test_zip_trace = DocumentManifestZipTrace.model_validate(TEST_ZIP_TRACE_DATA)

    mock_query_zip_trace.return_value = test_zip_trace

    with pytest.raises(DocumentManifestJobServiceException) as e:
        manifest_service.query_document_manifest_job(TEST_UUID, TEST_NHS_NUMBER)

    assert e.value == DocumentManifestJobServiceException(
        500, LambdaError.ManifestFailure
    )


def test_create_document_manifest_presigned_url(manifest_service, mock_s3_service):
    mock_s3_service.file_exist_on_s3.return_value = True
    mock_s3_service.create_download_presigned_url.return_value = (
        MOCK_PRESIGNED_URL_RESPONSE
    )

    expected = MOCK_PRESIGNED_URL_RESPONSE

    actual = manifest_service.create_document_manifest_presigned_url(
        TEST_DOCUMENT_LOCATION
    )

    mock_s3_service.file_exist_on_s3.assert_called_once_with(
        s3_bucket_name=MOCK_ZIP_OUTPUT_BUCKET, file_key=TEST_FILE_KEY
    )
    mock_s3_service.create_download_presigned_url.assert_called_once_with(
        s3_bucket_name=MOCK_ZIP_OUTPUT_BUCKET, file_key=TEST_FILE_KEY
    )

    assert actual == expected


def test_create_document_manifest_presigned_url_missing_manifest_raises_exception(
    manifest_service, mock_s3_service
):
    mock_s3_service.file_exist_on_s3.return_value = False

    with pytest.raises(DocumentManifestJobServiceException) as e:
        manifest_service.create_document_manifest_presigned_url(TEST_DOCUMENT_LOCATION)

    mock_s3_service.file_exist_on_s3.assert_called_once_with(
        s3_bucket_name=MOCK_ZIP_OUTPUT_BUCKET, file_key=TEST_FILE_KEY
    )
    assert e.value == DocumentManifestJobServiceException(
        404, LambdaError.ManifestMissingJob
    )


def test_query_zip_trace_returns_zip_trace_object(
    manifest_service, mock_dynamo_service, mock_filter_expression
):
    mock_dynamo_service.query_table.return_value = [TEST_ZIP_TRACE_DATA]

    expected = DocumentManifestZipTrace.model_validate(TEST_ZIP_TRACE_DATA)

    actual = manifest_service.query_zip_trace(TEST_UUID, TEST_NHS_NUMBER)

    mock_dynamo_service.query_table.assert_called_once_with(
        table_name=MOCK_ZIP_TRACE_TABLE,
        index_name="JobIdIndex",
        search_key="JobId",
        search_condition=TEST_UUID,
        requested_fields=DocumentManifestZipTrace.get_field_names_alias_list(),
        query_filter=mock_filter_expression,
    )
    assert actual == expected


def test_query_zip_trace_empty_response_raises_exception(
    manifest_service, mock_dynamo_service
):
    mock_dynamo_service.query_table.return_value = {"Items": []}

    with pytest.raises(DocumentManifestJobServiceException) as e:
        manifest_service.query_zip_trace(TEST_UUID, TEST_NHS_NUMBER)

    assert e.value == DocumentManifestJobServiceException(
        404, LambdaError.ManifestMissingJob
    )


def test_query_zip_trace_empty_response_object_raises_exception(
    manifest_service, mock_dynamo_service
):
    mock_dynamo_service.query_table.return_value = {"Items": [{}]}

    with pytest.raises(DocumentManifestJobServiceException) as e:
        manifest_service.query_zip_trace(TEST_UUID, TEST_NHS_NUMBER)

    assert e.value == DocumentManifestJobServiceException(
        404, LambdaError.ManifestMissingJob
    )
