from typing import Optional

from enums.mtls import MtlsCommonNames


def validate_common_name_in_mtls(request_context: dict) -> Optional[MtlsCommonNames]:
    client_cert = request_context.get("identity", {}).get("clientCert", {})
    subject = client_cert.get("subjectDN", "")
    if "CN=" not in subject:
        return None

    for part in subject.split(","):
        if part.strip().startswith("CN="):
            cn_value = part.strip().split("=", 1)[1].lower()
            return MtlsCommonNames.from_common_name(cn_value)
