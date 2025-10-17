import pytest
from enums.lambda_error import LambdaError
from enums.mtls import MtlsCommonNames
from utils.lambda_exceptions import InvalidDocTypeException


@pytest.mark.parametrize(
    ["common_name", "expected"],
    [
        ("ndrclient.main.int.pdm.national.nhs.uk", MtlsCommonNames.PDM),
        ("client.dev.ndr.national.nhs.uk", MtlsCommonNames.PDM),
    ],
)
def test_mtls_enum_returned(common_name, expected):
    doc_type_enum = MtlsCommonNames.from_common_name(common_name)
    assert doc_type_enum == expected


@pytest.mark.parametrize(
    "common_name",
    [
        "client.dev.ndr.lloydgeorge.national.nhs.uk",
        "pdm.pdm.pdm",
        "foo.bar",
    ],
)
def test_mtls_enum_error_raised(common_name):
    with pytest.raises(InvalidDocTypeException) as excinfo:
        MtlsCommonNames.from_common_name(common_name)
    assert excinfo.value.status_code == 400
    assert excinfo.value.error == LambdaError.DocTypeInvalid
