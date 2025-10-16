import { useEffect } from 'react';
import { useSessionContext } from '../../providers/sessionProvider/SessionProvider';
import { routes } from '../../types/generic/routes';
import { useNavigate } from 'react-router-dom';
import Spinner from '../../components/generic/spinner/Spinner';
import { isMock } from '../../helpers/utils/isLocal';
import { AxiosError } from 'axios';
import useBaseAPIHeaders from '../../helpers/hooks/useBaseAPIHeaders';
import logout, { Args } from '../../helpers/requests/logout';
import useBaseAPIUrl from '../../helpers/hooks/useBaseAPIUrl';

const LogoutPage = (): React.JSX.Element => {
    const baseUrl = useBaseAPIUrl();
    const [, setSession] = useSessionContext();
    const navigate = useNavigate();
    const baseHeaders = useBaseAPIHeaders();

    useEffect(() => {
        const args: Args = { baseUrl, baseHeaders };

        const onSuccess = (): void => {
            setSession({
                auth: null,
                isLoggedIn: false,
            });
            navigate(routes.START);
        };

        const handleCallback = async (args: Args): Promise<void> => {
            try {
                await logout(args);
                onSuccess();
            } catch (e) {
                const error = e as AxiosError;
                if (isMock(error)) {
                    onSuccess();
                } else {
                    navigate(-1);
                }
            }
        };

        handleCallback(args);
    }, [baseUrl, setSession, navigate, baseHeaders]);

    return <Spinner status="Signing out..." />;
};

export default LogoutPage;
