// @vitest-environment happy-dom
import { render, screen } from '@testing-library/react';
import { act } from 'react';
import {
    buildConfig,
    buildLgSearchResult,
    buildPatientDetails,
} from '../../../../helpers/test/testBuilders';
import userEvent from '@testing-library/user-event';
import usePatient from '../../../../helpers/hooks/usePatient';
import { routeChildren, routes } from '../../../../types/generic/routes';
import useConfig from '../../../../helpers/hooks/useConfig';
import { MemoryHistory, createMemoryHistory } from 'history';
import * as ReactRouter from 'react-router-dom';
import LloydGeorgeDownloadStage, { Props } from './LloydGeorgeDownloadStage';
import { runAxeTest } from '../../../../helpers/test/axeTestHelper';
import { DownloadManifestError } from '../../../../types/generic/errors';
import { afterEach, beforeEach, describe, expect, it, vi, Mock } from 'vitest';
import getPresignedUrlForZip from '../../../../helpers/requests/getPresignedUrlForZip';

vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return {
        ...actual,
        Link: (props: ReactRouter.LinkProps) => <a {...props} role="link" />,
        useNavigate: () => mockedUseNavigate,
    };
});
Date.now = () => new Date('2020-01-01T00:00:00.000Z').getTime();
vi.mock('axios');
vi.mock('../../../../helpers/requests/getPresignedUrlForZip');
vi.mock('../../../../helpers/hooks/useBaseAPIHeaders');
vi.mock('../../../../helpers/hooks/usePatient');
vi.mock('../../../../helpers/hooks/useConfig');

const mockedUseNavigate = vi.fn();
const mockedUsePatient = usePatient as Mock;
const mockUseConfig = useConfig as Mock;
const mockPdf = buildLgSearchResult();
const mockPatient = buildPatientDetails();

let history = createMemoryHistory({
    initialEntries: ['/'],
    initialIndex: 0,
});

describe('LloydGeorgeDownloadStage', () => {
    beforeEach(() => {
        vi.useFakeTimers();
        history = createMemoryHistory({ initialEntries: ['/'], initialIndex: 0 });

        import.meta.env.VITE_ENVIRONMENT = 'vitest';
        mockedUsePatient.mockReturnValue(mockPatient);
        mockUseConfig.mockReturnValue(buildConfig());
    });
    afterEach(() => {
        vi.useRealTimers();
        vi.clearAllMocks();
    });

    it('renders the component', () => {
        renderComponent(history);

        expect(screen.getByRole('heading', { name: 'Downloading documents' })).toBeInTheDocument();
        expect(
            screen.getByRole('heading', {
                name: mockPatient.givenName + ' ' + mockPatient.familyName,
            }),
        ).toBeInTheDocument();
        expect(
            screen.getByRole('heading', {
                name: `NHS number: ${mockPatient.nhsNumber}`,
            }),
        ).toBeInTheDocument();

        const expectedTestId = 'download-file-header-' + mockPdf.numberOfFiles + '-files';
        expect(screen.getByTestId(expectedTestId)).toBeInTheDocument();
        expect(screen.getByTestId('cancel-download-link')).toHaveTextContent(
            'Cancel and return to patient record',
        );
    });

    it('renders a progress bar', () => {
        renderComponent(history);
        expect(screen.getByText('0% downloaded...')).toBeInTheDocument();
    });

    it('navigates to download complete after auto-clicking link', async () => {
        vi.useFakeTimers();

        vi.mocked(getPresignedUrlForZip).mockResolvedValue(mockPdf.presignedUrl);

        renderComponent(history);

        await act(async () => {
            vi.advanceTimersByTime(1500);
        });

        expect(getPresignedUrlForZip).toHaveBeenCalled();

        await vi.waitFor(async () => {
            await userEvent.click(screen.getByText('Download Lloyd George Documents URL'));
        });

        await act(async () => {
            vi.advanceTimersByTime(1500);
        });
        expect(mockedUseNavigate).toHaveBeenCalledWith(
            routeChildren.LLOYD_GEORGE_DOWNLOAD_COMPLETE,
        );
    });

    it.skip('pass accessibility checks', async () => {
        renderComponent(history);

        const results = await runAxeTest(document.body);
        expect(results).toHaveNoViolations();
    });

    it('navigates to Error page when zip lg record view return 500', async () => {
        const errorResponse = {
            response: {
                status: 500,
                data: { message: 'An error occurred', err_code: 'SP_1001' },
            },
        };
        // eslint-disable-next-line prefer-promise-reject-errors
        vi.mocked(getPresignedUrlForZip).mockImplementation(() => Promise.reject(errorResponse));

        renderComponent(history);

        await act(async () => {
            vi.advanceTimersByTime(2000);
        });

        await vi.waitFor(() => {
            expect(vi.mocked(getPresignedUrlForZip)).toHaveBeenCalled();
        });

        expect(mockedUseNavigate).toHaveBeenCalledWith(
            routes.SERVER_ERROR + '?encodedError=WyJTUF8xMDAxIiwiMTU3NzgzNjgwMiJd',
        );
    });

    it('navigates to Error page when GetPresignedUrlForZip throw DownloadManifestError', async () => {
        const mockError = new DownloadManifestError('some error msg');
        vi.mocked(getPresignedUrlForZip).mockImplementation(() => Promise.reject(mockError));

        renderComponent(history);

        await act(async () => {
            vi.advanceTimersByTime(2000);
        });

        await vi.waitFor(() => {
            expect(vi.mocked(getPresignedUrlForZip)).toHaveBeenCalled();
        });

        expect(mockedUseNavigate).toHaveBeenCalledWith(
            expect.stringContaining(routes.SERVER_ERROR),
        );
    });

    it('navigates to session expire page when zip lg record return 403', async () => {
        const errorResponse = {
            response: {
                status: 403,
                data: { message: 'Unauthorised' },
            },
        };
        // eslint-disable-next-line prefer-promise-reject-errors
        vi.mocked(getPresignedUrlForZip).mockImplementation(() => Promise.reject(errorResponse));

        renderComponent(history);

        await act(async () => {
            vi.advanceTimersByTime(2000);
        });

        await vi.waitFor(() => {
            expect(vi.mocked(getPresignedUrlForZip)).toHaveBeenCalled();
        });

        expect(mockedUseNavigate).toHaveBeenCalledWith(routes.SESSION_EXPIRED);
    });
});

const renderComponent = (history: MemoryHistory, propsOverride?: Partial<Props>) => {
    const props: Omit<Props, 'setStage' | 'setDownloadStage'> = {
        ...propsOverride,
        numberOfFiles: mockPdf.numberOfFiles,
    };

    return render(
        <ReactRouter.Router navigator={history} location={history.location}>
            <LloydGeorgeDownloadStage {...props} />
        </ReactRouter.Router>,
    );
};
