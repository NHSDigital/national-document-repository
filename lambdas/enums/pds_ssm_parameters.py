from enum import Enum


class SSMParameter(Enum):
    PDS_KID = "/prs/dev/user-input/pds-fhir-kid"
    NHS_OAUTH_KEY = "/prs/dev/user-input/nhs-api-key"
    PDS_API_KEY = "/prs/dev/user-input/pds-fhir-private-key"
    NHS_OAUTH_ENDPOINT = "/prs/dev/user-input/nhs-oauth-endpoint"
    PDS_API_ENDPOINT = "/prs/dev/user-input/pds-fhir-endpoint"
    PDS_API_ACCESS_TOKEN = "/prs/dev-ndr/pds-fhir-access-token"
    GP_ODS_CODE = "/ndr/GP_ODS_code"
    VIRUS_API_USER = "/VirusScanner/dev/API_USERNAME"
    VIRUS_API_PASSWORD = "/VirusScanner/dev/API_PASSWORD"
    VIRUS_API_ACCESSTOKEN = "/VirusScanner/dev/API_ACCESSTOKEN"
    VIRUS_API_BASEURL = "/VirusScanner/dev/API_BASEURL"
