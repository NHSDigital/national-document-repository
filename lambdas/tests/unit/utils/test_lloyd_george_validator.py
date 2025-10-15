import pytest
from botocore.exceptions import ClientError
from requests import Response

from enums.supported_document_types import SupportedDocumentTypes
from enums.validation_score import ValidationResult, ValidationScore
from models.pds_models import Patient
from services.base.ssm_service import SSMService
from services.document_service import DocumentService
from tests.unit.conftest import TEST_NHS_NUMBER, expect_not_to_raise
from tests.unit.helpers.data.bulk_upload.test_data import (
    TEST_DOCUMENT_REFERENCE_LIST,
    TEST_NHS_NUMBER_FOR_BULK_UPLOAD,
    TEST_STAGING_METADATA_WITH_INVALID_FILENAME,
)
from tests.unit.helpers.data.pds.pds_patient_response import (
    PDS_PATIENT_WITH_MIDDLE_NAME,
)
from tests.unit.helpers.data.pds.test_cases_for_date_logic import (
    build_test_name,
    build_test_patient_with_names,
)
from tests.unit.helpers.data.pds.test_cases_for_patient_name_matching import (
    TEST_CASES_FOR_EMPTY_GIVEN_NAME,
    TEST_CASES_FOR_FAMILY_NAME_WITH_HYPHEN,
    TEST_CASES_FOR_TWO_WORDS_FAMILY_NAME,
    TEST_CASES_FOR_TWO_WORDS_FAMILY_NAME_AND_GIVEN_NAME,
    TEST_CASES_FOR_TWO_WORDS_FAMILY_NAME_STRICT,
    TEST_CASES_FOR_TWO_WORDS_GIVEN_NAME,
    load_test_cases,
)
from tests.unit.models.test_document_reference import MOCK_DOCUMENT_REFERENCE
from utils.common_query_filters import NotDeleted
from utils.exceptions import (
    PatientNotFoundException,
    PatientRecordAlreadyExistException,
    PdsTooManyRequestsException,
)
from utils.lloyd_george_validator import (
    LGInvalidFilesException,
    allowed_to_ingest_ods_code,
    calculate_validation_score_for_lenient_check,
    check_for_duplicate_files,
    check_for_file_names_agrees_with_each_other,
    check_for_number_of_files_match_expected,
    check_for_patient_already_exist_in_repo,
    check_pds_response_status,
    extract_info_from_filename,
    get_allowed_ods_codes,
    getting_patient_info_from_pds,
    parse_pds_response,
    validate_file_name,
    validate_filename_with_patient_details_lenient,
    validate_filename_with_patient_details_strict,
    validate_lg_file_names,
    validate_lg_file_type,
    validate_lg_files,
    validate_patient_date_of_birth,
    validate_patient_name_lenient,
    validate_patient_name_strict,
    validate_patient_name_using_full_name_history, validate_scan_date,
)


@pytest.fixture
def mock_get_ssm_parameter(mocker):
    return mocker.patch.object(SSMService, "get_ssm_parameter")


@pytest.fixture
def mock_pds_call(mocker):
    yield mocker.patch("services.mock_pds_service.MockPdsApiService.pds_request")


@pytest.fixture
def mock_fetch_available_document_references_by_type(mocker):
    yield mocker.patch.object(
        DocumentService, "fetch_available_document_references_by_type"
    )


def test_catching_error_when_file_type_not_pdf():
    with pytest.raises(LGInvalidFilesException):
        file_type = "image/png"
        validate_lg_file_type(file_type)


def test_valid_file_type():
    with expect_not_to_raise(LGInvalidFilesException):
        file_type = "application/pdf"
        validate_lg_file_type(file_type)


def test_invalid_file_name():
    with pytest.raises(LGInvalidFilesException):
        file_name = "bad_name"
        validate_file_name(file_name)


def test_valid_file_name():
    with expect_not_to_raise(LGInvalidFilesException):
        file_name = (
            "1of1_Lloyd_George_Record_[Joe Bloggs]_[1111111111]_[25-12-2019].pdf"
        )
        validate_file_name(file_name)


@pytest.mark.parametrize(
    "file_name",
    [
        "1of1_Lloyd_George_Record_[James O'Brien]_[1111111111]_[25-12-2019].pdf",
        "1of1_Lloyd_George_Record_[Joé Blöggês-Glüë]_[1111111111]_[25-12-2019].pdf",
        "1of1_Lloyd_George_Record_[Joé Blöggês-Glüë]_[1111111111]_[25-12-2019].pdf",  # same string in NFD form
    ],
    ids=[
        "Patient name with apostrophe",
        "Patient name with accented char in NFC code point",
        "Patient name with accented char in NFD code point",
    ],
)
def test_valid_file_name_special_characters(file_name):
    with expect_not_to_raise(
        LGInvalidFilesException,
        "validate_file_name should handle patient names with special characters",
    ):
        validate_file_name(file_name)


def test_valid_file_name_with_apostrophe():
    with expect_not_to_raise(
        LGInvalidFilesException,
        "validate_file_name should handle patient names with special characters and apostrophe",
    ):
        file_name = (
            "1of1_Lloyd_George_Record_[Joé Blöggê's-Glüë]_[1111111111]_[25-12-2019].pdf"
        )
        validate_file_name(file_name)


def test_files_with_duplication():
    with pytest.raises(LGInvalidFilesException):
        lg_file_list = [
            "1of1_Lloyd_George_Record_[Joe Bloggs]_[1111111111]_[25-12-2019].pdf",
            "1of1_Lloyd_George_Record_[Joe Bloggs]_[1111111111]_[25-12-2019].pdf",
        ]
        check_for_duplicate_files(lg_file_list)


def test_files_without_duplication():
    with expect_not_to_raise(LGInvalidFilesException):
        lg_file_list = [
            "1of2_Lloyd_George_Record_[Joe Bloggs]_[1111111111]_[25-12-2019].pdf",
            "2of2_Lloyd_George_Record_[Joe Bloggs]_[1111111111]_[25-12-2019].pdf",
        ]
        check_for_duplicate_files(lg_file_list)


def test_files_list_with_missing_files():
    with pytest.raises(LGInvalidFilesException) as e:
        lg_file_list = [
            "1of3_Lloyd_George_Record_[Joe Bloggs]_[1111111111]_[25-12-2019].pdf",
            "2of3_Lloyd_George_Record_[Joe Bloggs]_[1111111111]_[25-12-2019].pdf",
        ]
        check_for_number_of_files_match_expected(lg_file_list[0], len(lg_file_list))
    assert str(e.value) == "There are missing file(s) in the request"


def test_files_list_with_too_many_files():
    with pytest.raises(LGInvalidFilesException) as e:
        lg_file_list = [
            "1of3_Lloyd_George_Record_[Joe Bloggs]_[1111111111]_[25-12-2019].pdf",
            "2of3_Lloyd_George_Record_[Joe Bloggs]_[1111111111]_[25-12-2019].pdf",
            "3of3_Lloyd_George_Record_[Joe Bloggs]_[1111111111]_[25-12-2019].pdf",
            "1of3_Lloyd_George_Record_[Joe Bloggs]_[1111111111]_[25-12-2019].pdf",
        ]
        check_for_number_of_files_match_expected(lg_file_list[0], len(lg_file_list))
    assert str(e.value) == "There are more files than the total number in file name"


def test_files_list_with_invalid_name():
    with pytest.raises(LGInvalidFilesException) as e:
        lg_file_list = [
            "invalid_file_name",
            "2of4_Lloyd_George_Record_[Joe Bloggs]_[1111111111]_[25-12-2019].pdf",
            "3of4_Lloyd_George_Record_[Joe Bloggs]_[1111111111]_[25-12-2019].pdf",
            "4of4_Lloyd_George_Record_[Joe Bloggs]_[1111111111]_[25-12-2019].pdf",
        ]
        check_for_number_of_files_match_expected(lg_file_list[0], len(lg_file_list))
    assert str(e.value) == "One or more of the files do not match naming convention"


def test_file_name_with_apostrophe_as_name():
    """
    This is an edge case which currently passes.
    As part of prmdr-520 it was decided that it was acceptable to have an apostrophe accepted as a name
    This is because patient names will only ever come from PDS
    """
    with expect_not_to_raise(LGInvalidFilesException):
        file_name = "1of1_Lloyd_George_Record_[']_[1111111111]_[25-12-2019].pdf"
        validate_file_name(file_name)


def test_files_without_missing_files():
    with expect_not_to_raise(LGInvalidFilesException):
        lg_file_list = [
            "1of2_Lloyd_George_Record_[Joe Bloggs]_[1111111111]_[25-12-2019].pdf",
            "2of2_Lloyd_George_Record_[Joe Bloggs]_[1111111111]_[25-12-2019].pdf",
        ]
        check_for_number_of_files_match_expected(lg_file_list[0], len(lg_file_list))


@pytest.mark.parametrize(
    ["file_name", "patient_name"],
    [
        (
            "123of456_Lloyd_George_Record_[James O'Brien]_[1111111111]_[25-12-2019].pdf",
            "James O'Brien",
        ),
        (
            "123of456_Lloyd_George_Record_[Joé Blöggês-Glüë]_[1111111111]_[25-12-2019].pdf",
            "Joé Blöggês-Glüë",
        ),
        (
            "123of456_Lloyd_George_Record_[Joé Blöggês-Glüë]_[1111111111]_[25-12-2019].pdf",
            "Joé Blöggês-Glüë",
        ),  # same string in NFD form
    ],
    ids=[
        "Patient name with apostrophe",
        "Patient name with accented char in NFC code point",
        "Patient name with accented char in NFD code point",
    ],
)
def test_extract_info_from_filename(file_name, patient_name):
    expected = {
        "page_no": "123",
        "total_page_no": "456",
        "patient_name": patient_name,
        "nhs_number": "1111111111",
        "date_of_birth": "25-12-2019",
    }

    actual = extract_info_from_filename(file_name)

    assert actual == expected


def test_files_for_different_patients():
    lg_file_list = [
        "1of4_Lloyd_George_Record_[Joe Bloggs]_[1111111111]_[25-12-2019].pdf",
        "2of4_Lloyd_George_Record_[Joe Bloggs]_[1111111111]_[25-12-2019].pdf",
        "3of4_Lloyd_George_Record_[John Smith]_[1111111112]_[25-12-2019].pdf",
        "4of4_Lloyd_George_Record_[Joe Bloggs]_[1111111111]_[25-12-2019].pdf",
    ]
    with pytest.raises(LGInvalidFilesException) as e:
        check_for_file_names_agrees_with_each_other(lg_file_list)
    assert str(e.value) == "File names does not match with each other"


def test_validate_nhs_id_with_pds_service(mock_pds_patient):
    lg_file_list = [
        "1of2_Lloyd_George_Record_[Jane Smith]_[9000000009]_[22-10-2010].pdf",
        "2of2_Lloyd_George_Record_[Jane Smith]_[9000000009]_[22-10-2010].pdf",
    ]
    with expect_not_to_raise(LGInvalidFilesException):
        validate_filename_with_patient_details_lenient(lg_file_list, mock_pds_patient)

    with expect_not_to_raise(LGInvalidFilesException):
        validate_filename_with_patient_details_strict(lg_file_list, mock_pds_patient)


def test_mismatch_nhs_id(mocker):
    lg_file_list = [
        "1of2_Lloyd_George_Record_[Jane Smith]_[9000000005]_[22-10-2010].pdf",
        "2of2_Lloyd_George_Record_[Jane Smith]_[9000000005]_[22-10-2010].pdf",
    ]

    mocker.patch("utils.lloyd_george_validator.check_for_patient_already_exist_in_repo")
    mocker.patch(
        "utils.lloyd_george_validator.check_for_number_of_files_match_expected"
    )

    with pytest.raises(LGInvalidFilesException):
        validate_lg_file_names(lg_file_list, "9000000009")


def test_mismatch_name_with_pds_service_strict(mock_pds_patient):
    lg_file_list = [
        "1of2_Lloyd_George_Record_[Jake Plain Smith]_[9000000009]_[22-10-2010].pdf",
        "2of2_Lloyd_George_Record_[Jake Plain Smith]_[9000000009]_[22-10-2010].pdf",
    ]

    with pytest.raises(LGInvalidFilesException):
        validate_filename_with_patient_details_strict(lg_file_list, mock_pds_patient)


def test_mismatch_name_with_pds_service_lenient(mock_pds_patient):
    lg_file_list = [
        "1of2_Lloyd_George_Record_[Jake Plain Moody]_[9000000009]_[22-10-2010].pdf",
        "2of2_Lloyd_George_Record_[Jake Plain Moody]_[9000000009]_[22-10-2010].pdf",
    ]

    with pytest.raises(LGInvalidFilesException):
        validate_filename_with_patient_details_lenient(lg_file_list, mock_pds_patient)


def test_validate_name_with_correct_name_lenient(mocker, mock_pds_patient):
    lg_file_patient_name = "Jane Smith"
    mock_validate_name = mocker.patch(
        "utils.lloyd_george_validator.validate_patient_name_lenient"
    )
    expected_message = "matched on 1 family_name and 1 given name"
    mock_validate_name.return_value = ValidationResult(
        score=ValidationScore.FULL_MATCH,
        given_name_match=["Jane"],
        family_name_match="Smith",
    )
    actual_score, actual_is_name_validation_based_on_historic_name, result_message = (
        calculate_validation_score_for_lenient_check(
            lg_file_patient_name, mock_pds_patient
        )
    )

    assert expected_message == result_message
    assert mock_validate_name.call_count == 1
    assert actual_is_name_validation_based_on_historic_name is False
    assert actual_score == ValidationScore.FULL_MATCH


def test_validate_name_with_correct_name_strict(mocker, mock_pds_patient):
    lg_file_patient_name = "Jane Smith"
    mock_validate_name = mocker.patch(
        "utils.lloyd_george_validator.validate_patient_name_strict"
    )
    with expect_not_to_raise(LGInvalidFilesException):
        validate_patient_name_using_full_name_history(
            lg_file_patient_name, mock_pds_patient
        )
    assert mock_validate_name.call_count == 1


def test_validate_name_with_file_missing_middle_name(mocker):
    lg_file_patient_name = "Jane Smith"
    patient = Patient.model_validate(PDS_PATIENT_WITH_MIDDLE_NAME)
    mock_validate_name = mocker.patch(
        "utils.lloyd_george_validator.validate_patient_name_strict"
    )
    with expect_not_to_raise(LGInvalidFilesException):
        validate_patient_name_using_full_name_history(lg_file_patient_name, patient)

    assert mock_validate_name.call_count == 1


def test_validate_name_with_additional_middle_name_in_file_mismatching_pds_strict(
    mocker,
):
    lg_file_patient_name = "Jane David Smith"
    mock_validate_name = mocker.patch(
        "utils.lloyd_george_validator.validate_patient_name_strict"
    )
    patient = Patient.model_validate(PDS_PATIENT_WITH_MIDDLE_NAME)
    with expect_not_to_raise(LGInvalidFilesException):
        actual_is_name_validation_based_on_historic_name = (
            validate_patient_name_using_full_name_history(lg_file_patient_name, patient)
        )
    assert mock_validate_name.call_count == 1
    assert actual_is_name_validation_based_on_historic_name is False


def test_validate_name_with_additional_middle_name_in_file_mismatching_pds_lenient(
    mocker,
):
    lg_file_patient_name = "Jane David Smith"
    mock_validate_name = mocker.patch(
        "utils.lloyd_george_validator.validate_patient_name_lenient"
    )
    expected_message = "matched on 1 family_name and 1 given name"

    patient = Patient.model_validate(PDS_PATIENT_WITH_MIDDLE_NAME)
    mock_validate_name.return_value = ValidationResult(
        score=ValidationScore.FULL_MATCH,
        given_name_match=["Jane"],
        family_name_match="Smith",
    )
    actual_score, actual_is_name_validation_based_on_historic_name, result_message = (
        calculate_validation_score_for_lenient_check(lg_file_patient_name, patient)
    )

    assert expected_message == result_message
    assert mock_validate_name.call_count == 1
    assert actual_is_name_validation_based_on_historic_name is False
    assert actual_score == ValidationScore.FULL_MATCH


def test_validate_name_with_additional_middle_name_in_file_but_none_in_pds_strict(
    mock_pds_patient, mocker
):
    lg_file_patient_name = "Jane David Smith"
    mock_validate_name = mocker.patch(
        "utils.lloyd_george_validator.validate_patient_name_strict"
    )

    actual_is_name_validation_based_on_historic_name = (
        validate_patient_name_using_full_name_history(
            lg_file_patient_name, mock_pds_patient
        )
    )

    assert mock_validate_name.call_count == 1
    assert actual_is_name_validation_based_on_historic_name is False


def test_validate_name_with_additional_middle_name_in_file_but_none_in_pds(
    mock_pds_patient, mocker
):
    lg_file_patient_name = "Jane David Smith"
    mock_validate_name = mocker.patch(
        "utils.lloyd_george_validator.validate_patient_name_lenient"
    )

    expected_message = "matched on 1 family_name and 1 given name"

    mock_validate_name.return_value = ValidationResult(
        score=ValidationScore.FULL_MATCH,
        given_name_match=["Jane"],
        family_name_match="Smith",
    )
    actual_score, actual_is_name_validation_based_on_historic_name, result_message = (
        calculate_validation_score_for_lenient_check(
            lg_file_patient_name, mock_pds_patient
        )
    )

    assert expected_message == result_message
    assert mock_validate_name.call_count == 1
    assert actual_is_name_validation_based_on_historic_name is False
    assert actual_score == ValidationScore.FULL_MATCH


def test_validate_name_with_wrong_first_name_strict(mocker, mock_pds_patient):
    lg_file_patient_name = "John Smith"
    mock_validate_name = mocker.patch(
        "utils.lloyd_george_validator.validate_patient_name_strict"
    )
    mock_validate_name.return_value = False
    with pytest.raises(LGInvalidFilesException):
        validate_patient_name_using_full_name_history(
            lg_file_patient_name, mock_pds_patient
        )
    assert mock_validate_name.call_count == 3


def test_validate_name_with_wrong_first_name_lenient(mock_pds_patient):
    lg_file_patient_name = "John Smith"

    actual_response = validate_patient_name_lenient(
        lg_file_patient_name,
        mock_pds_patient.name[0].given,
        mock_pds_patient.name[0].family,
    )
    assert actual_response == ValidationResult(
        score=ValidationScore.PARTIAL_MATCH,
        family_name_match="smith",
    )


def test_validate_name_with_wrong_family_name_strict(mocker, mock_pds_patient):
    lg_file_patient_name = "John Johnson"
    mock_validate_name = mocker.patch(
        "utils.lloyd_george_validator.validate_patient_name_strict"
    )
    mock_validate_name.return_value = False
    with pytest.raises(LGInvalidFilesException):
        validate_patient_name_using_full_name_history(
            lg_file_patient_name, mock_pds_patient
        )
    assert mock_validate_name.call_count == 3


def test_validate_name_with_wrong_family_name_lenient(mock_pds_patient):
    lg_file_patient_name = "Jane Johnson"
    actual_response = validate_patient_name_lenient(
        lg_file_patient_name,
        mock_pds_patient.name[0].given,
        mock_pds_patient.name[0].family,
    )
    assert actual_response == ValidationResult(
        score=ValidationScore.PARTIAL_MATCH,
        given_name_match=["jane"],
    )


def test_validate_name_with_historical_name_strict(mocker, mock_pds_patient):
    lg_file_patient_name = "Jim Stevens"
    mock_validate_name = mocker.patch(
        "utils.lloyd_george_validator.validate_patient_name_strict"
    )
    mock_validate_name.side_effect = [False, True]
    with expect_not_to_raise(LGInvalidFilesException):
        actual_is_name_validation_based_on_historic_name = (
            validate_patient_name_using_full_name_history(
                lg_file_patient_name, mock_pds_patient
            )
        )

    assert mock_validate_name.call_count == 2
    assert actual_is_name_validation_based_on_historic_name is True


def test_validate_name_with_historical_name_lenient(mocker, mock_pds_patient):
    lg_file_patient_name = "Jim Stevens"
    mock_validate_name = mocker.patch(
        "utils.lloyd_george_validator.validate_patient_name_lenient"
    )
    expected_message = "matched on 1 family_name and 1 given name"

    mock_validate_name.side_effect = [
        ValidationResult(
            score=ValidationScore.NO_MATCH,
        ),
        ValidationResult(
            score=ValidationScore.FULL_MATCH,
            given_name_match=["Jim"],
            family_name_match="Stevens",
        ),
    ]
    actual_score, actual_is_validate_on_historic, result_message = (
        calculate_validation_score_for_lenient_check(
            lg_file_patient_name, mock_pds_patient
        )
    )

    assert result_message == expected_message
    assert actual_score == ValidationScore.FULL_MATCH
    assert mock_validate_name.call_count == 2
    assert actual_is_validate_on_historic is True


def test_validate_name_without_given_name_strict(mocker, mock_pds_patient):
    lg_file_patient_name = "Jane Smith"
    mock_pds_patient.name[0].given = [""]
    mock_validate_name = mocker.patch(
        "utils.lloyd_george_validator.validate_patient_name_strict"
    )

    with expect_not_to_raise(LGInvalidFilesException):
        actual_is_validate_on_historic = validate_patient_name_using_full_name_history(
            lg_file_patient_name, mock_pds_patient
        )

    assert actual_is_validate_on_historic is False
    assert mock_validate_name.call_count == 1


def test_validate_name_without_given_name_lenient(mocker, mock_pds_patient):
    lg_file_patient_name = "Jane Smith"
    mock_pds_patient.name[0].given = [""]
    expected_message = "No match found"

    mock_validate_name = mocker.patch(
        "utils.lloyd_george_validator.validate_patient_name_lenient"
    )
    actual_score, actual_is_validate_on_historic, result_message = (
        calculate_validation_score_for_lenient_check(
            lg_file_patient_name, mock_pds_patient
        )
    )

    assert result_message == expected_message
    assert actual_score == ValidationScore.NO_MATCH
    assert actual_is_validate_on_historic is False
    assert mock_validate_name.call_count == 2


@pytest.mark.parametrize(
    ["patient_details", "patient_name_in_file_name", "should_accept_name"],
    load_test_cases(TEST_CASES_FOR_TWO_WORDS_FAMILY_NAME_STRICT),
)
def test_validate_patient_name_with_two_words_family_name_strict(
    patient_details: Patient,
    patient_name_in_file_name: str,
    should_accept_name: bool,
):
    if should_accept_name:
        with expect_not_to_raise(LGInvalidFilesException):
            actual_is_validate_on_historic = (
                validate_patient_name_using_full_name_history(
                    patient_name_in_file_name, patient_details
                )
            )
            assert actual_is_validate_on_historic is False
    else:
        with pytest.raises(LGInvalidFilesException):
            validate_patient_name_using_full_name_history(
                patient_name_in_file_name, patient_details
            )


@pytest.mark.parametrize(
    ["patient_details", "patient_name_in_file_name", "should_accept_name"],
    load_test_cases(TEST_CASES_FOR_TWO_WORDS_FAMILY_NAME),
)
def test_validate_patient_name_with_two_words_family_name_lenient(
    patient_details: Patient,
    patient_name_in_file_name: str,
    should_accept_name: bool,
):

    actual_score, actual_is_validate_on_historic, result_message = (
        calculate_validation_score_for_lenient_check(
            patient_name_in_file_name, patient_details
        )
    )
    if should_accept_name:
        assert actual_is_validate_on_historic is False
        assert actual_score == ValidationScore.FULL_MATCH
    else:
        expected_message = "matched on 0 family_name and 1 given name"
        assert result_message == expected_message
        assert actual_is_validate_on_historic is False
        assert actual_score == ValidationScore.PARTIAL_MATCH


@pytest.mark.parametrize(
    ["patient_details", "patient_name_in_file_name", "should_accept_name"],
    load_test_cases(TEST_CASES_FOR_FAMILY_NAME_WITH_HYPHEN),
)
def test_validate_patient_name_with_family_name_with_hyphen_strict(
    patient_details: Patient,
    patient_name_in_file_name: str,
    should_accept_name: bool,
):
    if should_accept_name:
        with expect_not_to_raise(LGInvalidFilesException):
            actual_is_validate_on_historic = (
                validate_patient_name_using_full_name_history(
                    patient_name_in_file_name, patient_details
                )
            )
            assert actual_is_validate_on_historic is False
    else:
        with pytest.raises(LGInvalidFilesException):
            validate_patient_name_using_full_name_history(
                patient_name_in_file_name, patient_details
            )


@pytest.mark.parametrize(
    ["patient_details", "patient_name_in_file_name", "should_accept_name"],
    load_test_cases(TEST_CASES_FOR_FAMILY_NAME_WITH_HYPHEN),
)
def test_validate_patient_name_with_family_name_with_hyphen_lenient(
    patient_details: Patient,
    patient_name_in_file_name: str,
    should_accept_name: bool,
):
    actual_score, actual_is_validate_on_historic, result_message = (
        calculate_validation_score_for_lenient_check(
            patient_name_in_file_name, patient_details
        )
    )
    if should_accept_name:
        expected_message = "matched on 1 family_name and 1 given name"
        assert result_message == expected_message
        assert actual_is_validate_on_historic is False
        assert actual_score == ValidationScore.FULL_MATCH
    else:
        expected_message = "matched on 0 family_name and 1 given name"
        assert result_message == expected_message
        assert actual_is_validate_on_historic is False
        assert actual_score == ValidationScore.PARTIAL_MATCH


@pytest.mark.parametrize(
    ["patient_details", "patient_name_in_file_name", "should_accept_name"],
    load_test_cases(TEST_CASES_FOR_TWO_WORDS_GIVEN_NAME),
)
def test_validate_patient_name_with_two_words_given_name_strict(
    patient_details: Patient,
    patient_name_in_file_name: str,
    should_accept_name: bool,
):
    if should_accept_name:
        with expect_not_to_raise(LGInvalidFilesException):
            validate_patient_name_using_full_name_history(
                patient_name_in_file_name, patient_details
            )
    else:
        with pytest.raises(LGInvalidFilesException):
            validate_patient_name_using_full_name_history(
                patient_name_in_file_name, patient_details
            )


@pytest.mark.parametrize(
    ["patient_details", "patient_name_in_file_name", "should_accept_name"],
    load_test_cases(TEST_CASES_FOR_TWO_WORDS_GIVEN_NAME),
)
def test_validate_patient_name_with_two_words_given_name_lenient(
    patient_details: Patient,
    patient_name_in_file_name: str,
    should_accept_name: bool,
):
    actual_score, actual_is_validate_on_historic, result_message = (
        calculate_validation_score_for_lenient_check(
            patient_name_in_file_name, patient_details
        )
    )
    if should_accept_name:
        expected_message = "matched on 1 family_name and 1 given name"
        assert result_message == expected_message
        assert actual_is_validate_on_historic is False
        assert actual_score == ValidationScore.FULL_MATCH
    else:
        expected_message = "matched on 1 family_name and 0 given name"
        assert result_message == expected_message
        assert actual_is_validate_on_historic is False
        assert actual_score == ValidationScore.PARTIAL_MATCH


@pytest.mark.parametrize(
    ["patient_details", "patient_name_in_file_name", "should_accept_name"],
    load_test_cases(TEST_CASES_FOR_TWO_WORDS_FAMILY_NAME_AND_GIVEN_NAME),
)
def test_validate_patient_name_with_two_words_family_name_and_given_name_strict(
    patient_details: Patient,
    patient_name_in_file_name: str,
    should_accept_name: bool,
):
    if should_accept_name:
        with expect_not_to_raise(LGInvalidFilesException):
            validate_patient_name_using_full_name_history(
                patient_name_in_file_name, patient_details
            )
    else:
        with pytest.raises(LGInvalidFilesException):
            validate_patient_name_using_full_name_history(
                patient_name_in_file_name, patient_details
            )


@pytest.mark.parametrize(
    ["patient_details", "patient_name_in_file_name", "should_accept_name"],
    load_test_cases(TEST_CASES_FOR_EMPTY_GIVEN_NAME),
)
def test_validate_patient_name_with_family_name_and_empty_given_name_strict(
    patient_details: Patient,
    patient_name_in_file_name: str,
    should_accept_name: bool,
):
    if should_accept_name:
        with expect_not_to_raise(LGInvalidFilesException):
            validate_patient_name_using_full_name_history(
                patient_name_in_file_name, patient_details
            )
    else:
        with pytest.raises(LGInvalidFilesException):
            validate_patient_name_using_full_name_history(
                patient_name_in_file_name, patient_details
            )


@pytest.mark.parametrize(
    ["patient_details", "patient_name_in_file_name", "should_accept_name"],
    load_test_cases(TEST_CASES_FOR_TWO_WORDS_FAMILY_NAME_AND_GIVEN_NAME),
)
def test_validate_patient_name_with_two_words_family_name_and_given_name_lenient(
    patient_details: Patient,
    patient_name_in_file_name: str,
    should_accept_name: bool,
):
    actual_score, actual_is_validate_on_historic, result_message = (
        calculate_validation_score_for_lenient_check(
            patient_name_in_file_name, patient_details
        )
    )
    if should_accept_name:
        expected_message = "matched on 1 family_name and 1 given name"
        assert result_message == expected_message
        assert actual_is_validate_on_historic is False
        assert actual_score == ValidationScore.FULL_MATCH
    else:
        assert actual_is_validate_on_historic is False
        assert actual_score == ValidationScore.PARTIAL_MATCH


def test_missing_middle_name_names_with_pds_service():
    lg_file_list = [
        "1of2_Lloyd_George_Record_[Jane Smith]_[9000000009]_[22-10-2010].pdf",
        "2of2_Lloyd_George_Record_[Jane Smith]_[9000000009]_[22-10-2010].pdf",
    ]
    patient = Patient.model_validate(PDS_PATIENT_WITH_MIDDLE_NAME)

    with expect_not_to_raise(LGInvalidFilesException):
        validate_filename_with_patient_details_lenient(lg_file_list, patient)
        validate_filename_with_patient_details_strict(lg_file_list, patient)


def test_mismatch_dob_and_name_with_pds_service(mock_pds_patient):
    lg_file_list = [
        "1of2_Lloyd_George_Record_[Jake Plain Smith]_[9000000009]_[14-01-2000].pdf",
        "2of2_Lloyd_George_Record_[Jake Plain Smith]_[9000000009]_[14-01-2000].pdf",
    ]

    with pytest.raises(LGInvalidFilesException):
        validate_filename_with_patient_details_lenient(lg_file_list, mock_pds_patient)
        validate_filename_with_patient_details_strict(lg_file_list, mock_pds_patient)


def test_validate_date_of_birth_when_mismatch_dob_with_pds_service(
    mock_pds_patient,
):
    file_date_of_birth = "14-01-2000"

    actual = validate_patient_date_of_birth(file_date_of_birth, mock_pds_patient)

    assert actual is False


def test_validate_date_of_birth_valid_with_pds_service(mock_pds_patient):
    file_date_of_birth = "22-10-2010"
    actual = validate_patient_date_of_birth(file_date_of_birth, mock_pds_patient)
    assert actual is True


def test_validate_date_of_birth_none_with_pds_service(mock_pds_patient):
    file_date_of_birth = "22-10-2010"
    mock_pds_patient.birth_date = None
    actual = validate_patient_date_of_birth(file_date_of_birth, mock_pds_patient)
    assert actual is False


def test_patient_not_found_with_pds_service(mock_pds_call):
    response = Response()
    response.status_code = 404

    mock_pds_call.return_value = response

    with pytest.raises(PatientNotFoundException) as e:
        getting_patient_info_from_pds("9000000009")
    assert str(e.value) == "Could not find the given patient on PDS"

    mock_pds_call.assert_called_with(nhs_number="9000000009", retry_on_expired=True)


def test_bad_request_with_pds_service(mock_pds_call):
    response = Response()
    response.status_code = 400

    mock_pds_call.return_value = response

    with pytest.raises(LGInvalidFilesException) as e:
        getting_patient_info_from_pds("9000000009")
    assert str(e.value) == "Failed to retrieve patient data from PDS"

    mock_pds_call.assert_called_with(nhs_number="9000000009", retry_on_expired=True)


def test_validate_with_pds_service_raise_pds_too_many_requests_exception(mock_pds_call):
    response = Response()
    response.status_code = 429
    response._content = b"Too Many Requests"
    mock_pds_call.return_value = response

    with pytest.raises(PdsTooManyRequestsException):
        getting_patient_info_from_pds("9000000009")

    mock_pds_call.assert_called_with(nhs_number="9000000009", retry_on_expired=True)


def test_check_pds_response_429_status_raise_too_many_requests_exception():
    response = Response()
    response.status_code = 429

    with pytest.raises(PdsTooManyRequestsException):
        check_pds_response_status(response)


def test_check_pds_response_404_status_raises_patient_not_found_exception():
    response = Response()
    response.status_code = 404

    with pytest.raises(PatientNotFoundException):
        check_pds_response_status(response)


def test_check_pds_response_4xx_or_5xx_status_raise_lg_invalid_files_exception():
    response = Response()
    response.status_code = 500

    with pytest.raises(LGInvalidFilesException):
        check_pds_response_status(response)


def test_check_pds_response_200_status_not_raise_exception():
    response = Response()
    response.status_code = 200

    with expect_not_to_raise(LGInvalidFilesException):
        check_pds_response_status(response)


def test_parse_pds_response_return_the_patient_object(
    mock_pds_call, mock_valid_pds_response
):
    actual = parse_pds_response(mock_valid_pds_response)
    assert actual.id == "9000000017"
    assert actual.name[0].given == ["Jane"]
    assert actual.name[0].family == "Smith"


def test_parse_pds_response_raise_error_when_model_validation_failed():
    mock_invalid_pds_response = Response()
    mock_invalid_pds_response.status_code = 200
    mock_invalid_pds_response._content = (
        b"""{"body": "some data that pydantic cannot parse"}"""
    )

    with pytest.raises(LGInvalidFilesException) as error:
        parse_pds_response(mock_invalid_pds_response)

    assert str(error.value) == "Fail to parse the patient detail response from PDS API."


def test_check_for_patient_already_exist_in_repo_return_none_when_patient_record_not_exist(
    set_env, mock_fetch_available_document_references_by_type
):
    mock_fetch_available_document_references_by_type.return_value = []
    expected = None
    actual = check_for_patient_already_exist_in_repo(TEST_NHS_NUMBER)

    assert actual == expected

    mock_fetch_available_document_references_by_type.assert_called_with(
        nhs_number=TEST_NHS_NUMBER,
        doc_type=SupportedDocumentTypes.LG,
        query_filter=NotDeleted,
    )


def test_check_check_for_patient_already_exist_in_repo_raise_exception_when_patient_record_already_exist(
    set_env, mock_fetch_available_document_references_by_type
):
    mock_fetch_available_document_references_by_type.return_value = [
        MOCK_DOCUMENT_REFERENCE
    ]

    with pytest.raises(PatientRecordAlreadyExistException):
        check_for_patient_already_exist_in_repo(TEST_NHS_NUMBER)

    mock_fetch_available_document_references_by_type.assert_called_with(
        nhs_number=TEST_NHS_NUMBER,
        doc_type=SupportedDocumentTypes.LG,
        query_filter=NotDeleted,
    )


def test_validate_bulk_files_raises_patient_record_already_exist_exception_when_patient_record_already_exists(
    set_env, mocker
):
    mocker.patch(
        "utils.lloyd_george_validator.check_for_patient_already_exist_in_repo",
        side_effect=PatientRecordAlreadyExistException,
    )

    with pytest.raises(PatientRecordAlreadyExistException):
        validate_lg_file_names(
            TEST_STAGING_METADATA_WITH_INVALID_FILENAME, TEST_NHS_NUMBER_FOR_BULK_UPLOAD
        )


def test_get_allowed_ods_codes_return_a_list_of_ods_codes(mock_get_ssm_parameter):
    mock_get_ssm_parameter.return_value = "Y12345, H81109"
    expected = ["Y12345", "H81109"]

    actual = get_allowed_ods_codes()

    assert actual == expected


def test_get_allowed_ods_codes_can_handle_the_all_option(mock_get_ssm_parameter):
    mock_get_ssm_parameter.return_value = "ALL"

    expected = ["ALL"]

    actual = get_allowed_ods_codes()

    assert actual == expected


def test_get_allowed_ods_codes_remove_whitespaces_and_return_ods_codes_in_upper_case(
    mock_get_ssm_parameter,
):
    mock_get_ssm_parameter.return_value = "h12345 , abc12  ,  345xy "

    expected = ["H12345", "ABC12", "345XY"]

    actual = get_allowed_ods_codes()

    assert actual == expected


@pytest.mark.parametrize(
    ["gp_ods_param_value", "patient_ods_code", "expected"],
    [
        # can handle single ods code
        ["H81109", "H81109", True],
        ["H85686", "H81109", False],
        # can handle a list of ods codes
        ["H81109, H85686", "H81109", True],
        ["H81109, H85686", "H85686", True],
        ["H81109, H85686", "Y12345", False],
        # present of "ALL" option will allow any ods code to be accepted
        ["ALL", "H81109", True],
        ["ALL", "H85686", True],
        ["ALL", "", True],
        ["H81109, H85686, ALL", "Y12345", True],
    ],
)
def test_allowed_to_ingest_ods_code(
    mock_get_ssm_parameter, gp_ods_param_value, patient_ods_code, expected
):
    mock_get_ssm_parameter.return_value = gp_ods_param_value

    actual = allowed_to_ingest_ods_code(patient_ods_code)

    assert actual == expected


def test_allowed_to_ingest_ods_code_propagate_error(mock_get_ssm_parameter):
    mock_get_ssm_parameter.side_effect = ClientError(
        {"Error": {"Code": "500", "Message": "test error"}}, "GetParameter"
    )

    with pytest.raises(ClientError):
        allowed_to_ingest_ods_code("H81109")


def test_mismatch_nhs_in_validate_lg_file(mocker, mock_pds_patient):
    mocker.patch(
        "utils.lloyd_george_validator.check_for_number_of_files_match_expected"
    )
    mocker.patch("utils.lloyd_george_validator.validate_file_name")
    patient_with_different_nhs_number = mock_pds_patient.model_copy(
        update={"id": "9876543210"}
    )

    with pytest.raises(LGInvalidFilesException):
        validate_lg_files(
            TEST_DOCUMENT_REFERENCE_LIST, patient_with_different_nhs_number
        )


@pytest.mark.parametrize(
    ["file_patient_name", "first_name_from_pds", "family_name_from_pds"],
    [
        ["Jim Stevens", "Jane", "Smith"],
        ["Jane Smith Anderson", "Jane", "Smith"],
        ["Bob Smith Anderson", "Jane", "Smith"],
        ["Jane B Smith Anderson", "Jane", "Smith"],
        ["Jane Bob Anderson", "Jane", "Smith"],
        ["Jane Bob Smith", "Jane Bob", "Smith Anderson"],
        ["Jane Smith", "Jane Bob", "Smith"],
        ["Jane B Smith", "Jane Bob", "Smith"],
        ["Jane-Bob Smith", "Jane Bob", "Smith"],
        ["Jane Smith", "Jane Bob", "Smith"],
        ["Jane Smith Anderson", "Jane", "Smith-Anderson"],
        ["Jane Smith", "Jane", "Smith-Anderson"],
        ["Jane Anderson", "Jane", "Smith-Anderson"],
        ["Jane Bob Smith", "Jane Bob", "Smith-Anderson"],
        ["Bob Smith Anderson", "Jane", "Smith Anderson"],
        ["Jane Smith", "Jane", "Smith Anderson"],
        ["Jane Anderson", "Jane", "Smith Anderson"],
        ["Jane Anderson Smith", "Jane", "Smith Anderson"],
    ],
)
def test_validate_patient_name_return_false(
    file_patient_name, first_name_from_pds, family_name_from_pds
):
    actual = validate_patient_name_strict(
        file_patient_name, first_name_from_pds, family_name_from_pds
    )
    assert actual is False


@pytest.mark.parametrize(
    ["file_patient_name", "first_name_from_pds", "family_name_from_pds"],
    [
        ["Jane Smith", "Jane", "Smith"],
        ["Jane Bob Smith Anderson", "Jane", "Smith Anderson"],
        ["Jane Smith Anderson", "Jane", "Smith Anderson"],
        ["Jane B Smith Anderson", "Jane", "Smith Anderson"],
        ["Jane Smith-Anderson", "Jane", "Smith-Anderson"],
        ["Jane Bob Smith Anderson", "Jane Bob", "Smith Anderson"],
        ["Jane Bob Smith", "Jane Bob", "Smith"],
        ["Jane Bob Smith", "Jane Bob", ""],
    ],
)
def test_validate_patient_name_return_true(
    file_patient_name, first_name_from_pds, family_name_from_pds
):
    actual = validate_patient_name_strict(
        file_patient_name, first_name_from_pds, family_name_from_pds
    )
    assert actual is True


@pytest.mark.parametrize(
    ["file_patient_name", "first_name_from_pds", "family_name_from_pds", "result"],
    [
        ("Jim Stevens", ["Jane"], "Smith", ValidationScore.NO_MATCH),
        ["Jane Smith Anderson", ["Jane"], "Smith", ValidationScore.FULL_MATCH],
        ["Bob Smith Anderson", ["Jane"], "Smith", ValidationScore.PARTIAL_MATCH],
        ["Bob Smith Anderson", ["Jane", "Bob"], "Smith", ValidationScore.FULL_MATCH],
        ["Jane B Smith Anderson", ["Jane"], "Smith", ValidationScore.FULL_MATCH],
        ["Jane Bob Anderson", ["Jane"], "Smith", ValidationScore.PARTIAL_MATCH],
        [
            "Jane Bob Smith",
            ["Jane Bob"],
            "Smith Anderson",
            ValidationScore.PARTIAL_MATCH,
        ],
        ["Jane Smith", ["Jane Bob"], "Smith", ValidationScore.PARTIAL_MATCH],
        ["Jane B Smith", ["Jane Bob"], "Smith", ValidationScore.PARTIAL_MATCH],
        ["Jane-Bob Smith", ["Jane Bob"], "Smith", ValidationScore.PARTIAL_MATCH],
        ["Jane Smith", ["Jane Bob"], "Smith", ValidationScore.PARTIAL_MATCH],
        [
            "Jane Smith Anderson",
            ["Jane"],
            "Smith-Anderson",
            ValidationScore.PARTIAL_MATCH,
        ],
        ["Jane Smith", ["Jane"], "Smith-Anderson", ValidationScore.PARTIAL_MATCH],
        ["Jane Anderson", ["Jane"], "Smith-Anderson", ValidationScore.PARTIAL_MATCH],
        [
            "Jane Bob Smith",
            ["Jane Bob"],
            "Smith-Anderson",
            ValidationScore.PARTIAL_MATCH,
        ],
        [
            "Bob Smith Anderson",
            ["Jane"],
            "Smith Anderson",
            ValidationScore.PARTIAL_MATCH,
        ],
        ["Jane Smith", ["Jane"], "Smith Anderson", ValidationScore.PARTIAL_MATCH],
        ["Jane Anderson", ["Jane"], "Smith Anderson", ValidationScore.PARTIAL_MATCH],
        [
            "Jane Anderson",
            ["Jane", "A"],
            "Smith Anderson",
            ValidationScore.PARTIAL_MATCH,
        ],
        [
            "Jane Anderson Smith",
            ["Jane"],
            "Smith Anderson",
            ValidationScore.PARTIAL_MATCH,
        ],
    ],
)
def test_validate_patient_name_lenient_return_false(
    file_patient_name, first_name_from_pds, family_name_from_pds, result
):
    actual = validate_patient_name_lenient(
        file_patient_name, first_name_from_pds, family_name_from_pds
    )
    assert actual.score == result


@pytest.mark.parametrize(
    ["file_patient_name", "first_name_from_pds", "family_name_from_pds", "expected"],
    [
        (
            "Jane Smith",
            ["Jane"],
            "Smith",
            ValidationResult(
                score=ValidationScore.FULL_MATCH,
                given_name_match=["jane"],
                family_name_match="smith",
            ),
        ),
        (
            "Jane Bob Smith Anderson",
            ["Jane"],
            "Smith",
            ValidationResult(
                score=ValidationScore.FULL_MATCH,
                given_name_match=["jane"],
                family_name_match="smith",
            ),
        ),
        (
            "Jane Smith Anderson",
            ["Jane"],
            "Smith Anderson",
            ValidationResult(
                score=ValidationScore.FULL_MATCH,
                given_name_match=["jane"],
                family_name_match="smith anderson",
            ),
        ),
        (
            "Jane B Smith Anderson",
            ["Jane"],
            "Smith Anderson",
            ValidationResult(
                score=ValidationScore.FULL_MATCH,
                given_name_match=["jane"],
                family_name_match="smith anderson",
            ),
        ),
        (
            "Jane Smith-Anderson",
            ["Jane"],
            "Smith-Anderson",
            ValidationResult(
                score=ValidationScore.FULL_MATCH,
                given_name_match=["jane"],
                family_name_match="smith-anderson",
            ),
        ),
        (
            "Jane Bob Smith Anderson",
            ["Jane Bob"],
            "Smith Anderson",
            ValidationResult(
                score=ValidationScore.FULL_MATCH,
                given_name_match=["jane bob"],
                family_name_match="smith anderson",
            ),
        ),
        (
            "Jane Bob Smith",
            ["Jane Bob"],
            "Smith",
            ValidationResult(
                score=ValidationScore.FULL_MATCH,
                given_name_match=["jane bob"],
                family_name_match="smith",
            ),
        ),
        (
            "Jane Bob Smith",
            ["Jane Bob"],
            "Anderson",
            ValidationResult(
                score=ValidationScore.PARTIAL_MATCH,
                given_name_match=["jane bob"],
            ),
        ),
        (
            "Jane Smith",
            ["Bob"],
            "Smith",
            ValidationResult(
                score=ValidationScore.PARTIAL_MATCH,
                family_name_match="smith",
            ),
        ),
        (
            "Jane Smith",
            ["Bob"],
            "Dylan",
            ValidationResult(
                score=ValidationScore.NO_MATCH,
            ),
        ),
        (
            "Bob Smith",
            ["Bob", "S"],
            "Dylan",
            ValidationResult(
                score=ValidationScore.PARTIAL_MATCH,
                given_name_match=["bob"],
            ),
        ),
        (
            "Bob S Marleys",
            ["Bob", "S"],
            "Dylan",
            ValidationResult(
                score=ValidationScore.PARTIAL_MATCH,
                given_name_match=["bob"],
            ),
        ),
        (
            "Bob Sam Marleys",
            ["Bob", "Sam"],
            "Dylan",
            ValidationResult(
                score=ValidationScore.PARTIAL_MATCH,
                given_name_match=["bob", "sam"],
            ),
        ),
    ],
)
def test_validate_patient_name_lenient_return_true(
    file_patient_name, first_name_from_pds, family_name_from_pds, expected
):
    actual = validate_patient_name_lenient(
        file_patient_name, first_name_from_pds, family_name_from_pds
    )
    assert actual == expected


@pytest.mark.parametrize(
    ["file_patient_name", "expected_score", "expected_historical_match"],
    [
        ("Jane Smith", ValidationScore.FULL_MATCH, True),
        ("Smith Jane", ValidationScore.FULL_MATCH, True),
        ("Jane Bob Smith Moody", ValidationScore.FULL_MATCH, False),
        ("Jane Smith Moody", ValidationScore.FULL_MATCH, True),
        ("Jane B Smith Moody", ValidationScore.FULL_MATCH, True),
        ("Jane Smith-Moody", ValidationScore.FULL_MATCH, True),
        ("Jane Bob Smith Moody", ValidationScore.FULL_MATCH, False),
        ("Jane Bob Smith", ValidationScore.FULL_MATCH, False),
        ("Bob Smith", ValidationScore.PARTIAL_MATCH, True),
        ("Bob Jane", ValidationScore.FULL_MATCH, False),
        ("Alastor Moody", ValidationScore.NO_MATCH, False),
        ("Jones Bob", ValidationScore.MIXED_FULL_MATCH, True),
        ("Jones Jane", ValidationScore.PARTIAL_MATCH, True),
        ("Paul Anderson", ValidationScore.PARTIAL_MATCH, True),
        ("Jane Jane", ValidationScore.PARTIAL_MATCH, False),
        ("Jane Janet", ValidationScore.PARTIAL_MATCH, False),
    ],
)
def test_calculate_validation_score_for_lenient_check(
    file_patient_name, expected_score, expected_historical_match
):
    name_1 = build_test_name(start="1990-01-01", end=None, given=["Jane"])
    name_2 = build_test_name(start="1995-01-01", end=None, given=["Jane"], family="Bob")
    name_3 = build_test_name(use="temp", start=None, end=None, given=["Jones"])
    name_4 = build_test_name(
        use="usual", start="1995-01-01", end=None, given=["Paul", "Anderson"]
    )
    name_5 = build_test_name(start="1980-01-01", end="1990-01-01", given=["JANE"])

    test_patient = build_test_patient_with_names(
        [name_1, name_2, name_3, name_4, name_5]
    )

    actual_result, historical, _ = calculate_validation_score_for_lenient_check(
        file_patient_name, test_patient
    )
    assert historical == expected_historical_match
    assert actual_result == expected_score


def test_validates_correct_scan_date_format():
    scan_date = "12-03-2023"
    result = validate_scan_date(scan_date)
    assert result == "2023-03-12"

@pytest.mark.parametrize("scan_date", ["", "not-a-date", "1678246", "12/12/2024 12:12", "2023/03/12"])
def test_raises_exception_for_invalid_scan_date_format(scan_date):
    with pytest.raises(LGInvalidFilesException, match="Invalid scan date format"):
        validate_scan_date(scan_date)
