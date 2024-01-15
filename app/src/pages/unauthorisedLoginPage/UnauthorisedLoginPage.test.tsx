import { render, screen, waitFor } from '@testing-library/react';
import { LinkProps } from 'react-router-dom';
import { act } from 'react-dom/test-utils';
import userEvent from '@testing-library/user-event';
import { routes } from '../../types/generic/routes';
import UnauthorisedLoginPage from './UnauthorisedLoginPage';

const mockedUseNavigate = jest.fn();
jest.mock('react-router', () => ({
    useNavigate: () => mockedUseNavigate,
}));
jest.mock('../../helpers/hooks/useBaseAPIUrl');
jest.mock('react-router-dom', () => ({
    __esModule: true,
    Link: (props: LinkProps) => <a {...props} role="link" />,
}));

describe('UnauthorisedPage', () => {
    describe('Rendering', () => {
        it('renders unauthorised message', () => {
            render(<UnauthorisedLoginPage />);
            expect(screen.getByText('Your account cannot access this service')).toBeInTheDocument();
        });

        it('renders a return home button', () => {
            render(<UnauthorisedLoginPage />);
            expect(
                screen.getByRole('button', {
                    name: 'Return to start page',
                }),
            ).toBeInTheDocument();
        });
    });

    describe('Navigation', () => {
        it('navigates user to home page when return home is clicked', async () => {
            render(<UnauthorisedLoginPage />);
            const returnHomeLink = screen.getByRole('button', {
                name: 'Return to start page',
            });
            expect(returnHomeLink).toBeInTheDocument();
            act(() => {
                userEvent.click(returnHomeLink);
            });

            await waitFor(() => {
                expect(mockedUseNavigate).toHaveBeenCalledWith(routes.START);
            });
        });
    });
});
