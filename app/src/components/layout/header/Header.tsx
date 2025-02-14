import React from 'react';
import { Header as NhsHeader } from 'nhsuk-react-components';
import { routes } from '../../../types/generic/routes';
import { useNavigate } from 'react-router-dom';
import NavLinks from '../navLinks/NavLinks';
import useRole from '../../../helpers/hooks/useRole';

const Header = () => {
    const role = useRole();
    const navigateHome = () => {
        navigate(role ? routes.HOME : routes.START);
    };
    const navigate = useNavigate();
    return (
        <NhsHeader transactional>
            <NhsHeader.Container>
                <NhsHeader.Logo onClick={navigateHome} className="clickable" />
                <NhsHeader.ServiceName onClick={navigateHome} className="clickable">
                    Access and store digital patient documents
                </NhsHeader.ServiceName>
            </NhsHeader.Container>

            <NavLinks />
        </NhsHeader>
    );
};

export default Header;
