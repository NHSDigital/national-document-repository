import { useEffect } from 'react';
import getAuthToken, { AuthTokenArgs } from '../../helpers/requests/getAuthToken';
import { useSessionContext } from '../../providers/sessionProvider/SessionProvider';
import { routes } from '../../types/generic/routes';
import { useNavigate } from 'react-router-dom';
import Spinner from '../../components/generic/spinner/Spinner';
import { isMock } from '../../helpers/utils/isLocal';
import { AxiosError } from 'axios';
import { buildUserAuth } from '../../helpers/test/testBuilders';
import { UserAuth } from '../../types/blocks/userAuth';
import useBaseAPIUrl from '../../helpers/hooks/useBaseAPIUrl';
import { REPOSITORY_ROLE } from '../../types/generic/authRole';
import { useConfigContext } from '../../providers/configProvider/ConfigProvider';
import getFeatureFlags from '../../helpers/requests/getFeatureFlags';
import { FeatureFlags, defaultFeatureFlags } from '../../types/generic/featureFlags';

const AuthCallbackPage = (): React.JSX.Element => {
    const baseUrl = useBaseAPIUrl();
    const [, setSession] = useSessionContext();
    const [{ mockLocal }, setConfig] = useConfigContext();
    const navigate = useNavigate();

    useEffect(() => {
        const handleError = (error: AxiosError): void => {
            setSession({
                auth: null,
                isLoggedIn: false,
            });
            if (error.response?.status === 401) {
                navigate(routes.UNAUTHORISED_LOGIN, { state: { errorData: error.response?.data } });
            } else {
                navigate(routes.AUTH_ERROR);
            }
        };
        const handleSuccess = (auth: UserAuth, featureFlags: FeatureFlags): void => {
            const { GP_ADMIN, GP_CLINICAL, PCSE } = REPOSITORY_ROLE;
            setSession({
                auth,
                isLoggedIn: true,
            });

            setConfig({
                mockLocal,
                featureFlags,
            });

            if ([GP_ADMIN, GP_CLINICAL, PCSE].includes(auth.role)) {
                navigate(routes.HOME);
            } else {
                navigate(routes.AUTH_ERROR);
            }
        };

        const handleCallback = async (args: AuthTokenArgs): Promise<void> => {
            try {
                const authData = await getAuthToken(args);
                const jwtToken = authData.authorisation_token ?? '';
                const featureFlagsData = await getFeatureFlags({
                    baseUrl,
                    baseHeaders: {
                        'Content-Type': 'application/json',
                        Authorization: jwtToken,
                    },
                });
                handleSuccess(authData, featureFlagsData);
            } catch (e) {
                const error = e as AxiosError;
                if (isMock(error)) {
                    const { userRole } = mockLocal;
                    const mockFeatureFlags = Object.entries(defaultFeatureFlags).reduce(
                        (acc, [k, v]) => ({
                            ...acc,
                            [k]: true,
                        }),
                        {} as FeatureFlags,
                    );
                    handleSuccess(buildUserAuth({ role: userRole }), mockFeatureFlags);
                } else {
                    handleError(error);
                }
            }
        };

        const urlSearchParams = new URLSearchParams(window.location.search);
        const code = urlSearchParams.get('code') ?? '';
        const state = urlSearchParams.get('state') ?? '';
        void handleCallback({ baseUrl, code, state });
    }, [baseUrl, setSession, navigate, mockLocal, setConfig]);

    return <Spinner status="Signing in..." />;
};

export default AuthCallbackPage;
