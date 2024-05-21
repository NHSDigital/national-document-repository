import { render, screen, waitFor } from '@testing-library/react';
import DocumentSearchResultsPage from './DocumentSearchResultsPage';
import userEvent from '@testing-library/user-event';
import { buildPatientDetails, buildSearchResult } from '../../helpers/test/testBuilders';
import { routes } from '../../types/generic/routes';
import axios from 'axios';
import usePatient from '../../helpers/hooks/usePatient';
import { LinkProps } from 'react-router-dom';
import { act } from 'react-dom/test-utils';
import { runAxeTest } from '../../helpers/test/axeTestHelper';

const mockedUseNavigate = jest.fn();
jest.mock('react-router', () => ({
    useNavigate: () => mockedUseNavigate,
}));

jest.mock('react-router-dom', () => ({
    __esModule: true,
    Link: (props: LinkProps) => <a {...props} role="link" />,
    useNavigate: () => jest.fn(),
    useLocation: () => jest.fn(),
}));
jest.mock('moment', () => {
    return () => jest.requireActual('moment')('2020-01-01T00:00:00.000Z');
});
jest.mock('../../helpers/hooks/useBaseAPIHeaders');
jest.mock('axios');
jest.mock('../../helpers/hooks/usePatient');

const mockedAxios = axios as jest.Mocked<typeof axios>;
const mockedUsePatient = usePatient as jest.Mock;
const mockPatient = buildPatientDetails();

describe('<DocumentSearchResultsPage />', () => {
    beforeEach(() => {
        process.env.REACT_APP_ENVIRONMENT = 'jest';
        mockedUsePatient.mockReturnValue(mockPatient);
    });
    afterEach(() => {
        jest.clearAllMocks();
    });

    describe('Rendering', () => {
        it('renders the page after a successful response from api', async () => {
            mockedAxios.get.mockResolvedValue(async () => {
                return Promise.resolve({ data: [buildSearchResult()] });
            });

            render(<DocumentSearchResultsPage />);

            expect(
                screen.getByRole('heading', {
                    name: 'Download electronic health records and attachments',
                }),
            ).toBeInTheDocument();

            await waitFor(() => {
                expect(
                    screen.queryByRole('progressbar', { name: 'Loading...' }),
                ).not.toBeInTheDocument();
            });

            expect(screen.getByRole('link', { name: 'Start Again' })).toBeInTheDocument();
        });

        it('displays a progress bar when the document search results are being requested', async () => {
            mockedAxios.get.mockImplementation(async () => {
                await new Promise((resolve) => {
                    setTimeout(() => {
                        // To delay the mock request, and give a chance for the progress bar to appear
                        resolve(null);
                    }, 500);
                });
                return Promise.resolve({ data: [buildSearchResult()] });
            });

            render(<DocumentSearchResultsPage />);

            expect(screen.getByRole('progressbar', { name: 'Loading...' })).toBeInTheDocument();
        });

        it('displays a message when a document search returns no results', async () => {
            mockedAxios.get.mockResolvedValue(async () => {
                return Promise.resolve({ data: [] });
            });

            render(<DocumentSearchResultsPage />);

            await waitFor(() => {
                expect(
                    screen.getByText('There are no documents available for this patient.'),
                ).toBeInTheDocument();
            });

            expect(
                screen.queryByRole('button', { name: 'Download All Documents' }),
            ).not.toBeInTheDocument();
            expect(
                screen.queryByRole('button', { name: 'Delete All Documents' }),
            ).not.toBeInTheDocument();
        });

        it('displays a error messages when the call to document manifest fails', async () => {
            mockedAxios.get.mockResolvedValue({ data: [buildSearchResult()] });

            const errorResponse = {
                response: {
                    status: 403,
                    message: 'An error occurred',
                },
            };

            render(<DocumentSearchResultsPage />);

            mockedAxios.get.mockImplementation(() => Promise.reject(errorResponse));

            await waitFor(() => {
                screen.getByRole('button', { name: 'Download All Documents' });
            });
            act(() => {
                userEvent.click(screen.getByRole('button', { name: 'Download All Documents' }));
            });

            expect(
                await screen.findByText('An error has occurred while preparing your download'),
            ).toBeInTheDocument();
            expect(
                screen.getByRole('button', { name: 'Download All Documents' }),
            ).toBeInTheDocument();
            expect(
                screen.getByRole('button', { name: 'Delete All Documents' }),
            ).toBeInTheDocument();
            expect(screen.getByRole('link', { name: 'Start Again' })).toBeInTheDocument();
        });
        it('displays a error messages when the call to document manifest return 400', async () => {
            mockedAxios.get.mockResolvedValue({ data: [buildSearchResult()] });

            const errorResponse = {
                response: {
                    status: 400,
                    data: { message: 'An error occurred', err_code: 'SP_1001' },
                },
            };

            render(<DocumentSearchResultsPage />);

            mockedAxios.get.mockImplementation(() => Promise.reject(errorResponse));

            await waitFor(() => {
                screen.getByRole('button', { name: 'Download All Documents' });
            });
            act(() => {
                userEvent.click(screen.getByRole('button', { name: 'Download All Documents' }));
            });
            expect(
                await screen.findByText('An error has occurred while preparing your download'),
            ).toBeInTheDocument();
            expect(
                screen.getByRole('button', { name: 'Download All Documents' }),
            ).toBeInTheDocument();
            expect(
                screen.getByRole('button', { name: 'Delete All Documents' }),
            ).toBeInTheDocument();
            expect(screen.getByRole('link', { name: 'Start Again' })).toBeInTheDocument();
        });
    });

    describe('Accessibility', () => {
        it('pass accessibility checks at loading screen', async () => {
            mockedAxios.get.mockReturnValueOnce(
                new Promise((resolve) => setTimeout(resolve, 100000)),
            );
            render(<DocumentSearchResultsPage />);

            expect(screen.getByRole('progressbar', { name: 'Loading...' })).toBeInTheDocument();

            const results = await runAxeTest(document.body);
            expect(results).toHaveNoViolations();
        });

        it('pass accessibility checks when displaying search result', async () => {
            mockedAxios.get.mockResolvedValue({ data: [buildSearchResult()] });

            render(<DocumentSearchResultsPage />);

            expect(await screen.findByText('List of documents available')).toBeInTheDocument();

            const results = await runAxeTest(document.body);
            expect(results).toHaveNoViolations();
        });

        it('pass accessibility checks when error boxes are showing up', async () => {
            mockedAxios.get.mockResolvedValue({ data: [buildSearchResult()] });
            const errorResponse = {
                response: {
                    status: 400,
                    data: { message: 'An error occurred', err_code: 'SP_1001' },
                },
            };
            render(<DocumentSearchResultsPage />);

            const downloadButton = await screen.findByRole('button', {
                name: 'Download All Documents',
            });
            mockedAxios.get.mockImplementation(() => Promise.reject(errorResponse));
            act(() => {
                userEvent.click(downloadButton);
            });

            expect(
                await screen.findByText('Sorry, the service is currently unavailable.'),
            ).toBeInTheDocument();
            expect(
                await screen.findByText('An error has occurred while preparing your download'),
            ).toBeInTheDocument();

            const results = await runAxeTest(document.body);
            expect(results).toHaveNoViolations();
        });
    });

    describe('Navigation', () => {
        it('navigates to Start page when user clicks on start again button', async () => {
            mockedAxios.get.mockImplementation(() =>
                Promise.resolve({ data: [buildSearchResult()] }),
            );

            render(<DocumentSearchResultsPage />);

            await waitFor(() => {
                expect(screen.getByRole('link', { name: 'Start Again' })).toBeInTheDocument();
            });

            userEvent.click(screen.getByRole('link', { name: 'Start Again' }));

            await waitFor(() => {
                expect(mockedUseNavigate).toHaveBeenCalledWith(routes.START);
            });
        });
        it('navigates to Error page when call to doc manifest return 500', async () => {
            mockedAxios.get.mockResolvedValue({ data: [buildSearchResult()] });
            const errorResponse = {
                response: {
                    status: 500,
                    data: { message: 'An error occurred', err_code: 'SP_1001' },
                },
            };
            mockedAxios.get.mockImplementation(() => Promise.reject(errorResponse));

            act(() => {
                render(<DocumentSearchResultsPage />);
            });

            await waitFor(() => {
                expect(screen.queryByRole('link', { name: 'Start Again' })).not.toBeInTheDocument();
            });

            await waitFor(() => {
                expect(mockedUseNavigate).toHaveBeenCalledWith(
                    routes.SERVER_ERROR + '?encodedError=WyJTUF8xMDAxIiwiMTU3NzgzNjgwMCJd',
                );
            });
        });
        it('navigates to session expire page when a document search return 403 unauthorised error', async () => {
            const errorResponse = {
                response: {
                    status: 403,
                    message: 'An error occurred',
                },
            };
            mockedAxios.get.mockImplementation(() => Promise.reject(errorResponse));

            render(<DocumentSearchResultsPage />);

            await waitFor(() => {
                expect(mockedUseNavigate).toHaveBeenCalledWith(routes.SESSION_EXPIRED);
            });
        });
    });
});
