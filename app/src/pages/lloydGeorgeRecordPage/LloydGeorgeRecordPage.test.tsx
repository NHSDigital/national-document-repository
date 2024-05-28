import { render, screen, waitFor } from '@testing-library/react';
import LloydGeorgeRecordPage from './LloydGeorgeRecordPage';
import {
    buildPatientDetails,
    buildLgSearchResult,
    buildSearchResult,
    buildConfig,
} from '../../helpers/test/testBuilders';
import { getFormattedDate } from '../../helpers/utils/formatDate';
import axios from 'axios';
import formatFileSize from '../../helpers/utils/formatFileSize';
import usePatient from '../../helpers/hooks/usePatient';
import { act } from 'react-dom/test-utils';
import { routes } from '../../types/generic/routes';
import useConfig from '../../helpers/hooks/useConfig';
import useRole from '../../helpers/hooks/useRole';
import { REPOSITORY_ROLE } from '../../types/generic/authRole';
import { LinkProps } from 'react-router-dom';
import * as ReactRouter from 'react-router';
import { History, createMemoryHistory } from 'history';
import { runAxeTest } from '../../helpers/test/axeTestHelper';

jest.mock('../../helpers/hooks/useConfig');
jest.mock('axios');
jest.mock('../../helpers/hooks/usePatient');
jest.mock('../../helpers/hooks/useBaseAPIHeaders');
jest.mock('../../helpers/hooks/useBaseAPIUrl');
jest.mock('../../helpers/hooks/useRole');
jest.mock('../../helpers/hooks/useIsBSOL');
const mockAxios = axios as jest.Mocked<typeof axios>;
const mockPatientDetails = buildPatientDetails();
const mockedUsePatient = usePatient as jest.Mock;
const mockNavigate = jest.fn();
const mockUseConfig = useConfig as jest.Mock;
const mockUseRole = useRole as jest.Mock;
jest.mock('react-router-dom', () => ({
    __esModule: true,
    Link: (props: LinkProps) => <a {...props} role="link" />,
    useNavigate: () => mockNavigate,
}));
jest.mock('react-router', () => ({
    ...jest.requireActual('react-router'),
    useNavigate: () => mockNavigate,
}));
jest.mock('moment', () => {
    return () => jest.requireActual('moment')('2020-01-01T00:00:00.000Z');
});

let history = createMemoryHistory({
    initialEntries: ['/'],
    initialIndex: 0,
});

describe('LloydGeorgeRecordPage', () => {
    beforeEach(() => {
        history = createMemoryHistory({
            initialEntries: ['/'],
            initialIndex: 0,
        });

        process.env.REACT_APP_ENVIRONMENT = 'jest';
        mockedUsePatient.mockReturnValue(mockPatientDetails);
        mockUseConfig.mockReturnValue(buildConfig());
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    it('renders patient details', async () => {
        const patientName = `${mockPatientDetails.givenName} ${mockPatientDetails.familyName}`;
        const dob = getFormattedDate(new Date(mockPatientDetails.birthDate));
        mockAxios.get.mockReturnValue(Promise.resolve({ data: buildLgSearchResult() }));

        renderPage(history);

        await waitFor(async () => {
            expect(screen.getByText(patientName)).toBeInTheDocument();
        });
        expect(screen.getByText(`Date of birth: ${dob}`)).toBeInTheDocument();
        expect(screen.getByText(/NHS number/)).toBeInTheDocument();
    });

    it('renders initial lg record view', async () => {
        renderPage(history);
        await waitFor(async () => {
            expect(screen.getByText('Lloyd George record')).toBeInTheDocument();
        });
    });

    it('renders initial lg record view with no docs available text if there is no LG record', async () => {
        const errorResponse = {
            response: {
                status: 404,
                message: '404 no docs found',
            },
        };

        mockAxios.get.mockImplementation(() => Promise.reject(errorResponse));

        renderPage(history);

        await waitFor(async () => {
            expect(screen.getByText('No documents are available.')).toBeInTheDocument();
        });

        expect(screen.queryByText('View record')).not.toBeInTheDocument();
    });
    it('renders initial lg record view with no docs available text if lambda return records status is uploading for more than 3 min', async () => {
        const errorResponse = {
            response: {
                status: 400,
                data: { err_code: 'LGL_400', message: '400 no docs found' },
                message: '400 no docs found',
            },
        };

        mockAxios.get.mockImplementation(() => Promise.reject(errorResponse));

        renderPage(history);

        await waitFor(async () => {
            expect(screen.getByText('No documents are available.')).toBeInTheDocument();
        });

        expect(screen.queryByText('View record')).not.toBeInTheDocument();
    });
    it('renders initial lg record view with docs are uploading text if response status is 423', async () => {
        const errorResponse = {
            response: {
                status: 423,
                data: { err_code: 'LGL_423', message: '423' },
                message: '423',
            },
        };

        mockAxios.get.mockImplementation(() => Promise.reject(errorResponse));

        renderPage(history);

        await waitFor(async () => {
            expect(
                screen.getByText(
                    'You can view this record once it’s finished uploading. This may take a few minutes.',
                ),
            ).toBeInTheDocument();
        });

        expect(screen.queryByText('View record')).not.toBeInTheDocument();
    });
    it('renders initial lg record view with timeout text if response is 504', async () => {
        const errorResponse = {
            response: {
                status: 504,
                message: '504 no docs found',
            },
        };

        mockAxios.get.mockImplementation(() => Promise.reject(errorResponse));
        mockUseRole.mockReturnValue(REPOSITORY_ROLE.GP_CLINICAL);

        renderPage(history);

        await waitFor(async () => {
            expect(
                screen.getByText(/The Lloyd George document is too large to view in a browser/i),
            ).toBeInTheDocument();
        });
        expect(screen.getByText(/please download instead/i)).toBeInTheDocument();

        expect(screen.queryByText('View record')).not.toBeInTheDocument();
    });

    it('displays Loading... until the pdf is fetched', async () => {
        mockAxios.get.mockReturnValue(Promise.resolve({ data: buildLgSearchResult() }));

        renderPage(history);

        await waitFor(async () => {
            expect(screen.getByText('Loading...')).toBeInTheDocument();
        });
    });

    it('renders initial lg record view with file info when LG record is returned by search', async () => {
        const lgResult = buildLgSearchResult();
        mockAxios.get.mockReturnValue(Promise.resolve({ data: lgResult }));

        renderPage(history);

        await waitFor(() => {
            expect(screen.getByTitle('Embedded PDF')).toBeInTheDocument();
        });
        expect(screen.getByText('View record')).toBeInTheDocument();
        expect(screen.getByText('View in full screen')).toBeInTheDocument();

        expect(screen.getByText('Lloyd George record')).toBeInTheDocument();
        expect(screen.queryByText('No documents are available')).not.toBeInTheDocument();

        expect(screen.getByText(`${lgResult.number_of_files} files`)).toBeInTheDocument();
        expect(
            screen.getByText(`File size: ${formatFileSize(lgResult.total_file_size_in_byte)}`),
        ).toBeInTheDocument();
        expect(screen.getByText('File format: PDF')).toBeInTheDocument();
    });

    describe('Accessibility', () => {
        it('pass accessibility checks at page entry point', async () => {
            const lgResult = buildLgSearchResult();
            mockAxios.get.mockReturnValue(Promise.resolve({ data: lgResult }));

            renderPage(history);

            await waitFor(() => {
                expect(screen.getByTitle('Embedded PDF')).toBeInTheDocument();
            });

            const results = await runAxeTest(document.body);
            expect(results).toHaveNoViolations();
        });
    });

    it('navigates to Error page when call to lg record view return 500', async () => {
        mockAxios.get.mockResolvedValue({ data: [buildSearchResult()] });
        const errorResponse = {
            response: {
                status: 500,
                data: { message: 'An error occurred', err_code: 'SP_1001' },
            },
        };
        mockAxios.get.mockImplementation(() => Promise.reject(errorResponse));

        act(() => {
            renderPage(history);
        });

        await waitFor(() => {
            expect(screen.queryByRole('link', { name: 'Start Again' })).not.toBeInTheDocument();
        });

        await waitFor(() => {
            expect(mockNavigate).toHaveBeenCalledWith(
                routes.SERVER_ERROR + '?encodedError=WyJTUF8xMDAxIiwiMTU3NzgzNjgwMCJd',
            );
        });
    });

    it('navigates to session expired page when call to lg record view return 403', async () => {
        mockAxios.get.mockResolvedValue({ data: [buildSearchResult()] });
        const errorResponse = {
            response: {
                status: 403,
                data: { message: 'Unauthorised' },
            },
        };
        mockAxios.get.mockImplementation(() => Promise.reject(errorResponse));

        act(() => {
            renderPage(history);
        });

        await waitFor(() => {
            expect(screen.queryByRole('link', { name: 'Start Again' })).not.toBeInTheDocument();
        });

        await waitFor(() => {
            expect(mockNavigate).toHaveBeenCalledWith(routes.SESSION_EXPIRED);
        });
    });

    const renderPage = (history: History) => {
        return render(
            <ReactRouter.Router navigator={history} location={history.location}>
                <LloydGeorgeRecordPage />
            </ReactRouter.Router>,
        );
    };
});
