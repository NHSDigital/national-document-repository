import re

from enum import StrEnum, auto

CN_PATTERN = re.compile(
    r"^ndrclient\.main\.([a-z0-9-]+)\.(?P<identifier>[a-z0-9-]+)\.national\.nhs\.uk$",
    re.IGNORECASE,
)


class MtlsCommonNames(StrEnum):
    PDM = auto()
