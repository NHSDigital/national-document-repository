import itertools
import os
import re
import uuid
from datetime import datetime
from urllib.parse import urlparse

from inflection import camelize
from services.base.nhs_oauth_service import NhsOauthService
from services.base.ssm_service import SSMService
from services.mock_pds_service import MockPdsApiService
from services.mock_virus_scan_service import MockVirusScanService
from services.patient_search_service import PatientSearch
from services.pds_api_service import PdsApiService
from services.virus_scan_result_service import VirusScanService
from utils.exceptions import InvalidNhsNumberException

DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def validate_nhs_number(nhs_number: str) -> bool:
    """
    Validate an NHS number using the Modulus 11 algorithm.
    https://www.datadictionary.nhs.uk/attributes/nhs_number.html
    """
    nhs_number = re.sub(r"\D", "", nhs_number)

    if not re.fullmatch(r"\d{10}", nhs_number):
        raise InvalidNhsNumberException("Invalid NHS number length")

    digits = [int(digit) for digit in nhs_number]
    check_digit = digits.pop()

    weights = list(range(10, 1, -1))
    total = sum(w * d for w, d in zip(weights, digits))
    remainder = total % 11
    calculated_check_digit = 11 - remainder

    if calculated_check_digit == 11:
        calculated_check_digit = 0

    if check_digit != calculated_check_digit:
        raise InvalidNhsNumberException("Invalid NHS number format")

    return True


def camelize_dict(data: dict) -> dict:
    """
    Reformat a dictionary so it's keys are returned as camelcase suitable for JSON response
        :param data: dict to reformat

    example usage:
        values = {"FileName": "test", "VirusScannerResult": "test"}
        result = camelize_dict(values)

    result:
        {"fileName": "test", "virusScannerResult": "test"}
    """
    camelized_data = {}
    for key, value in data.items():
        camelized_data[camelize(key, uppercase_first_letter=False)] = value
    return camelized_data


def create_reference_id() -> str:
    return str(uuid.uuid4())


def get_pds_service() -> PatientSearch:
    if os.getenv("PDS_FHIR_IS_STUBBED") in ["False", "false"]:
        ssm_service = SSMService()
        auth_service = NhsOauthService(ssm_service)
        return PdsApiService(ssm_service, auth_service)
    else:
        return MockPdsApiService(
            always_pass_mock=os.getenv("BYPASS_PDS", "false").lower() == "true"
        )


def get_virus_scan_service():
    if os.getenv("VIRUS_SCAN_STUB") in ["False", "false"]:
        return VirusScanService()
    else:
        return MockVirusScanService()


def redact_id_to_last_4_chars(str_id: str) -> str:
    return str_id[-4:]


def get_file_key_from_s3_url(s3_url: str) -> str:
    return urlparse(s3_url).path.lstrip("/")


def flatten(nested_list: list[list]) -> list:
    return list(itertools.chain(*nested_list))


def generate_date_folder_name(date: str) -> str:
    date_obj = datetime.strptime(date, "%Y%m%d")
    return date_obj.strftime("%Y-%m-%d")


def format_cloudfront_url(presign_url: str, cloudfront_domain: str) -> str:
    formatted_url = f"https://{cloudfront_domain}/{presign_url}"
    return formatted_url


def parse_date(date_string: str) -> datetime | None:
    if not date_string:
        return None

    SUPPORTED_FORMATS = [
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%b %d, %Y",
    ]

    for fmt in SUPPORTED_FORMATS:
        try:
            date_object = datetime.strptime(date_string, fmt)
            return date_object
        except ValueError:
            continue
    return None
