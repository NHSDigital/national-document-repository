from enums.patient_ods_inactive_status import PatientOdsInactiveStatus

"""
On PDS, GP ODS codes must be 6 characters long, see the 'epraccur' document here for info:
https://digital.nhs.uk/services/organisation-data-service/export-data-files/csv-downloads/gp-and-gp-practice-related-data

Sometimes, a patient will not have a generalPractitioner on PDS. Internally, we can also add codes to mark inactive
patients for reporting purposes. The only values that should be considered 'active' are valid ODS codes.
"""
PCSE_ODS_CODE = "8JD29"


def is_ods_code_active(gp_ods) -> bool:
    if gp_ods in PatientOdsInactiveStatus.list():
        return False

    return len(gp_ods or "") == 6


def extract_ods_role_code_with_r_prefix_from_role_codes_string(role_codes) -> str:
    for role_code in role_codes.split(":"):
        if role_code.startswith("R"):
            return role_code
