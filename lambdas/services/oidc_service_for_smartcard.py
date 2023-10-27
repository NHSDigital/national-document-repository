import logging
from typing import Dict, List

import requests
from models.oidc_models import AccessToken

from services.oidc_service import OidcService
from utils.exceptions import AuthorisationException

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class OidcServiceForSmartcard(OidcService):
    def fetch_user_org_codes(self, access_token: str, id_token_claim_set) -> List[str]:
        userinfo = self.fetch_userinfo(access_token)
        nrbac_roles = userinfo.get("nhsid_nrbac_roles", [])
        selected_role = get_selected_roleid(id_token_claim_set)

        logger.info(f"Selected role ID: {nrbac_roles}")
        logger.info(f"Selected role ID: {selected_role}")

        for role in nrbac_roles:
            if role["person_roleid"] == selected_role:
                return role["org_code"]
        return []

    def fetch_userinfo(self, access_token: AccessToken) -> Dict:
        userinfo_response = requests.get(
            self._oidc_userinfo_url,
            headers={
                "Authorization": f"Bearer {access_token}, scope nationalrbacaccess"
            },
            # see if setting scope is actually needed
        )
        if userinfo_response.status_code == 200:
            return userinfo_response.json()
        else:
            logger.error(
                f"Got error response from OIDC provider: {userinfo_response.status_code} "
                f"{userinfo_response.content}"
            )
            raise AuthorisationException("Failed to retrieve userinfo")


@staticmethod
def get_selected_roleid(id_token_claim_set):
    return id_token_claim_set.selected_roleid
