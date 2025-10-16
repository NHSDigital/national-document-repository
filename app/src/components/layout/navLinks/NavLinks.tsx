import type { MouseEvent as ReactEvent } from 'react';
import { Header } from 'nhsuk-react-components';
import { useNavigate } from 'react-router-dom';
import { routes } from '../../../types/generic/routes';
import { useSessionContext } from '../../../providers/sessionProvider/SessionProvider';

const NavLinks = (): React.JSX.Element => {
    const navigate = useNavigate();
    const [session] = useSessionContext();
    const nav = (e: ReactEvent<HTMLAnchorElement, MouseEvent>, link: string): void => {
        e.preventDefault();
        navigate(link);
    };

    const appLinks = [
        { href: routes.HOME, label: 'Home', id: 'home-btn' },
        { href: routes.SEARCH_PATIENT, label: 'Search for a patient', id: 'search-btn' },
        { href: routes.LOGOUT, label: 'Sign out', id: 'logout-btn' },
    ];

    return session.isLoggedIn ? (
        <Header.Nav>
            {appLinks.map((l) => (
                <Header.NavItem
                    tabIndex={0}
                    href="#"
                    key={l.href}
                    role="link"
                    data-testid={l.id}
                    onClick={(e): void => nav(e, l.href)}
                >
                    {l.label}
                </Header.NavItem>
            ))}
        </Header.Nav>
    ) : (
        <></>
    );
};

export default NavLinks;
