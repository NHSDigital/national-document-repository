import json

from models.staging_metadata import StagingSqsMetadata
from tests.unit.helpers.data.bulk_upload.test_data import (
    EXPECTED_SQS_MSG_FOR_PATIENT_123456789,
    EXPECTED_SQS_MSG_FOR_PATIENT_1234567890,
    patient_1,
    patient_2,
)


def test_serialise_staging_data_to_json():
    assert (
        patient_1.model_dump_json(by_alias=True)
        == EXPECTED_SQS_MSG_FOR_PATIENT_1234567890
    )
    assert (
        patient_2.model_dump_json(by_alias=True)
        == EXPECTED_SQS_MSG_FOR_PATIENT_123456789
    )


def test_deserialise_json_to_staging_data():
    assert (
        StagingSqsMetadata.model_validate(
            json.loads(EXPECTED_SQS_MSG_FOR_PATIENT_1234567890)
        )
        == patient_1
    )
    assert (
        StagingSqsMetadata.model_validate(
            json.loads(EXPECTED_SQS_MSG_FOR_PATIENT_123456789)
        )
        == patient_2
    )
