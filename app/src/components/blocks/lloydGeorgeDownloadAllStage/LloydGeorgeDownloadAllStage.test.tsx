import { render, screen, waitFor } from '@testing-library/react';
import LgDownloadAllStage, { Props } from './LloydGeorgeDownloadAllStage';
import { buildLgSearchResult, buildPatientDetails } from '../../../helpers/test/testBuilders';
import { createMemoryHistory } from 'history';
import * as ReactRouter from 'react-router';
import axios from 'axios';
import { act } from 'react-dom/test-utils';
import userEvent from '@testing-library/user-event';

jest.mock('axios');
jest.mock('../../../helpers/hooks/useBaseAPIHeaders');
const mockedAxios = axios as jest.Mocked<typeof axios>;
const mockPdf = buildLgSearchResult();
const mockPatient = buildPatientDetails();
const mockSetStage = jest.fn();

describe('LloydGeorgeDownloadAllStage', () => {
    beforeEach(() => {
        process.env.REACT_APP_ENVIRONMENT = 'jest';
    });
    afterEach(() => {
        jest.clearAllMocks();
    });

    it('renders the component', () => {
        renderComponent();

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
        expect(
            screen.getByRole('heading', {
                name: `Preparing download for ${mockPdf.number_of_files} files`,
            }),
        ).toBeInTheDocument();
    });

    it('renders a progress bar', () => {
        renderComponent();
        expect(screen.getByText('0% downloaded...')).toBeInTheDocument();
    });

    it('renders download complete on zip success', async () => {
        window.HTMLAnchorElement.prototype.click = jest.fn();
        mockedAxios.get.mockImplementation(() => Promise.resolve({ data: mockPdf.presign_url }));

        jest.useFakeTimers();

        renderComponent();

        expect(screen.getByText('0% downloaded...')).toBeInTheDocument();
        expect(screen.queryByText('100% downloaded...')).not.toBeInTheDocument();

        act(() => {
            jest.advanceTimersByTime(500);
        });

        await waitFor(() => {
            expect(screen.getByText('100% downloaded...')).toBeInTheDocument();
        });
        expect(screen.queryByText('0% downloaded...')).not.toBeInTheDocument();

        expect(screen.getByTestId(mockPdf.presign_url)).toBeInTheDocument();
        const urlLink = screen.getByTestId(mockPdf.presign_url);

        urlLink.addEventListener('click', (e) => {
            e.preventDefault();
        });
        act(() => {
            userEvent.click(urlLink);
        });

        await waitFor(async () => {
            expect(screen.queryByText('Downloading documents')).not.toBeInTheDocument();
        });
        expect(screen.getByRole('heading', { name: 'Download complete' })).toBeInTheDocument();
    });
});

const TestApp = (props: Omit<Props, 'setStage'>) => {
    const history = createMemoryHistory({
        initialEntries: ['/example'],
        initialIndex: 0,
    });
    return (
        <ReactRouter.Router navigator={history} location={history.location}>
            <LgDownloadAllStage {...props} setStage={mockSetStage} />
        </ReactRouter.Router>
    );
};

const renderComponent = (propsOverride?: Partial<Props>) => {
    const props: Omit<Props, 'setStage'> = {
        numberOfFiles: mockPdf.number_of_files,
        patientDetails: mockPatient,
        ...propsOverride,
    };

    return render(<TestApp {...props} />);
};
