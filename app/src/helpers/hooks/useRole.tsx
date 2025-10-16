import { useSessionContext } from '../../providers/sessionProvider/SessionProvider';
import { REPOSITORY_ROLE } from '../../types/generic/authRole';

const useRole = (): REPOSITORY_ROLE | null => {
    const [session] = useSessionContext();

    const role = session.auth ? session.auth.role : null;
    return role;
};

export default useRole;
