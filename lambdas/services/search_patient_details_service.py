from enums.feature_flags import FeatureFlags
from enums.lambda_error import LambdaError
from enums.repository_role import RepositoryRole
from pydantic import ValidationError
from pydantic_core import PydanticSerializationError
from services.feature_flags_service import FeatureFlagService
from services.manage_user_session_access import ManageUserSessionAccess
from utils.audit_logging_setup import LoggingService
from utils.exceptions import (
    InvalidResourceIdException,
    PatientNotFoundException,
    PdsErrorException,
    UserNotAuthorisedException,
)
from utils.lambda_exceptions import SearchPatientException
from utils.ods_utils import is_ods_code_active
from utils.utilities import get_pds_service

logger = LoggingService(__name__)


class SearchPatientDetailsService:
    def __init__(self, user_role, user_ods_code):
        self.user_role = user_role
        self.user_ods_code = user_ods_code
        self.manage_user_session_service = ManageUserSessionAccess()
        self.feature_flag_service = FeatureFlagService()

    def handle_search_patient_request(self, nhs_number, update_session=True):
        """
        Handle search patient request and return patient details if authorised.

        Args:
            nhs_number: The NHS number to search for
            update_session: Flag to control whether to update the session (default: True)

        Returns:
            PatientDetails object if found and the user is authorised

        Raises:
            SearchPatientException: With appropriate error code and message
        """
        try:
            patient_details = self._fetch_patient_details(nhs_number)

            if not patient_details.deceased:
                self._check_authorization(patient_details.general_practice_ods)

            logger.info("Searched for patient details", {"Result": "Patient found"})

            if update_session:
                self._update_session(nhs_number, patient_details.deceased)

            # Return the patient details object directly
            return patient_details

        except PatientNotFoundException as e:
            self._handle_error(
                e, LambdaError.SearchPatientNoPDS, 404, "Patient not found"
            )
            return None

        except UserNotAuthorisedException as e:
            self._handle_error(
                e,
                LambdaError.SearchPatientNoAuth,
                404,
                "Patient found, User not authorised to view patient",
            )
            return None

        except (InvalidResourceIdException, PdsErrorException) as e:
            self._handle_error(
                e, LambdaError.SearchPatientNoId, 400, "Patient not found"
            )
            return None

        except (ValidationError, PydanticSerializationError) as e:
            self._handle_error(
                e, LambdaError.SearchPatientNoParse, 400, "Patient not found"
            )
            return None

    def _fetch_patient_details(self, nhs_number):
        """Fetch patient details from PDS service"""
        pds_service = get_pds_service()
        return pds_service.fetch_patient_details(nhs_number)

    def _check_authorization(self, gp_ods_for_patient):
        """
        Check if the current user is authorised to view the patient details.

        Args:
            gp_ods_for_patient: The ODS code of the patient's GP practice

        Raises:
            UserNotAuthorisedException: If the user is not authorised
        """
        patient_is_active = is_ods_code_active(gp_ods_for_patient)
        is_arf_journey_on = self._is_arf_upload_enabled()

        match self.user_role:
            case RepositoryRole.GP_ADMIN.value:
                if patient_is_active and gp_ods_for_patient != self.user_ods_code:
                    raise UserNotAuthorisedException
                elif not patient_is_active and not is_arf_journey_on:
                    raise UserNotAuthorisedException

            case RepositoryRole.GP_CLINICAL.value:
                if not patient_is_active or gp_ods_for_patient != self.user_ods_code:
                    raise UserNotAuthorisedException

            case RepositoryRole.PCSE.value:
                if patient_is_active:
                    raise UserNotAuthorisedException

            case _:
                raise UserNotAuthorisedException

    def _is_arf_upload_enabled(self):
        """Check if ARF upload workflow is enabled via feature flags"""
        upload_flag_name = FeatureFlags.UPLOAD_ARF_WORKFLOW_ENABLED.value
        upload_lambda_enabled_flag_object = (
            self.feature_flag_service.get_feature_flags_by_flag(upload_flag_name)
        )
        return upload_lambda_enabled_flag_object[upload_flag_name]

    def _update_session(self, nhs_number, is_deceased):
        """Update the user session with permitted search information"""
        self.manage_user_session_service.update_auth_session_with_permitted_search(
            user_role=self.user_role,
            nhs_number=nhs_number,
            write_to_deceased_column=is_deceased,
        )

    def _handle_error(self, exception, error_code, status_code, result_message):
        """
        Handle error logging and raise the appropriate exception

        Args:
            exception: The caught exception
            error_code: Lambda error code to use
            status_code: HTTP status code to use
            result_message: Message to log as a result

        Raises:
            SearchPatientException: With appropriate error details
        """
        logger.error(
            f"{error_code.to_str()}: {str(exception)}",
            {"Result": result_message},
        )
        raise SearchPatientException(status_code, error_code)
