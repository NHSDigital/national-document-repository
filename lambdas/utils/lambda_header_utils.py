from typing import Optional

from enums.mtls import MtlsCommonNames


def validate_common_name_in_mtls(headers: dict) -> Optional[MtlsCommonNames]:
    subject = headers.get("x-amzn-mtls-clientcert-subject", "")
    if "CN=" not in subject:
        return None

    for part in subject.split(","):
        if part.strip().startswith("CN="):
            cn_value = part.strip().split("=", 1)[1].lower()
            return MtlsCommonNames.from_common_name(cn_value)
