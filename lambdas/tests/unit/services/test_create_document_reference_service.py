import pytest
from botocore.exceptions import ClientError
from models.nhs_document_reference import NHSDocumentReference, UploadRequestDocument
from services.create_document_reference_service import CreateDocumentReferenceService
from tests.unit.helpers.data.create_document_reference import (
    ARF_FILE_LIST,
    LG_FILE_LIST,
)
from utils.lambda_exceptions import CreateDocumentRefException
from utils.lloyd_george_validator import LGInvalidFilesException

from lambdas.enums.supported_document_types import SupportedDocumentTypes
from lambdas.tests.unit.conftest import TEST_NHS_NUMBER

NA_STRING = "Not Test Important"


@pytest.fixture
def mock_create_doc_ref_service(mocker, set_env):
    create_doc_ref_service = CreateDocumentReferenceService()
    mocker.patch.object(create_doc_ref_service, "s3_service")
    mocker.patch.object(create_doc_ref_service, "dynamo_service")
    yield create_doc_ref_service


@pytest.fixture
def mock_s3(mocker, mock_create_doc_ref_service):
    mocker.patch.object(
        mock_create_doc_ref_service.s3_service, "create_upload_presigned_url"
    )
    yield mock_create_doc_ref_service.s3_service


@pytest.fixture()
def mock_prepare_doc_object(mock_create_doc_ref_service, mocker):
    yield mocker.patch.object(mock_create_doc_ref_service, "prepare_doc_object")


@pytest.fixture()
def mock_prepare_pre_signed_url(mock_create_doc_ref_service, mocker):
    yield mocker.patch.object(mock_create_doc_ref_service, "prepare_pre_signed_url")


@pytest.fixture()
def mock_create_reference_in_dynamodb(mock_create_doc_ref_service, mocker):
    yield mocker.patch.object(
        mock_create_doc_ref_service, "create_reference_in_dynamodb"
    )


@pytest.fixture()
def mock_validate_lg(mocker):
    yield mocker.patch("services.create_document_reference_service.validate_lg_files")


def test_create_document_reference_request_empty_list(
    mock_create_doc_ref_service,
    mock_prepare_doc_object,
    mock_prepare_pre_signed_url,
    mock_create_reference_in_dynamodb,
):
    mock_create_doc_ref_service.create_document_reference_request(TEST_NHS_NUMBER, [])

    mock_prepare_doc_object.assert_not_called()
    mock_prepare_pre_signed_url.assert_not_called()
    mock_create_reference_in_dynamodb.assert_not_called()


def test_create_document_reference_request_with_arf_list_happy_path(
    mock_create_doc_ref_service,
    mocker,
    mock_prepare_doc_object,
    mock_prepare_pre_signed_url,
    mock_create_reference_in_dynamodb,
    mock_validate_lg,
):
    document_references = []
    side_effects = []

    for (
        index,
        file,
    ) in enumerate(ARF_FILE_LIST):
        document_references.append(
            NHSDocumentReference(
                nhs_number=TEST_NHS_NUMBER,
                s3_bucket_name=NA_STRING,
                reference_id=NA_STRING,
                content_type=NA_STRING,
                file_name=file["fileName"],
                doc_type=SupportedDocumentTypes.ARF.value,
            )
        )
        side_effects.append(
            document_references[index],
        )

    mock_prepare_doc_object.side_effect = side_effects

    mock_create_doc_ref_service.create_document_reference_request(
        TEST_NHS_NUMBER, ARF_FILE_LIST
    )

    mock_prepare_doc_object.assert_has_calls(
        [mocker.call(TEST_NHS_NUMBER, file) for file in ARF_FILE_LIST], any_order=True
    )

    mock_prepare_pre_signed_url.assert_has_calls(
        [mocker.call(document_reference) for document_reference in document_references],
        any_order=True,
    )

    mock_create_reference_in_dynamodb.assert_called_once()
    mock_validate_lg.assert_not_called()


def test_create_document_reference_request_with_lg_list_happy_path(
    mock_create_doc_ref_service,
    mocker,
    mock_prepare_doc_object,
    mock_prepare_pre_signed_url,
    mock_create_reference_in_dynamodb,
    mock_validate_lg,
):
    document_references = []
    side_effects = []

    for (
        index,
        file,
    ) in enumerate(LG_FILE_LIST):
        document_references.append(
            NHSDocumentReference(
                nhs_number=TEST_NHS_NUMBER,
                s3_bucket_name=NA_STRING,
                reference_id=NA_STRING,
                content_type=NA_STRING,
                file_name=file["fileName"],
                doc_type=SupportedDocumentTypes.LG.value,
            )
        )
        side_effects.append(document_references[index])

    mock_prepare_doc_object.side_effect = side_effects

    mock_create_doc_ref_service.create_document_reference_request(
        TEST_NHS_NUMBER, LG_FILE_LIST
    )

    mock_prepare_doc_object.assert_has_calls(
        [mocker.call(TEST_NHS_NUMBER, file) for file in LG_FILE_LIST], any_order=True
    )
    mock_prepare_pre_signed_url.assert_has_calls(
        [mocker.call(document_reference) for document_reference in document_references],
        any_order=True,
    )

    mock_create_reference_in_dynamodb.assert_called_once()
    mock_validate_lg.assert_called_with(document_references, TEST_NHS_NUMBER)


def test_create_document_reference_request_with_both_list(
    mock_create_doc_ref_service,
    mocker,
    mock_prepare_doc_object,
    mock_prepare_pre_signed_url,
    mock_create_reference_in_dynamodb,
    mock_validate_lg,
):
    document_references = []
    lg_dictionaries = []
    arf_dictionaries = []
    side_effects = []
    files_list = ARF_FILE_LIST + LG_FILE_LIST

    for (
        index,
        file,
    ) in enumerate(files_list):
        is_lg_file = index >= len(ARF_FILE_LIST)

        doc_type = SupportedDocumentTypes.ARF.value
        if is_lg_file:
            doc_type = SupportedDocumentTypes.LG.value

        document_reference = NHSDocumentReference(
            nhs_number=TEST_NHS_NUMBER,
            s3_bucket_name=NA_STRING,
            reference_id=NA_STRING,
            content_type=NA_STRING,
            file_name=file["fileName"],
            doc_type=doc_type,
        )
        document_references.append(document_reference)

        if is_lg_file:
            lg_dictionaries.append(document_reference.to_dict())
        else:
            arf_dictionaries.append(document_reference.to_dict())

        side_effects.append(document_reference)

    mock_prepare_doc_object.side_effect = side_effects
    mock_create_doc_ref_service.create_document_reference_request(
        TEST_NHS_NUMBER, files_list
    )

    mock_prepare_doc_object.assert_has_calls(
        [mocker.call(TEST_NHS_NUMBER, file) for file in files_list], any_order=True
    )
    mock_prepare_pre_signed_url.assert_has_calls(
        [mocker.call(document_reference) for document_reference in document_references],
        any_order=True,
    )
    mock_create_reference_in_dynamodb.assert_has_calls(
        [
            mocker.call(mock_create_doc_ref_service.lg_dynamo_table, lg_dictionaries),
            mocker.call(mock_create_doc_ref_service.arf_dynamo_table, arf_dictionaries),
        ]
    )
    mock_validate_lg.assert_called()


def test_create_document_reference_request_raise_error_when_invalid_lg(
    mock_create_doc_ref_service,
    mocker,
    mock_prepare_doc_object,
    mock_prepare_pre_signed_url,
    mock_create_reference_in_dynamodb,
    mock_validate_lg,
):
    document_references = []
    side_effects = []

    for (
        index,
        file,
    ) in enumerate(LG_FILE_LIST):
        document_references.append(
            NHSDocumentReference(
                nhs_number=TEST_NHS_NUMBER,
                s3_bucket_name=NA_STRING,
                reference_id=NA_STRING,
                content_type=NA_STRING,
                file_name=file["fileName"],
                doc_type=SupportedDocumentTypes.LG.value,
            )
        )
        side_effects.append(document_references[index])

    mock_prepare_doc_object.side_effect = side_effects
    mock_validate_lg.side_effect = LGInvalidFilesException("test")

    with pytest.raises(CreateDocumentRefException):
        mock_create_doc_ref_service.create_document_reference_request(
            TEST_NHS_NUMBER, LG_FILE_LIST
        )

    mock_prepare_doc_object.assert_has_calls(
        [mocker.call(TEST_NHS_NUMBER, file) for file in LG_FILE_LIST], any_order=True
    )
    mock_prepare_pre_signed_url.assert_has_calls(
        [mocker.call(document_reference) for document_reference in document_references],
        any_order=True,
    )

    mock_create_reference_in_dynamodb.assert_not_called()
    mock_validate_lg.assert_called_with(document_references, TEST_NHS_NUMBER)


def test_create_document_reference_invalid_nhs_number(mocker):
    nhs_number = "100000009"
    create_doc_ref_service = CreateDocumentReferenceService()
    mock_prepare_doc_object = mocker.patch.object(
        create_doc_ref_service, "prepare_doc_object"
    )
    mock_prepare_pre_signed_url = mocker.patch.object(
        create_doc_ref_service, "prepare_pre_signed_url"
    )
    mock_create_reference_in_dynamodb = mocker.patch.object(
        create_doc_ref_service, "create_reference_in_dynamodb"
    )

    with pytest.raises(CreateDocumentRefException):
        create_doc_ref_service.create_document_reference_request(
            nhs_number, ARF_FILE_LIST
        )

    mock_prepare_doc_object.assert_not_called()
    mock_prepare_pre_signed_url.assert_not_called()
    mock_create_reference_in_dynamodb.assert_not_called()


def test_prepare_doc_object_raise_error_when_no_type(
    mocker, mock_create_doc_ref_service
):
    document = {}
    mocker.patch.object(UploadRequestDocument, "model_validate")

    with pytest.raises(CreateDocumentRefException):
        mock_create_doc_ref_service.prepare_doc_object(TEST_NHS_NUMBER, document)


def test_prepare_doc_object_raise_error_when_invalid_type(
    mocker, mock_create_doc_ref_service
):
    document = {}
    mock_model = mocker.patch.object(UploadRequestDocument, "model_validate")
    mock_model.return_value.docType = "Invalid"

    with pytest.raises(CreateDocumentRefException):
        mock_create_doc_ref_service.prepare_doc_object(TEST_NHS_NUMBER, document)


def test_prepare_doc_object_arf_happy_path(mocker, mock_create_doc_ref_service):
    document = ARF_FILE_LIST[0]
    nhs_number = 1234567890
    reference_id = 12341234

    mocker.patch(
        "services.create_document_reference_service.create_reference_id",
        return_value=reference_id,
    )
    mocked_doc = mocker.MagicMock()
    nhs_doc_class = mocker.patch(
        "services.create_document_reference_service.NHSDocumentReference",
        return_value=mocked_doc,
    )
    nhs_doc_class.to_dict.return_value = {}

    actual_document_reference = mock_create_doc_ref_service.prepare_doc_object(
        nhs_number, document
    )

    assert actual_document_reference == mocked_doc
    nhs_doc_class.assert_called_with(
        nhs_number=nhs_number,
        s3_bucket_name=mock_create_doc_ref_service.staging_bucket_name,
        sub_folder=mock_create_doc_ref_service.upload_sub_folder,
        reference_id=reference_id,
        content_type="text/plain",
        file_name="test1.txt",
        doc_type=SupportedDocumentTypes.ARF.value,
    )


def test_prepare_doc_object_lg_happy_path(mocker, mock_create_doc_ref_service):
    document = LG_FILE_LIST[0]
    nhs_number = 1234567890
    reference_id = 12341234

    mocker.patch(
        "services.create_document_reference_service.create_reference_id",
        return_value=reference_id,
    )
    mocked_doc = mocker.MagicMock()
    nhs_doc_class = mocker.patch(
        "services.create_document_reference_service.NHSDocumentReference",
        return_value=mocked_doc,
    )
    nhs_doc_class.to_dict.return_value = {}

    actual_document_reference = mock_create_doc_ref_service.prepare_doc_object(
        nhs_number, document
    )

    assert actual_document_reference == mocked_doc
    nhs_doc_class.assert_called_with(
        nhs_number=nhs_number,
        s3_bucket_name=mock_create_doc_ref_service.staging_bucket_name,
        sub_folder=mock_create_doc_ref_service.upload_sub_folder,
        reference_id=reference_id,
        content_type="application/pdf",
        file_name="1of3_Lloyd_George_Record_[Joe Bloggs]_[9000000009]_[25-12-2019].pdf",
        doc_type=SupportedDocumentTypes.LG.value,
    )


def test_prepare_pre_signed_url(mock_create_doc_ref_service, mocker, mock_s3):
    mock_s3.create_upload_presigned_url.return_value = "test_url"
    mock_document = mocker.MagicMock()
    mock_document.file_name = "test_name"
    expected = "test_url"

    response = mock_create_doc_ref_service.prepare_pre_signed_url(mock_document)

    mock_s3.create_upload_presigned_url.assert_called_once()
    assert expected == response


def test_prepare_pre_signed_url_raise_error(
    mock_create_doc_ref_service, mocker, mock_s3
):
    mock_s3.create_upload_presigned_url.side_effect = ClientError(
        {"Error": {"Code": "500", "Message": "mocked error"}}, "test"
    )
    mock_document = mocker.MagicMock()
    mock_document.file_name = "test_name"
    with pytest.raises(CreateDocumentRefException):
        mock_create_doc_ref_service.prepare_pre_signed_url(mock_document)

    mock_s3.create_upload_presigned_url.assert_called_once()


def test_create_reference_in_dynamodb_raise_error(mock_create_doc_ref_service):
    mock_create_doc_ref_service.dynamo_service.batch_writing.side_effect = ClientError(
        {"Error": {"Code": "500", "Message": "mocked error"}}, "test"
    )
    mock_create_doc_ref_service.arf_documents_dict_format = {"test": "test"}
    with pytest.raises(CreateDocumentRefException):
        mock_create_doc_ref_service.create_reference_in_dynamodb("test", ["test"])

    mock_create_doc_ref_service.dynamo_service.batch_writing.assert_called_once()


def test_create_reference_in_dynamodb_both_tables(mock_create_doc_ref_service, mocker):
    mock_create_doc_ref_service.create_reference_in_dynamodb(
        mock_create_doc_ref_service.arf_dynamo_table, [{"test_arf": "test"}]
    )

    mock_create_doc_ref_service.dynamo_service.batch_writing.assert_has_calls(
        [
            mocker.call(
                mock_create_doc_ref_service.arf_dynamo_table, [{"test_arf": "test"}]
            )
        ]
    )
    assert mock_create_doc_ref_service.dynamo_service.batch_writing.call_count == 1
