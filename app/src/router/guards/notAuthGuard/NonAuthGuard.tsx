import { useEffect, type ReactNode } from 'react';
import { useSessionContext } from '../../../providers/sessionProvider/SessionProvider';
import { routes } from '../../../types/generic/routes';
import { useNavigate } from 'react-router-dom';
type Props = {
    children: ReactNode;
    redirectRoute: routes;
};

const NonAuthGuard = ({ children, redirectRoute }: Props): React.JSX.Element => {
    const [session] = useSessionContext();
    const navigate = useNavigate();

    useEffect(() => {
        if (session.isLoggedIn) {
            navigate(redirectRoute);
        }
    }, [session, navigate, redirectRoute]);

    return <>{children}</>;
};

export default NonAuthGuard;
