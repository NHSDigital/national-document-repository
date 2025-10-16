import { useSessionContext } from '../../providers/sessionProvider/SessionProvider';
import { AuthHeaders } from '../../types/blocks/authHeaders';

const useBaseAPIHeaders = (authHeaderName = 'Authorization'): AuthHeaders => {
    const [session] = useSessionContext();
    const jwtToken = session.auth?.authorisation_token ?? '';
    const headers: AuthHeaders = {
        'Content-Type': 'application/json',
        [authHeaderName]: jwtToken,
    };
    return headers;
};

export default useBaseAPIHeaders;
