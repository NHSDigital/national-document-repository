import { render, screen } from '@testing-library/react';
import DocumentUploadInfectedStage from './DocumentUploadInfectedStage';
import userEvent from '@testing-library/user-event';
import { routes } from '../../../../types/generic/routes';
import { runAxeTest } from '../../../../helpers/test/axeTestHelper';
import { describe, expect, it, Mock, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

const mockedUseNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return {
        ...actual,
        useNavigate: (): Mock => mockedUseNavigate,
    };
});

describe('DocumentUploadInfectedStage', () => {
    describe('Rendering', () => {
        it('renders infected warning when document has infected status', () => {
            const contentStrings = [
                'Warning: we found a virus in your files',
                'One or more of your files has a virus.',
                "To keep patient information safe and our systems secure, we've stopped the upload.",
                'Contact your local IT support desk for help immediately. Do not attempt to upload the files again until they have been made safe.',
                'Go to home',
            ];

            render(
                <MemoryRouter>
                    <DocumentUploadInfectedStage />
                </MemoryRouter>,
            );

            contentStrings.forEach((s) => {
                const st = new RegExp(s, 'i');
                expect(screen.getByText(st)).toBeInTheDocument();
            });

            expect(
                screen.getByRole('button', {
                    name: 'Go to home',
                }),
            ).toBeInTheDocument();
        });
    });

    describe('Accessibility', () => {
        it('pass accessibility checks', async () => {
            render(
                <MemoryRouter>
                    <DocumentUploadInfectedStage />
                </MemoryRouter>,
            );
            const results = await runAxeTest(document.body);
            expect(results).toHaveNoViolations();
        });
    });

    describe('Navigation', () => {
        it('navigates to home page when button is clicked', async () => {
            render(
                <MemoryRouter>
                    <DocumentUploadInfectedStage />
                </MemoryRouter>,
            );

            const homeButton = screen.getByRole('button', {
                name: 'Go to home',
            });
            expect(homeButton).toBeInTheDocument();

            await userEvent.click(homeButton);

            expect(mockedUseNavigate).toHaveBeenCalledWith(routes.HOME, {
                replace: true,
            });
        });
    });
});
