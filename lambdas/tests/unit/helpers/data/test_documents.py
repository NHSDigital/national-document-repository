from typing import Dict, List, Optional

from enums.supported_document_types import SupportedDocumentTypes
from freezegun import freeze_time
from models.document_reference import DocumentReference
from tests.unit.conftest import (
    MOCK_ARF_BUCKET,
    MOCK_LG_BUCKET,
    MOCK_LG_STAGING_STORE_BUCKET_ENV_NAME,
    TEST_NHS_NUMBER,
    TEST_UUID,
)
from tests.unit.helpers.data.dynamo.dynamo_responses import MOCK_SEARCH_RESPONSE
from enums.snomed_codes import SnomedCodes
import json


def create_test_doc_store_refs():
    return [
        DocumentReference.model_validate(result)
        for result in MOCK_SEARCH_RESPONSE["Items"]
    ]


@freeze_time("2024-01-01 12:00:00")
def create_singular_test_lloyd_george_doc_store_ref(
    override: Optional[Dict] = None,
) -> DocumentReference:
    ref = DocumentReference.model_validate(MOCK_SEARCH_RESPONSE["Items"][0])
    filename = (
        f"1of1_Lloyd_George_Record_[Joe Bloggs]_[{TEST_NHS_NUMBER}]_[30-12-2019].pdf"
    )
    ref.file_name = filename
    if override:
        ref = ref.model_copy(update=override)
    return ref


@freeze_time("2024-01-01 12:00:00")
def create_test_lloyd_george_doc_store_refs(
    override: Optional[Dict] = None,
) -> List[DocumentReference]:
    refs = create_test_doc_store_refs()

    filename_1 = (
        f"1of3_Lloyd_George_Record_[Joe Bloggs]_[{TEST_NHS_NUMBER}]_[30-12-2019].pdf"
    )
    filename_2 = (
        f"2of3_Lloyd_George_Record_[Joe Bloggs]_[{TEST_NHS_NUMBER}]_[30-12-2019].pdf"
    )
    filename_3 = (
        f"3of3_Lloyd_George_Record_[Joe Bloggs]_[{TEST_NHS_NUMBER}]_[30-12-2019].pdf"
    )

    refs[0].file_name = filename_1
    refs[0].s3_file_key = f"{TEST_NHS_NUMBER}/test-key-1"
    refs[0].file_location = f"s3://{MOCK_LG_BUCKET}/{TEST_NHS_NUMBER}/test-key-1"
    refs[0].s3_bucket_name = MOCK_LG_BUCKET
    refs[1].file_name = filename_2
    refs[1].s3_file_key = f"{TEST_NHS_NUMBER}/test-key-2"
    refs[1].file_location = f"s3://{MOCK_LG_BUCKET}/{TEST_NHS_NUMBER}/test-key-2"
    refs[1].s3_bucket_name = MOCK_LG_BUCKET
    refs[2].file_name = filename_3
    refs[2].s3_file_key = f"{TEST_NHS_NUMBER}/test-key-3"
    refs[2].file_location = f"s3://{MOCK_LG_BUCKET}/{TEST_NHS_NUMBER}/test-key-3"
    refs[2].s3_bucket_name = MOCK_LG_BUCKET

    if override:
        refs = [doc_ref.model_copy(update=override) for doc_ref in refs]
    return refs


def create_test_arf_doc_store_refs(
    override: Optional[Dict] = None,
) -> List[DocumentReference]:
    refs = create_test_doc_store_refs()

    for index in range(3):
        file_name = f"test{index + 1 }.txt"
        file_location = f"s3://{MOCK_ARF_BUCKET}/test-key-{index + 1}23"
        refs[index].file_name = file_name
        refs[index].file_location = file_location

    if override:
        refs = [doc_ref.model_copy(update=override) for doc_ref in refs]
    return refs


def create_test_doc_refs(
    override: Optional[Dict] = None, file_names: Optional[List[str]] = None
) -> List[DocumentReference]:
    if not file_names:
        file_names = [
            f"{i}of3_Lloyd_George_Record_[Joe Bloggs]_[9000000009]_[30-12-2019].pdf"
            for i in range(1, 4)
        ]

    override = override or {}
    arguments = {
        "nhs_number": TEST_NHS_NUMBER,
        "s3_bucket_name": MOCK_LG_STAGING_STORE_BUCKET_ENV_NAME,
        "sub_folder": "upload",
        "id": TEST_UUID,
        "content_type": "application/pdf",
        "doc_type": SupportedDocumentTypes.LG.value,
        "uploading": True,
        **override,
    }

    list_of_doc_ref = [
        DocumentReference(file_name=file_name, **arguments) for file_name in file_names
    ]

    return list_of_doc_ref


def create_test_doc_refs_as_dict(
    override: Optional[Dict] = None, file_names: Optional[List[str]] = None
) -> List[Dict]:
    test_doc_refs = create_test_doc_refs(override, file_names)
    return [
        doc_ref.model_dump(by_alias=True, exclude_none=True)
        for doc_ref in test_doc_refs
    ]

def create_valid_fhir_doc_json(nhs_number: str = "9000000009"):
    return json.dumps(
        {
            "resourceType": "DocumentReference",
            "docStatus": "final",
            "status": "current",
            "subject": {
                "identifier": {
                    "system": "https://fhir.nhs.uk/Id/nhs-number",
                    "value": nhs_number,
                }
            },
            "type": {
                "coding": [
                    {
                        "system": "https://snomed.info/sct",
                        "code": SnomedCodes.LLOYD_GEORGE.value.code,
                        "display": SnomedCodes.LLOYD_GEORGE.value.display_name,
                    }
                ]
            },
            "custodian": {
                "identifier": {
                    "system": "https://fhir.nhs.uk/Id/ods-organization-code",
                    "value": "A12345",
                }
            },
            "author": [
                {
                    "identifier": {
                        "system": "https://fhir.nhs.uk/Id/ods-organization-code",
                        "value": "A12345",
                    }
                }
            ],
            "content": [
                {
                    "attachment": {
                        "contentType": "application/pdf",
                        "language": "en-GB",
                        "title": "test-file.pdf",
                        "creation": "2023-01-01T12:00:00Z",
                    }
                }
            ],
            "meta": {
                "versionId": "1"
            }
        }
    )
