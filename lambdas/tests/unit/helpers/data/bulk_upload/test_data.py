import os

from enums.snomed_codes import SnomedCodes
from enums.virus_scan_result import VirusScanResult
from freezegun import freeze_time
from models.document_reference import DocumentReference
from models.sqs.nrl_sqs_message import NrlSqsMessage
from models.sqs.pdf_stitching_sqs_message import PdfStitchingSqsMessage
from models.staging_metadata import MetadataFile, StagingMetadata
from tests.unit.conftest import MOCK_LG_BUCKET, TEST_CURRENT_GP_ODS, TEST_UUID

from lambdas.enums.nrl_sqs_upload import NrlActionTypes

sample_metadata_model = MetadataFile(
    FILEPATH="/1234567890/1of2_Lloyd_George_Record_[Joe Bloggs]_[1234567890]_[25-12-2019].pdf",
    stored_file_name="/1234567890/1of2_Lloyd_George_Record_[Joe Bloggs]_[1234567890]_[25-12-2019].pdf",
    page_count="",
    gp_practice_code="Y12345",
    section="LG",
    sub_section="",
    scan_date="03/09/2022",
    scan_id="NEC",
    user_id="NEC",
    upload="04/10/2023",
)
patient_1_file_1 = sample_metadata_model.model_copy()
patient_1_file_2 = sample_metadata_model.model_copy(
    update={
        "file_path": "/1234567890/2of2_Lloyd_George_Record_[Joe Bloggs]_[1234567890]_[25-12-2019].pdf",
        "stored_file_name":"/1234567890/2of2_Lloyd_George_Record_[Joe Bloggs]_[1234567890]_[25-12-2019].pdf",
    }
)
patient_1 = StagingMetadata(
    nhs_number="1234567890",
    files=[patient_1_file_1, patient_1_file_2],
    retries=0,
)

patient_2_file_1 = sample_metadata_model.model_copy(
    update={
        "file_path": "1of1_Lloyd_George_Record_[Joe Bloggs_invalid]_[123456789]_[25-12-2019].txt",
        "stored_file_name":"1of1_Lloyd_George_Record_[Joe Bloggs_invalid]_[123456789]_[25-12-2019].txt",
        "scan_date": "04/09/2022",
    }
)
patient_2 = StagingMetadata(nhs_number="123456789", files=[patient_2_file_1], retries=0)
MOCK_METADATA = [patient_1, patient_2]


patient_1_file_1_with_temp_nhs_number = patient_1_file_1.model_copy(
    update={"nhs_number": "1234567890"}
)
patient_1_file_2_with_temp_nhs_number = patient_1_file_2.model_copy(
    update={"nhs_number": "1234567890"}
)

patient_1_file_1_with_temp_nhs_number_different_ods_code = patient_1_file_1.model_copy(
    update={
        "nhs_number": "1234567890",
        "gp_practice_code": "Y6789",
    }
)
patient_1_file_2_with_temp_nhs_number_different_ods_code = patient_1_file_2.model_copy(
    update={
        "nhs_number": "1234567890",
        "gp_practice_code": "Y6789",
    }
)
patient_2_file_1_with_short_nhs_number = patient_2_file_1.model_copy(
    update={"nhs_number": "123456789"}
)

patient_2_file_1_with_short_nhs_number_different_ods_code = patient_2_file_1.model_copy(
    update={
        "nhs_number": "123456789",
        "gp_practice_code": "Y6789",
    }
)


patient_3_with_missing_nhs_number_metadata_file = sample_metadata_model.model_copy(
    update={
        "nhs_number": "",
        "file_path": "1of1_Lloyd_George_Record_[Jane Smith]_[1234567892]_[25-12-2019].txt",
        "stored_file_name":"1of1_Lloyd_George_Record_[Jane Smith]_[1234567892]_[25-12-2019].txt",
        "scan_date": "04/09/2022",
    }
)

patient_3_with_missing_nhs_number_metadata_file_different_ods_code = sample_metadata_model.model_copy(
    update={
        "nhs_number": "",
        "file_path": "1of1_Lloyd_George_Record_[Jane Smith]_[1234567892]_[25-12-2019].txt",
        "stored_file_name": "1of1_Lloyd_George_Record_[Jane Smith]_[1234567892]_[25-12-2019].txt",
        "scan_date": "04/09/2022",
        "gp_practice_code": "Y6789",
    }
)

patient_1_with_temp_nhs_number = StagingMetadata(
    nhs_number="1234567890",
    files=[
        patient_1_file_1_with_temp_nhs_number,
        patient_1_file_2_with_temp_nhs_number,
    ],
)

patient_1_with_temp_nhs_number_different_ods_code = StagingMetadata(
    nhs_number="1234567890",
    files=[
        patient_1_file_1_with_temp_nhs_number_different_ods_code,
        patient_1_file_2_with_temp_nhs_number_different_ods_code,
    ],
)

patient_2_with_short_nhs_number = StagingMetadata(
    nhs_number="123456789",
    files=[patient_2_file_1_with_short_nhs_number],
)

patient_2_with_short_nhs_number_different_ods_code = StagingMetadata(
    nhs_number="123456789",
    files=[patient_2_file_1_with_short_nhs_number_different_ods_code],
)

patient_3_with_missing_nhs_number = StagingMetadata(
    nhs_number="0000000000",
    files=[patient_3_with_missing_nhs_number_metadata_file],
)

patient_3_with_missing_nhs_number_different_ods_code = StagingMetadata(
    nhs_number="0000000000",
    files=[patient_3_with_missing_nhs_number_metadata_file_different_ods_code],
)

EXPECTED_PARSED_METADATA = [
    patient_1_with_temp_nhs_number,
    patient_2_with_short_nhs_number,
    patient_3_with_missing_nhs_number,
]

EXPECTED_PARSED_METADATA_2 = [
    patient_1_with_temp_nhs_number,
    patient_1_with_temp_nhs_number_different_ods_code,
    patient_2_with_short_nhs_number,
    patient_2_with_short_nhs_number_different_ods_code,
    patient_3_with_missing_nhs_number,
    patient_3_with_missing_nhs_number_different_ods_code,
]


def readfile(filename: str) -> str:
    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, "r") as file:
        file_content = file.read()
    return file_content


EXPECTED_SQS_MSG_FOR_PATIENT_1234567890 = readfile(
    "expect_sqs_msg_for_patient_1234567890.json"
)
EXPECTED_SQS_MSG_FOR_PATIENT_123456789 = readfile(
    "expect_sqs_msg_for_patient_123456789.json"
)
EXPECTED_SQS_MSG_FOR_PATIENT_0000000000 = readfile(
    "expect_sqs_msg_for_patient_0000000000.json"
)


def make_valid_lg_file_names(
    total_number: int, nhs_number: str = "9000000009", patient_name: str = "Jane Smith"
):
    return [
        f"{i}of{total_number}_Lloyd_George_Record_[{patient_name}]_[{nhs_number}]_[22-10-2010].pdf"
        for i in range(1, total_number + 1)
    ]


def make_s3_file_paths(file_names: list[str], nhs_number: str = "9000000009"):
    return [f"{nhs_number}/{file_name}" for file_name in file_names]


def build_test_staging_metadata_from_patient_name(
    patient_name: str, nhs_number: str = "9000000009"
) -> StagingMetadata:
    file_names = make_valid_lg_file_names(
        total_number=3, nhs_number=nhs_number, patient_name=patient_name
    )
    return build_test_staging_metadata(file_names=file_names, nhs_number=nhs_number)


def build_test_staging_metadata(file_names: list[str], nhs_number: str = "9000000009"):
    files = []
    for file_name in file_names:
        source_file_path = f"/{nhs_number}/{file_name}"
        files.append(
            sample_metadata_model.model_copy(update={"file_path": source_file_path})
        )
    return StagingMetadata(files=files, nhs_number=nhs_number)


def build_test_sqs_message(staging_metadata: StagingMetadata):
    return {
        "body": staging_metadata.model_dump_json(by_alias=True),
        "eventSource": "aws:sqs",
        "messageAttributes": {
            "NhsNumber": {"stringValue": staging_metadata.nhs_number}
        },
    }


def build_test_sqs_message_from_nhs_number(nhs_number: str) -> dict:
    file_names = make_valid_lg_file_names(total_number=3, nhs_number=nhs_number)
    staging_metadata = build_test_staging_metadata(
        file_names=file_names, nhs_number=nhs_number
    )
    return build_test_sqs_message(staging_metadata)


def build_test_nrl_sqs_fifo_message(nhs_number: str, action: str) -> NrlSqsMessage:
    message_body = {
        "nhs_number": nhs_number,
        "action": action,
    }
    nrl_sqs_message = NrlSqsMessage(**message_body)
    return nrl_sqs_message


def build_test_pdf_stitching_sqs_message(
    nhs_number: str, snomed_code_doc_type
) -> PdfStitchingSqsMessage:
    message_body = {
        "nhs_number": nhs_number,
        "snomed_code_doc_type": snomed_code_doc_type,
    }
    pdf_stitching_sqs_message = PdfStitchingSqsMessage(**message_body)
    return pdf_stitching_sqs_message


@freeze_time("2024-01-01 12:00:00")
def build_test_document_reference(file_name: str, nhs_number: str = "9000000009"):
    doc_ref = DocumentReference(
        nhs_number=nhs_number,
        content_type="application/pdf",
        file_name=file_name,
        id=TEST_UUID,
        s3_bucket_name=MOCK_LG_BUCKET,
        current_gp_ods=TEST_CURRENT_GP_ODS,
        author=TEST_CURRENT_GP_ODS,
        custodian=TEST_CURRENT_GP_ODS,
        doc_status="preliminary",
        document_scan_creation="2022-09-03",
    )
    doc_ref.virus_scanner_result = VirusScanResult.CLEAN
    return doc_ref


TEST_NHS_NUMBER_FOR_BULK_UPLOAD = "9000000009"
TEST_STAGING_METADATA = build_test_staging_metadata(make_valid_lg_file_names(3))
TEST_SQS_MESSAGE = build_test_sqs_message(TEST_STAGING_METADATA)
TEST_STAGING_METADATA_SINGLE_FILE = build_test_staging_metadata(
    make_valid_lg_file_names(1)
)
TEST_SQS_MESSAGE_SINGLE_FILE = build_test_sqs_message(TEST_STAGING_METADATA_SINGLE_FILE)
TEST_FILE_METADATA = TEST_STAGING_METADATA.files[0]
TEST_GROUP_ID = "123"
TEST_NRL_SQS_MESSAGE = build_test_nrl_sqs_fifo_message(
    TEST_NHS_NUMBER_FOR_BULK_UPLOAD, NrlActionTypes.CREATE
)
TEST_SNOMED_CODE_FOR_PDF_STITCHING = SnomedCodes.LLOYD_GEORGE.value
TEST_PDF_STITCHING_SQS_MESSAGE = build_test_pdf_stitching_sqs_message(
    TEST_NHS_NUMBER_FOR_BULK_UPLOAD, TEST_SNOMED_CODE_FOR_PDF_STITCHING
)
TEST_STAGING_METADATA_WITH_INVALID_FILENAME = build_test_staging_metadata(
    [*make_valid_lg_file_names(2), "invalid_file_name.txt"]
)

TEST_DOCUMENT_REFERENCE = build_test_document_reference(make_valid_lg_file_names(3)[0])
TEST_DOCUMENT_REFERENCE_LIST = [
    build_test_document_reference(file_name)
    for file_name in make_valid_lg_file_names(3)
]

TEST_SQS_MESSAGE_WITH_INVALID_FILENAME = build_test_sqs_message(
    TEST_STAGING_METADATA_WITH_INVALID_FILENAME
)
TEST_STAGING_METADATA_WITH_INVALID_FILENAME.model_dump_json(by_alias=True)

TEST_EVENT_WITH_ONE_SQS_MESSAGE = {"Records": [TEST_SQS_MESSAGE]}

TEST_SQS_MESSAGES_AS_LIST = [
    TEST_SQS_MESSAGE,
    TEST_SQS_MESSAGE_WITH_INVALID_FILENAME,
    TEST_SQS_MESSAGE,
]

TEST_EVENT_WITH_NO_SQS_MESSAGES = {"Records": []}

TEST_EVENT_WITH_SQS_MESSAGES = {"Records": TEST_SQS_MESSAGES_AS_LIST}

TEST_SQS_10_MESSAGES_AS_LIST = [
    build_test_sqs_message_from_nhs_number(str(nhs_number))
    for nhs_number in range(9_000_000_000, 9_000_000_010)
]

TEST_EVENT_WITH_10_SQS_MESSAGES = {"Records": TEST_SQS_10_MESSAGES_AS_LIST}
