import logging
from typing import Dict, List

import requests
from models.oidc_models import AccessToken
from services.oidc_service import OidcService
from utils.exceptions import AuthorisationException
from utils.lambda_response import ApiGatewayResponse

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class OidcServiceForPassword(OidcService):
    def fetch_user_org_codes(
        self, access_token: str, selected_role: str = None
    ) -> List[str]:
        userinfo = self.fetch_userinfo(access_token)
        nrbac_roles = userinfo.get("nhsid_nrbac_roles", [])
        return [role["org_code"] for role in nrbac_roles if "org_code" in role]

    def fetch_userinfo(self, access_token: AccessToken) -> Dict:
        userinfo_response = requests.get(
            self._oidc_userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_response.status_code == 200:
            return userinfo_response.json()
        else:
            logger.error(
                f"Got error response from OIDC provider: {userinfo_response.status_code} "
                f"{userinfo_response.content}"
            )
            raise AuthorisationException("Failed to retrieve userinfo")


def response_400_bad_request_for_missing_parameter():
    return ApiGatewayResponse(
        400, "Please supply an authorisation code and state", "GET"
    ).create_api_gateway_response()
