import { routes } from '../../types/generic/routes';
import { useNavigate, useLocation } from 'react-router-dom';
import { ButtonLink } from 'nhsuk-react-components';
import useTitle from '../../helpers/hooks/useTitle';

const UnauthorisedLoginPage = (): React.JSX.Element => {
    const navigate = useNavigate();
    const pageHeader = 'Your account cannot access this service';
    const location = useLocation();
    const errorData = location.state?.errorData;
    useTitle({ pageTitle: 'Unauthorised account' });

    const gpAdminRoles = errorData.roles[0].split(',').join(', ');
    const gpClinicalRoles = errorData.roles[1].split(',').join(', ');

    return (
        <>
            <h1>{pageHeader}</h1>
            <p>
                Your account does not have authorisation to view or manage patient records using
                this service.
            </p>
            <h2>Who can access this service</h2>
            <p>
                In order to keep patient information safe, only authorised accounts can access this
                service
            </p>
            <p>This includes:</p>
            <ul>
                <li>
                    GP practice staff who work at the practice the patient is registered with who
                    have one of these roles on their smart cards:
                    <br />
                    <br />
                    <p>
                        <strong>GP Admin Role:</strong> {gpAdminRoles}
                    </p>
                    <p>
                        <strong>GP Clinical Role:</strong> {gpClinicalRoles}
                    </p>
                </li>
                <li>PCSE staff where a patient does not have an active registration</li>
            </ul>
            <p>
                If you don't have access and feel you should have, please contact your local
                Registration Authority
            </p>
            <ButtonLink
                href="#"
                onClick={(e): void => {
                    e.preventDefault();
                    navigate(routes.START);
                }}
            >
                Return to start page
            </ButtonLink>
        </>
    );
};
export default UnauthorisedLoginPage;
