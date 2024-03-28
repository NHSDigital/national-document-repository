import React from 'react';
import type { MouseEvent as ReactEvent } from 'react';
import { Header } from 'nhsuk-react-components';
import { useNavigate } from 'react-router';
import { routes } from '../../../types/generic/routes';
import { useSessionContext } from '../../../providers/sessionProvider/SessionProvider';

const NavLinks = () => {
    const navigate = useNavigate();
    const [session] = useSessionContext();

    const nav = (e: ReactEvent<HTMLAnchorElement, MouseEvent>, link: string) => {
        e.preventDefault();
        navigate(link);
    };

    return session.isLoggedIn ? (
        <Header.Nav>
            <Header.NavItem
                role="link"
                className="clickable"
                onClick={(e) => nav(e, routes.HOME)}
                tabIndex={0}
                href="#"
            >
                Home
            </Header.NavItem>
            <Header.NavItem
                role="link"
                className="clickable"
                data-testid="logout-btn"
                onClick={(e) => nav(e, routes.LOGOUT)}
                tabIndex={0}
                href="#"
            >
                Log Out
            </Header.NavItem>
        </Header.Nav>
    ) : null;
};

export default NavLinks;
