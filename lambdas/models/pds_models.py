from datetime import date
from typing import Optional, Tuple

from enums.death_notification_status import DeathNotificationStatus
from enums.patient_ods_inactive_status import PatientOdsInactiveStatus
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from utils.audit_logging_setup import LoggingService
from utils.ods_utils import is_ods_code_active

logger = LoggingService(__name__)
conf = ConfigDict(alias_generator=to_camel)


class Period(BaseModel):
    start: date
    end: Optional[date] = None


class Address(BaseModel):
    model_config = conf

    use: str
    period: Optional[Period] = None
    postal_code: str = ""


class Name(BaseModel):
    use: str
    period: Optional[Period] = None
    given: Optional[list[str]] = []
    family: str

    def is_currently_in_use(self) -> bool:
        if not self.period:
            return False
        if self.use.lower() in ["nickname", "old"]:
            return False

        today = date.today()

        name_started_already = self.period.start <= today
        name_not_expired_yet = (not self.period.end) or self.period.end >= today

        return name_started_already and name_not_expired_yet


class Security(BaseModel):
    code: str
    display: str


class Meta(BaseModel):
    versionId: str
    security: list[Security]


class GPIdentifier(BaseModel):
    system: str = ""
    value: str
    period: Optional[Period] = None


class GeneralPractitioner(BaseModel):
    id: str = ""
    type: str = ""
    identifier: GPIdentifier


class Extension(BaseModel):
    url: str
    extension: list[dict] = []


class PatientDetails(BaseModel):
    model_config = conf

    given_name: Optional[list[str]] = None
    family_name: str = ""
    birth_date: Optional[date] = None
    postal_code: str = ""
    nhs_number: str
    superseded: bool
    restricted: bool
    general_practice_ods: str = ""
    active: Optional[bool] = None
    deceased: bool = False
    death_notification_status: Optional[DeathNotificationStatus] = None


class Patient(BaseModel):
    model_config = conf

    id: str
    birth_date: Optional[date] = None
    address: list[Address] = []
    name: list[Name]
    meta: Meta
    general_practitioner: list[GeneralPractitioner] = []
    deceased_date_time: str = ""
    extension: list[Extension] = []

    def get_security(self) -> Security:
        security = self.meta.security[0] if self.meta.security[0] else None
        if not security:
            raise ValueError("No valid security found in patient meta")

        return security

    def is_unrestricted(self) -> bool:
        security = self.get_security()
        return security.code == "U"

    def get_usual_name(self) -> Optional[Name]:
        for entry in self.name:
            if entry.use.lower() == "usual":
                return entry

    def get_names_by_start_date(self) -> [Name]:
        sorted_by_start_date_desc = sorted(
            self.name,
            key=lambda name: (
                (1, name.period.start, name.use.lower() == "usual")
                if name.period and name.period.start is not None
                else (0, 0, name.use.lower() == "usual")
            ),
            reverse=True,
        )
        return sorted_by_start_date_desc

    def get_current_family_name_and_given_name(self) -> Tuple[str, list[str]]:
        ordered_names = self.get_names_by_start_date()
        if not ordered_names:
            logger.warning(
                "The patient does not have a currently active name or a usual name."
            )
            return "", [""]

        given_name = ordered_names[0].given
        family_name = ordered_names[0].family

        if not given_name or given_name == [""]:
            logger.warning("The given name of patient is empty.")

        return family_name, given_name

    def get_current_home_address(self) -> Optional[Address]:
        if self.is_unrestricted() and self.address:
            for entry in self.address:
                if entry.use.lower() == "home":
                    return entry

    def get_ods_code_or_inactive_status_for_gp(self) -> str:
        return (
            PatientOdsInactiveStatus.RESTRICTED
            if not self.is_unrestricted()
            else self.get_active_ods_code_for_gp()
            or self.get_status_for_inactive_patient()
        )

    def get_active_ods_code_for_gp(self) -> str:
        for entry in self.general_practitioner:
            period = entry.identifier.period
            if not period:
                continue
            gp_end_date = period.end
            if not gp_end_date or gp_end_date >= date.today():
                return entry.identifier.value

    def get_status_for_inactive_patient(self) -> str:
        if is_formally_deceased(self.get_death_notification_status()):
            return PatientOdsInactiveStatus.DECEASED
        else:
            return PatientOdsInactiveStatus.SUSPENDED

    def get_is_active_status(self) -> bool:
        gp_ods = self.get_ods_code_or_inactive_status_for_gp()
        return is_ods_code_active(gp_ods)

    def get_death_notification_status(self) -> Optional[DeathNotificationStatus]:
        if not self.deceased_date_time:
            return None

        for extension_wrapper in self.extension:
            if (
                extension_wrapper.url
                == "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-DeathNotificationStatus"
            ):
                return self.parse_death_notification_status_extension(extension_wrapper)

        return None

    @staticmethod
    def parse_death_notification_status_extension(
        extension_wrapper: Extension,
    ) -> Optional[DeathNotificationStatus]:
        try:
            for nested_extension in extension_wrapper.extension:
                if nested_extension["url"] == "deathNotificationStatus":
                    status_code = nested_extension["valueCodeableConcept"]["coding"][0][
                        "code"
                    ]
                    return DeathNotificationStatus(status_code)

        except (KeyError, IndexError, ValueError) as e:
            logger.info(
                f"Failed to parse death_notification_status for patient due to error: {str(e)}. "
                "Will fill the value as None."
            )
        return None

    def get_patient_details(self, nhs_number) -> PatientDetails:
        family_name, given_name = self.get_current_family_name_and_given_name()
        current_home_address = self.get_current_home_address()
        death_notification_status = self.get_death_notification_status()

        patient_details = PatientDetails(
            givenName=given_name,
            familyName=family_name,
            birthDate=self.birth_date,
            postalCode=(
                current_home_address.postal_code if current_home_address else ""
            ),
            nhsNumber=self.id,
            superseded=bool(nhs_number == id),
            restricted=not self.is_unrestricted(),
            generalPracticeOds=self.get_ods_code_or_inactive_status_for_gp(),
            active=self.get_is_active_status(),
            deceased=is_formally_deceased(death_notification_status),
            deathNotificationStatus=death_notification_status,
        )

        return patient_details

    def get_minimum_patient_details(self, nhs_number) -> PatientDetails:
        family_name, given_name = self.get_current_family_name_and_given_name()
        death_notification_status = self.get_death_notification_status()

        return PatientDetails(
            givenName=given_name,
            familyName=family_name,
            birthDate=self.birth_date,
            generalPracticeOds=self.get_ods_code_or_inactive_status_for_gp(),
            nhsNumber=self.id,
            superseded=bool(nhs_number == id),
            restricted=not self.is_unrestricted(),
            deceased=is_formally_deceased(death_notification_status),
            deathNotificationStatus=death_notification_status,
        )


def is_formally_deceased(
    death_notification_status: Optional[DeathNotificationStatus],
) -> bool:
    return death_notification_status == DeathNotificationStatus.FORMAL
