from enums.metadata_field_names import DocumentReferenceMetadataFields


def test_can_get_one_field_name():
    subject = DocumentReferenceMetadataFields["NHS_NUMBER"]
    assert subject.value == "NhsNumber"


def test_returns_all_as_list():
    subject = DocumentReferenceMetadataFields.list()
    assert len(subject) == 16
    assert DocumentReferenceMetadataFields.ID.value in subject
    assert DocumentReferenceMetadataFields.CONTENT_TYPE.value in subject
    assert DocumentReferenceMetadataFields.CREATED.value in subject
    assert DocumentReferenceMetadataFields.DELETED.value in subject
    assert DocumentReferenceMetadataFields.FILE_NAME.value in subject
    assert DocumentReferenceMetadataFields.FILE_LOCATION.value in subject
    assert DocumentReferenceMetadataFields.NHS_NUMBER.value in subject
    assert DocumentReferenceMetadataFields.VIRUS_SCANNER_RESULT.value in subject
    assert DocumentReferenceMetadataFields.CURRENT_GP_ODS.value in subject
    assert DocumentReferenceMetadataFields.UPLOADED.value in subject
    assert DocumentReferenceMetadataFields.UPLOADING.value in subject
    assert DocumentReferenceMetadataFields.LAST_UPDATED.value in subject
    assert DocumentReferenceMetadataFields.DOC_STATUS.value in subject
    assert DocumentReferenceMetadataFields.DOCUMENT_SCAN_CREATION.value in subject
    assert DocumentReferenceMetadataFields.CUSTODIAN.value in subject
    assert DocumentReferenceMetadataFields.FILE_SIZE.value in subject
