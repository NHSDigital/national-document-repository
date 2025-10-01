from enum import Enum
from typing import Optional

from pydantic import BaseModel


class SnomedCode(BaseModel):
    code: str
    display_name: str


class SnomedCodes(Enum):
    LLOYD_GEORGE = SnomedCode(
        code="16521000000101", display_name="Lloyd George record folder"
    )
    CARE_PLAN = SnomedCode(code="734163000", display_name="Care plan")
    GENERAL_MEDICAL_PRACTICE = SnomedCode(
        code="1060971000000108", display_name="General practice service"
    )
    # Temporary snomed code used.
    PATIENT_DATA = SnomedCode(
        code="717391000000106", display_name="Confidential patient data"
    )

    @classmethod
    def find_by_code(cls, code: str) -> Optional["SnomedCode"]:
        """
        Find a SnomedCodes enum value by its code string.

        Args:
            code: The SNOMED code string to search for (e.g. "16521000000101")

        Returns:
            The matching SnomedCodes enum value or None if not found
        """
        for snomed_enum in cls:
            if snomed_enum.value.code == code:
                return snomed_enum.value
        return None
