import React, { MouseEvent, useState } from 'react';
import { endpoints } from '../../types/generic/endpoints';
import Spinner from '../../components/generic/spinner/Spinner';
import { Link } from 'react-router-dom';
import useBaseAPIUrl from '../../helpers/hooks/useBaseAPIUrl';
import ServiceDeskLink from '../../components/generic/serviceDeskLink/ServiceDeskLink';

const AuthErrorPage = () => {
    const baseAPIUrl = useBaseAPIUrl();
    const [isLoading, setIsLoading] = useState(false);

    const handleLogin = (e: MouseEvent<HTMLAnchorElement>) => {
        setIsLoading(true);
        e.preventDefault();
        window.location.replace(`${baseAPIUrl}${endpoints.LOGIN}`);
    };
    return !isLoading ? (
        <>
            <h1>You have been logged out</h1>
            <p>
                If you were entering information, it has not been saved and you will need to
                re-enter it.
            </p>
            <p>
                If the issue persists please contact the <ServiceDeskLink />.
            </p>
            <Link to="" onClick={handleLogin}>
                Log in
            </Link>
        </>
    ) : (
        <Spinner status="Logging in..." />
    );
};
export default AuthErrorPage;
