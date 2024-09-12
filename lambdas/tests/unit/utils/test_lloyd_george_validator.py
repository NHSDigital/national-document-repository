import pytest
from botocore.exceptions import ClientError
from enums.supported_document_types import SupportedDocumentTypes
from models.pds_models import Patient
from requests import Response
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
from tests.unit.helpers.data.pds.test_cases_for_patient_name_matching import (
    TEST_CASES_FOR_FAMILY_NAME_WITH_HYPHEN,
    TEST_CASES_FOR_TWO_WORDS_FAMILY_NAME,
    TEST_CASES_FOR_TWO_WORDS_FAMILY_NAME_AND_GIVEN_NAME,
    TEST_CASES_FOR_TWO_WORDS_GIVEN_NAME,
    load_test_cases,
)
from tests.unit.models.test_document_reference import MOCK_DOCUMENT_REFERENCE
from utils.common_query_filters import NotDeleted
from utils.exceptions import (
    PatientRecordAlreadyExistException,
    PdsTooManyRequestsException,
)
from utils.lloyd_george_validator import (
    LGInvalidFilesException,
    allowed_to_ingest_ods_code,
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
    validate_filename_with_patient_details,
    validate_lg_file_names,
    validate_lg_file_type,
    validate_lg_files,
    validate_patient_date_of_birth,
    validate_patient_name,
    validate_patient_name_using_full_name_history,
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
        validate_filename_with_patient_details(lg_file_list, mock_pds_patient)


def test_mismatch_nhs_id(mocker):
    lg_file_list = [
        "1of2_Lloyd_George_Record_[Jane Smith]_[9000000005]_[22-10-2010].pdf",
        "2of2_Lloyd_George_Record_[Jane Smith]_[9000000005]_[22-10-2010].pdf",
    ]

    mocker.patch("utils.lloyd_george_validator.check_for_patient_already_exist_in_repo")
    mocker.patch(
        "utils.lloyd_george_validator.check_for_number_of_files_match_expected"
    )
    mocker.patch("utils.lloyd_george_validator.validate_file_name")

    with pytest.raises(LGInvalidFilesException):
        validate_lg_file_names(lg_file_list, "9000000009")


def test_mismatch_name_with_pds_service(mock_pds_patient):
    lg_file_list = [
        "1of2_Lloyd_George_Record_[Jake Plain Smith]_[9000000009]_[22-10-2010].pdf",
        "2of2_Lloyd_George_Record_[Jake Plain Smith]_[9000000009]_[22-10-2010].pdf",
    ]

    with pytest.raises(LGInvalidFilesException):
        validate_filename_with_patient_details(lg_file_list, mock_pds_patient)


def test_validate_name_with_correct_name(mocker, mock_pds_patient):
    lg_file_patient_name = "Jane Smith"
    mock_validate_name = mocker.patch(
        "utils.lloyd_george_validator.validate_patient_name"
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
        "utils.lloyd_george_validator.validate_patient_name"
    )
    with expect_not_to_raise(LGInvalidFilesException):
        validate_patient_name_using_full_name_history(lg_file_patient_name, patient)

    assert mock_validate_name.call_count == 1


def test_validate_name_with_additional_middle_name_in_file_mismatching_pds(mocker):
    lg_file_patient_name = "Jane David Smith"
    mock_validate_name = mocker.patch(
        "utils.lloyd_george_validator.validate_patient_name"
    )
    patient = Patient.model_validate(PDS_PATIENT_WITH_MIDDLE_NAME)

    with expect_not_to_raise(LGInvalidFilesException):
        actual_is_name_validation_based_on_historic_name = (
            validate_patient_name_using_full_name_history(lg_file_patient_name, patient)
        )
    assert mock_validate_name.call_count == 1
    assert actual_is_name_validation_based_on_historic_name is False


def test_validate_name_with_additional_middle_name_in_file_but_none_in_pds(
    mock_pds_patient, mocker
):
    lg_file_patient_name = "Jane David Smith"
    mock_validate_name = mocker.patch(
        "utils.lloyd_george_validator.validate_patient_name"
    )
    with expect_not_to_raise(LGInvalidFilesException):
        actual_is_name_validation_based_on_historic_name = (
            validate_patient_name_using_full_name_history(
                lg_file_patient_name, mock_pds_patient
            )
        )
    assert mock_validate_name.call_count == 1
    assert actual_is_name_validation_based_on_historic_name is False


def test_validate_name_with_wrong_first_name(mocker, mock_pds_patient):
    lg_file_patient_name = "John Smith"
    mock_validate_name = mocker.patch(
        "utils.lloyd_george_validator.validate_patient_name"
    )
    mock_validate_name.return_value = False

    with pytest.raises(LGInvalidFilesException):
        validate_patient_name_using_full_name_history(
            lg_file_patient_name, mock_pds_patient
        )
    assert mock_validate_name.call_count == 2


def test_validate_name_with_wrong_family_name(mocker, mock_pds_patient):
    lg_file_patient_name = "Jane Johnson"
    mock_validate_name = mocker.patch(
        "utils.lloyd_george_validator.validate_patient_name"
    )
    mock_validate_name.return_value = False
    with pytest.raises(LGInvalidFilesException):
        validate_patient_name_using_full_name_history(
            lg_file_patient_name, mock_pds_patient
        )
    assert mock_validate_name.call_count == 2


def test_validate_name_with_historical_name(mocker, mock_pds_patient):
    lg_file_patient_name = "Jim Stevens"
    mock_validate_name = mocker.patch(
        "utils.lloyd_george_validator.validate_patient_name"
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


def test_validate_name_without_given_name(mocker, mock_pds_patient):
    lg_file_patient_name = "Jane Smith"
    mock_pds_patient.name[0].given = [""]
    mock_validate_name = mocker.patch(
        "utils.lloyd_george_validator.validate_patient_name"
    )

    with expect_not_to_raise(LGInvalidFilesException):
        actual_is_validate_on_historic = validate_patient_name_using_full_name_history(
            lg_file_patient_name, mock_pds_patient
        )
    assert actual_is_validate_on_historic is False
    assert mock_validate_name.call_count == 1


@pytest.mark.parametrize(
    ["patient_details", "patient_name_in_file_name", "should_accept_name"],
    load_test_cases(TEST_CASES_FOR_TWO_WORDS_FAMILY_NAME),
)
def test_validate_patient_name_with_two_words_family_name(
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
def test_validate_patient_name_with_family_name_with_hyphen(
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
    load_test_cases(TEST_CASES_FOR_TWO_WORDS_GIVEN_NAME),
)
def test_validate_patient_name_with_two_words_given_name(
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
def test_validate_patient_name_with_two_words_family_name_and_given_name(
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


def test_missing_middle_name_names_with_pds_service():
    lg_file_list = [
        "1of2_Lloyd_George_Record_[Jane Smith]_[9000000009]_[22-10-2010].pdf",
        "2of2_Lloyd_George_Record_[Jane Smith]_[9000000009]_[22-10-2010].pdf",
    ]
    patient = Patient.model_validate(PDS_PATIENT_WITH_MIDDLE_NAME)

    with expect_not_to_raise(LGInvalidFilesException):
        validate_filename_with_patient_details(lg_file_list, patient)


def test_mismatch_dob_with_pds_service(mock_pds_patient):
    lg_file_list = [
        "1of2_Lloyd_George_Record_[Jane Plain Smith]_[9000000009]_[14-01-2000].pdf",
        "2of2_Lloyd_George_Record_[Jane Plain Smith]_[9000000009]_[14-01-2000].pdf",
    ]

    with pytest.raises(LGInvalidFilesException):
        validate_filename_with_patient_details(lg_file_list, mock_pds_patient)


def test_validate_date_of_birth_when_mismatch_dob_with_pds_service(
    mock_pds_patient,
):
    file_date_of_birth = "14-01-2000"

    with pytest.raises(LGInvalidFilesException):
        validate_patient_date_of_birth(file_date_of_birth, mock_pds_patient)


def test_validate_date_of_birth_valid_with_pds_service(mock_pds_patient):
    file_date_of_birth = "22-10-2010"
    with expect_not_to_raise(LGInvalidFilesException):
        validate_patient_date_of_birth(file_date_of_birth, mock_pds_patient)


def test_validate_date_of_birth_none_with_pds_service(mock_pds_patient):
    file_date_of_birth = "22-10-2010"
    mock_pds_patient.birth_date = None
    with pytest.raises(LGInvalidFilesException):
        validate_patient_date_of_birth(file_date_of_birth, mock_pds_patient)


def test_patient_not_found_with_pds_service(mock_pds_call):
    response = Response()
    response.status_code = 404

    mock_pds_call.return_value = response

    with pytest.raises(LGInvalidFilesException) as e:
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


def test_check_pds_response_404_status_raise_lg_invalid_files_exception():
    response = Response()
    response.status_code = 404

    with pytest.raises(LGInvalidFilesException):
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
    assert actual.id == "9000000002"
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
    actual = validate_patient_name(
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
    ],
)
def test_validate_patient_name_return_true(
    file_patient_name, first_name_from_pds, family_name_from_pds
):
    actual = validate_patient_name(
        file_patient_name, first_name_from_pds, family_name_from_pds
    )
    assert actual is True


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
