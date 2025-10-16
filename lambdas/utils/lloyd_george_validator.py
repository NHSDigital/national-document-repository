import datetime
import os
import re

import pydantic
import requests
from enums.pds_ssm_parameters import SSMParameter
from enums.supported_document_types import SupportedDocumentTypes
from enums.validation_score import ValidationResult, ValidationScore
from models.document_reference import DocumentReference
from models.pds_models import Patient
from requests import HTTPError
from services.base.ssm_service import SSMService
from services.document_service import DocumentService
from utils.audit_logging_setup import LoggingService
from utils.common_query_filters import NotDeleted
from utils.exceptions import (
    LGInvalidFilesException,
    PatientNotFoundException,
    PatientRecordAlreadyExistException,
    PdsTooManyRequestsException,
)
from utils.unicode_utils import (
    REGEX_PATIENT_NAME_PATTERN,
    convert_to_nfd_form,
    name_contains_in,
    name_ends_with,
    name_starts_with,
)
from utils.utilities import get_pds_service, parse_date

logger = LoggingService(__name__)

file_name_invalid = "One or more of the files do not match naming convention"
file_type_invalid = "One or more of the files do not match the required file type"


def validate_lg_file_type(file_type: str):
    if file_type != "application/pdf":
        raise LGInvalidFilesException(file_type_invalid)


def validate_file_name(name: str):
    nhs_number_pattern = "[0-9]{10}"
    lg_regex = rf"[0-9]+of[0-9]+_Lloyd_George_Record_\[{REGEX_PATIENT_NAME_PATTERN}\]_\[{nhs_number_pattern}\]_\[\d\d-\d\d-\d\d\d\d].pdf"
    if not re.fullmatch(lg_regex, name):
        raise LGInvalidFilesException(file_name_invalid)


def check_for_duplicate_files(file_list: list[str]):
    if len(file_list) > len(set(file_list)):
        raise LGInvalidFilesException("One or more of the files has the same filename")


def check_for_number_of_files_match_expected(file_name: str, total_files_number: int):
    lg_number_regex = "of[0-9]+"
    regex_match_result = re.search(lg_number_regex, file_name)
    try:
        expected_number_of_files = int(regex_match_result.group()[2:])
        if total_files_number < expected_number_of_files:
            raise LGInvalidFilesException("There are missing file(s) in the request")
        elif total_files_number > expected_number_of_files:
            raise LGInvalidFilesException(
                "There are more files than the total number in file name"
            )
    except (AttributeError, IndexError, ValueError):
        raise LGInvalidFilesException(file_name_invalid)


def check_for_patient_already_exist_in_repo(nhs_number: str):
    document_service = DocumentService()
    documents_found = document_service.fetch_available_document_references_by_type(
        nhs_number=nhs_number,
        doc_type=SupportedDocumentTypes.LG,
        query_filter=NotDeleted,
    )

    if documents_found:
        raise PatientRecordAlreadyExistException(
            "Lloyd George already exists for patient, upload cancelled."
        )


def validate_lg_files(file_list: list[DocumentReference], pds_patient_details: Patient):
    nhs_number = pds_patient_details.id
    files_name_list = []

    for doc in file_list:
        check_for_number_of_files_match_expected(doc.file_name, len(file_list))
        validate_lg_file_type(doc.content_type)
        checks_per_filename(doc.file_name, nhs_number)
        files_name_list.append(doc.file_name)

    check_for_duplicate_files(files_name_list)
    validate_filename_with_patient_details_strict(files_name_list, pds_patient_details)


def validate_lg_file_names(file_name_list: list[str], nhs_number: str):
    check_for_patient_already_exist_in_repo(nhs_number)

    for file_name in file_name_list:
        check_for_number_of_files_match_expected(file_name, len(file_name_list))
        checks_per_filename(file_name, nhs_number)

    check_for_duplicate_files(file_name_list)
    check_for_file_names_agrees_with_each_other(file_name_list)


def checks_per_filename(file_name: str, nhs_number: str):
    validate_file_name(file_name)
    file_name_info = extract_info_from_filename(file_name)
    if file_name_info["nhs_number"] != nhs_number:
        raise LGInvalidFilesException(
            "NHS number in file names does not match the given NHS number"
        )


def extract_info_from_filename(filename: str) -> dict:
    page_number = r"(?P<page_no>[1-9][0-9]*)"
    total_page_number = r"(?P<total_page_no>[1-9][0-9]*)"
    patient_name = rf"(?P<patient_name>{REGEX_PATIENT_NAME_PATTERN})"
    nhs_number = r"(?P<nhs_number>\d{10})"
    date_of_birth = r"(?P<date_of_birth>\d\d-\d\d-\d\d\d\d)"

    # ruff: noqa: E501
    lg_regex = rf"{page_number}of{total_page_number}_Lloyd_George_Record_\[{patient_name}\]_\[{nhs_number}\]_\[{date_of_birth}\].pdf"

    if match := re.fullmatch(lg_regex, filename):
        return match.groupdict()
    else:
        raise LGInvalidFilesException(file_name_invalid)


def check_for_file_names_agrees_with_each_other(file_name_list: list[str]):
    expected_common_part = [
        file_name[file_name.index("of") :] for file_name in file_name_list
    ]
    if len(set(expected_common_part)) != 1:
        raise LGInvalidFilesException("File names does not match with each other")


def validate_filename_with_patient_details_strict(
    file_name_list: list[str], patient_details: Patient
):
    try:
        file_name_info = extract_info_from_filename(file_name_list[0])
        file_patient_name = file_name_info["patient_name"]
        file_date_of_birth = file_name_info["date_of_birth"]
        is_dob_valid = validate_patient_date_of_birth(
            file_date_of_birth, patient_details
        )
        if not is_dob_valid:
            raise LGInvalidFilesException("Patient DoB does not match our records")
        is_name_validation_based_on_historic_name = (
            validate_patient_name_using_full_name_history(
                file_patient_name, patient_details
            )
        )
        return is_name_validation_based_on_historic_name
    except (ValueError, KeyError) as e:
        logger.error(e)
        raise LGInvalidFilesException(e)


def validate_patient_name_strict(
    file_patient_name: str, first_name_in_pds: str, family_name_in_pds: str
):
    logger.info("Verifying patient name against the record in PDS...")

    first_name_matches = name_starts_with(file_patient_name, first_name_in_pds)
    family_name_matches = name_ends_with(file_patient_name, family_name_in_pds)

    if not (first_name_matches and family_name_matches):
        return False
    return True


def validate_patient_name_using_full_name_history(
    file_patient_name: str, pds_patient_details: Patient
):
    usual_family_name_in_pds, usual_first_name_in_pds = (
        pds_patient_details.get_current_family_name_and_given_name()
    )

    if (
        usual_first_name_in_pds
        and usual_family_name_in_pds
        and validate_patient_name_strict(
            file_patient_name, usual_first_name_in_pds[0], usual_family_name_in_pds
        )
    ):
        return False
    logger.info(
        "Failed to validate patient name using usual name, trying to validate using name history"
    )

    for name in pds_patient_details.name:
        if not name.given or not name.family:
            continue
        historic_first_name_in_pds: str = name.given[0]
        historic_family_name_in_pds = name.family
        if validate_patient_name_strict(
            file_patient_name, historic_first_name_in_pds, historic_family_name_in_pds
        ):
            return True

    raise LGInvalidFilesException("Patient name does not match our records")


def validate_filename_with_patient_details_lenient(
    file_name_list: list[str], patient_details: Patient
) -> (str, bool):
    try:
        file_name_info = extract_info_from_filename(file_name_list[0])
        file_patient_name = file_name_info["patient_name"]
        file_date_of_birth = file_name_info["date_of_birth"]
        name_validation_score, historical_match, result_message = (
            calculate_validation_score_for_lenient_check(
                file_patient_name, patient_details
            )
        )
        if name_validation_score == ValidationScore.NO_MATCH:
            raise LGInvalidFilesException("Patient name does not match our records")
        is_dob_valid = validate_patient_date_of_birth(
            file_date_of_birth, patient_details
        )
        if not is_dob_valid and name_validation_score == ValidationScore.PARTIAL_MATCH:
            raise LGInvalidFilesException("Patient name does not match our records 1/3")
        validation_messages = {
            ValidationScore.PARTIAL_MATCH: {
                True: f"Patient matched on partial match 2/3, {result_message}",
                False: "",
            },
            ValidationScore.MIXED_FULL_MATCH: {
                True: f"Patient matched on mixed match 3/3, {result_message}",
                False: f"Patient matched on mixed match 2/3, {result_message}",
            },
            ValidationScore.FULL_MATCH: {
                True: f"Patient matched on full match 3/3, {result_message}",
                False: f"Patient matched on full match 2/3, {result_message}",
            },
        }
        acceptance_message = validation_messages[name_validation_score][is_dob_valid]
        return acceptance_message, historical_match

    except (ValueError, KeyError) as e:
        logger.error(e)
        raise LGInvalidFilesException(e)


def calculate_validation_score_for_lenient_check(
    file_patient_name: str, patient_details: Patient
) -> (ValidationScore, bool, str):
    matched_on_given_name = set()
    matched_on_family_name = set()
    historical_match = False
    ordered_names = patient_details.get_names_by_start_date()
    for index, name in enumerate(ordered_names):
        first_name_in_pds = name.given
        family_name_in_pds = name.family
        result = validate_patient_name_lenient(
            file_patient_name, first_name_in_pds, family_name_in_pds
        )
        if result.score == ValidationScore.FULL_MATCH:
            result_message = f"matched on {1 if bool(result.family_name_match) else 0} family_name and {len(result.given_name_match)} given name"
            historical_match = index != 0
            return result.score, historical_match, result_message
        elif result.score == ValidationScore.PARTIAL_MATCH:
            current_matched_on_given_name_len = len(matched_on_given_name)
            current_matched_on_family_name_len = len(matched_on_family_name)

            matched_on_given_name.update(result.given_name_match)
            (
                matched_on_family_name.add(result.family_name_match)
                if result.family_name_match
                else None
            )
            if (
                len(matched_on_given_name) != current_matched_on_given_name_len
                or len(matched_on_family_name) != current_matched_on_family_name_len
            ):
                historical_match = index != 0

            logger.info(
                "Failed to find full match on patient name, trying to validate using name history"
            )
    result_message = f"matched on {len(matched_on_family_name)} family_name and {len(matched_on_given_name)} given name"
    if len(matched_on_given_name) > 0 and len(matched_on_family_name) > 0:
        return ValidationScore.MIXED_FULL_MATCH, historical_match, result_message
    elif matched_on_given_name or matched_on_family_name:
        return ValidationScore.PARTIAL_MATCH, historical_match, result_message
    return ValidationScore.NO_MATCH, False, "No match found"


def validate_patient_name_lenient(
    file_patient_name: str, first_name_in_pds: list[str], family_name_in_pds: str
) -> ValidationResult:
    logger.info("Verifying patient name against the record in PDS...")
    family_name_in_pds = convert_to_nfd_form(family_name_in_pds).casefold()

    given_name_matches = [
        convert_to_nfd_form(first_name).casefold()
        for first_name in first_name_in_pds
        if len(first_name) > 1 and name_contains_in(file_patient_name, first_name)
    ]
    family_name_matches = (
        name_contains_in(file_patient_name, family_name_in_pds)
        if family_name_in_pds
        else None
    )

    if given_name_matches and family_name_matches:
        return ValidationResult(
            score=ValidationScore.FULL_MATCH,
            given_name_match=given_name_matches,
            family_name_match=family_name_in_pds,
        )
    elif given_name_matches:
        return ValidationResult(
            score=ValidationScore.PARTIAL_MATCH,
            given_name_match=given_name_matches,
        )
    elif family_name_matches:
        return ValidationResult(
            score=ValidationScore.PARTIAL_MATCH, family_name_match=family_name_in_pds
        )
    return ValidationResult(
        score=ValidationScore.NO_MATCH,
    )


def validate_patient_date_of_birth(file_date_of_birth, pds_patient_details):
    date_of_birth = datetime.datetime.strptime(file_date_of_birth, "%d-%m-%Y").date()
    if pds_patient_details.birth_date:
        return pds_patient_details.birth_date == date_of_birth
    return False


def getting_patient_info_from_pds(nhs_number: str) -> Patient:
    pds_service = get_pds_service()
    pds_response = pds_service.pds_request(nhs_number=nhs_number, retry_on_expired=True)
    check_pds_response_status(pds_response)
    patient = parse_pds_response(pds_response)
    return patient


def check_pds_response_status(pds_response: requests.Response):
    if pds_response.status_code == 429:
        logger.error("Got 429 Too Many Requests error from PDS.")
        raise PdsTooManyRequestsException(
            "Failed to validate filename against PDS record due to too many requests"
        )
    elif pds_response.status_code == 404:
        logger.error("Got 404, Could not find the given patient on PDS.")
        raise PatientNotFoundException("Could not find the given patient on PDS")
    try:
        pds_response.raise_for_status()
    except HTTPError as e:
        logger.error(e)
        raise LGInvalidFilesException("Failed to retrieve patient data from PDS")


def parse_pds_response(pds_response: requests.Response) -> Patient:
    try:
        patient = Patient.model_validate(pds_response.json())
        return patient
    except pydantic.ValidationError:
        error_msg = "Fail to parse the patient detail response from PDS API."
        logger.error(error_msg)
        raise LGInvalidFilesException(error_msg)


def get_allowed_ods_codes() -> list[str]:
    if os.getenv("PDS_FHIR_IS_STUBBED") in ["True", "true"]:
        return ["ALL"]
    else:
        ssm_service = SSMService()
        gp_ods = ssm_service.get_ssm_parameter(SSMParameter.GP_ODS_CODE.value)
        return [ods_code.strip().upper() for ods_code in gp_ods.split(",")]


def allowed_to_ingest_ods_code(patient_ods_code: str) -> bool:
    allowed_ods_codes = get_allowed_ods_codes()

    if "ALL" in allowed_ods_codes:
        return True

    return patient_ods_code.upper() in allowed_ods_codes


def validate_scan_date(scan_date: str):
    if formatted_date := parse_date(scan_date):
        return formatted_date.strftime("%Y-%m-%d")
    else:
        raise LGInvalidFilesException("Invalid scan date format")
