import time

from enums.repository_role import RepositoryRole
from services.manage_user_session_access import ManageUserSessionAccess
from services.token_service import TokenService
from utils.audit_logging_setup import LoggingService
from utils.exceptions import AuthorisationException
from utils.request_context import request_context
from utils.utilities import redact_id_to_last_4_chars

logger = LoggingService(__name__)

token_service = TokenService()


class AuthoriserService:
    def __init__(self):
        self.redact_session_id = ""
        self.allowed_nhs_numbers = []
        self.deceased_nhs_numbers = []
        self.manage_user_session_service = ManageUserSessionAccess()

    def auth_request(
        self, path, ssm_jwt_public_key_parameter, auth_token, nhs_number: str = None
    ):
        try:
            decoded_token = token_service.get_public_key_and_decode_auth_token(
                auth_token=auth_token,
                ssm_public_key_parameter=ssm_jwt_public_key_parameter,
            )
            if decoded_token is None:
                raise AuthorisationException("Error while decoding JWT")
            request_context.authorization = decoded_token

            ndr_session_id = decoded_token.get("ndr_session_id")
            self.redact_session_id = redact_id_to_last_4_chars(ndr_session_id)
            user_role = decoded_token.get("repository_role")

            current_session = self.manage_user_session_service.find_login_session(
                ndr_session_id
            )
            self.allowed_nhs_numbers = (
                current_session.get("AllowedNHSNumbers", "").split(",")
                if current_session.get("AllowedNHSNumbers")
                else []
            )
            self.deceased_nhs_numbers = (
                current_session.get("DeceasedNHSNumbers", "").split(",")
                if current_session.get("DeceasedNHSNumbers")
                else []
            )

            self.validate_login_session(float(current_session["TimeToExist"]))

            resource_denied = self.deny_access_policy(path, user_role, nhs_number)

            allow_policy = False

            if not resource_denied:
                accepted_roles = RepositoryRole.list()
                if user_role in accepted_roles:
                    allow_policy = True
            return allow_policy

        except (KeyError, IndexError) as e:
            raise AuthorisationException(e)

    def deny_access_policy(self, path, user_role, nhs_number: str = None):
        logger.info(f"Path: {path}")

        patient_access_is_allowed = (
            nhs_number in self.allowed_nhs_numbers if nhs_number else False
        )
        access_to_deceased_patient = (
            nhs_number in self.deceased_nhs_numbers if nhs_number else False
        )

        is_user_gp_admin = user_role == RepositoryRole.GP_ADMIN.value
        is_user_gp_clinical = user_role == RepositoryRole.GP_CLINICAL.value
        is_user_pcse = user_role == RepositoryRole.PCSE.value

        match path:
            case "/AccessAudit":
                deny_resource = not access_to_deceased_patient

            case "/DocumentDelete":
                deny_resource = not patient_access_is_allowed or is_user_gp_clinical

            case "/DocumentManifest":
                deny_resource = not patient_access_is_allowed or is_user_gp_clinical

            case "/DocumentReference":
                deny_resource = True
                if (
                    is_user_gp_admin or is_user_gp_clinical
                ) and patient_access_is_allowed:
                    deny_resource = False
                if patient_access_is_allowed and access_to_deceased_patient:
                    deny_resource = True

            case "/LloydGeorgeStitch":
                deny_resource = not patient_access_is_allowed or is_user_pcse

            case "/OdsReport":
                deny_resource = False

            case "/SearchPatient":
                deny_resource = False

            case "/FeatureFlags":
                deny_resource = False

            case "/Feedback":
                deny_resource = False

            case "/DocumentStatus":
                deny_resource = (
                    not patient_access_is_allowed or is_user_gp_clinical or is_user_pcse
                )

            case "/UploadState":
                deny_resource = (
                    not patient_access_is_allowed or is_user_gp_clinical or is_user_pcse
                )

            case "/VirusScan":
                deny_resource = (
                    not patient_access_is_allowed or is_user_gp_clinical or is_user_pcse
                )

            case _:
                deny_resource = not patient_access_is_allowed

        logger.info("Allow resource: %s" % (not deny_resource))

        return bool(deny_resource)

    def validate_login_session(self, session_expiry_time: float):
        time_now = time.time()
        if session_expiry_time <= time_now:
            raise AuthorisationException(
                f"The session is already expired for session ID ending in: {self.redact_session_id}",
            )
