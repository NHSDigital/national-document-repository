import React, { MouseEvent, useState } from 'react';
import { routes } from '../../types/generic/routes';
import { Link, useNavigate } from 'react-router-dom';
import { endpoints } from '../../types/generic/endpoints';
import Spinner from '../../components/generic/spinner/Spinner';
import useBaseAPIUrl from '../../helpers/hooks/useBaseAPIUrl';
import useTitle from '../../helpers/hooks/useTitle';

const UnauthorisedPage = (): React.JSX.Element => {
    const baseAPIUrl = useBaseAPIUrl();
    const [isLoading, setIsLoading] = useState(false);
    const navigate = useNavigate();

    const handleLogin = (e: MouseEvent<HTMLAnchorElement>): void => {
        setIsLoading(true);
        e.preventDefault();
        window.location.replace(`${baseAPIUrl}${endpoints.LOGIN}`);
    };

    const pageHeader = 'Unauthorised access';
    useTitle({ pageTitle: pageHeader });

    return !isLoading ? (
        <>
            <h1>{pageHeader}</h1>
            <p>
                The page you were looking for could not be accessed. If you have the permissions,{' '}
                <Link to="" onClick={handleLogin}>
                    signing in
                </Link>{' '}
                may fix this.
            </p>
            <Link
                to="#"
                onClick={(e): void => {
                    e.preventDefault();
                    navigate(routes.START);
                }}
            >
                Return home
            </Link>
        </>
    ) : (
        <Spinner status="Signing in..." />
    );
};

export default UnauthorisedPage;
