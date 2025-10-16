import { routes } from '../../types/generic/routes';
import { Link } from 'react-router-dom';
import useTitle from '../../helpers/hooks/useTitle';

const NotFoundPage = (): React.JSX.Element => {
    const pageHeader = 'Page not found';
    useTitle({ pageTitle: pageHeader });

    return (
        <>
            <h1>{pageHeader}</h1>
            <p>
                The page you were looking for could not be found. It might not exist, or you do not
                have access to it.
            </p>
            <Link to={routes.HOME}>Return home</Link>
        </>
    );
};

export default NotFoundPage;
