import pytest
from enums.lambda_error import LambdaError
from lambdas.enums.snomed_codes import SnomedCodes
from tests.unit.conftest import MOCK_PDM_BUCKET, MOCK_LG_BUCKET
from utils.s3_utils import DocTypeS3BucketRouter
from utils.lambda_exceptions import InvalidDocTypeException


@pytest.mark.parametrize(
    "doc_type, expected_bucket",
    [
        (SnomedCodes.LLOYD_GEORGE.value, MOCK_LG_BUCKET),
        (SnomedCodes.PATIENT_DATA.value, MOCK_PDM_BUCKET),
    ],
)
def test_s3_bucket_mapping(set_env, doc_type, expected_bucket):
    bucket_router = DocTypeS3BucketRouter()
    bucket = bucket_router.resolve(doc_type)
    assert bucket == expected_bucket


@pytest.mark.parametrize(
    "doc_type",
    [
        SnomedCodes.GENERAL_MEDICAL_PRACTICE.value,
    ],
)
def test_s3_bucket_mapping_fails(set_env, doc_type):
    bucket_router = DocTypeS3BucketRouter()
    with pytest.raises(InvalidDocTypeException) as excinfo:
        bucket_router.resolve(doc_type)

    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.DocTypeInvalid
