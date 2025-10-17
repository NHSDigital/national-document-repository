import { render, waitFor, screen, RenderResult } from '@testing-library/react';
import DocumentUploadConfirmStage from './DocumentUploadConfirmStage';
import { formatNhsNumber } from '../../../../helpers/utils/formatNhsNumber';
import { getFormattedDate } from '../../../../helpers/utils/formatDate';
import { buildPatientDetails } from '../../../../helpers/test/testBuilders';
import usePatient from '../../../../helpers/hooks/usePatient';
import {
    DOCUMENT_TYPE,
    DOCUMENT_UPLOAD_STATE,
    UploadDocument,
} from '../../../../types/pages/UploadDocumentsPage/types';
import * as ReactRouter from 'react-router-dom';
import { MemoryHistory, createMemoryHistory } from 'history';
import userEvent from '@testing-library/user-event';
import { routeChildren, routes } from '../../../../types/generic/routes';
import { getFormattedPatientFullName } from '../../../../helpers/utils/formatPatientFullName';

const mockedUseNavigate = vi.fn();
vi.mock('../../../../helpers/hooks/usePatient');
vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return {
        ...actual,
        useNavigate: () => mockedUseNavigate,
    };
});

const patientDetails = buildPatientDetails();

URL.createObjectURL = vi.fn();

let history = createMemoryHistory({
    initialEntries: ['/'],
    initialIndex: 0,
});

describe('DocumentUploadCompleteStage', () => {
    beforeEach(() => {
        vi.mocked(usePatient).mockReturnValue(patientDetails);

        import.meta.env.VITE_ENVIRONMENT = 'vitest';
        history = createMemoryHistory({ initialEntries: ['/'], initialIndex: 0 });
    });
    afterEach(() => {
        vi.clearAllMocks();
    });

    it('renders', async () => {
        renderApp(history, 1);

        await waitFor(async () => {
            expect(screen.getByText('Check your files before uploading')).toBeInTheDocument();
        });
    });

    it('should navigate to next screen when confirm button is clicked', async () => {
        renderApp(history, 1);

        userEvent.click(await screen.findByTestId('confirm-button'));

        await waitFor(() => {
            expect(mockedUseNavigate).toHaveBeenCalledWith({
                pathname: routeChildren.DOCUMENT_UPLOAD_UPLOADING,
                search: '',
            });
        });
    });

    it('should render pagination when doc count is high enough', async () => {
        renderApp(history, 15);

        await waitFor(async () => {
            expect(await screen.findByTestId('page-1-button')).toBeInTheDocument();
            expect(await screen.findByTestId('page-2-button')).toBeInTheDocument();
        });
    });

    describe('Navigation', () => {
        it('should navigate to previous screen when go back is clicked', async () => {
            renderApp(history, 1);

            userEvent.click(await screen.findByTestId('go-back-link'));

            await waitFor(() => {
                expect(mockedUseNavigate).toHaveBeenCalledWith(-1);
            });
        });

        it('should navigate to the file selection page when change files is clicked', async () => {
            renderApp(history, 1);

            userEvent.click(await screen.findByTestId('change-files-button'));

            await waitFor(() => {
                expect(mockedUseNavigate).toHaveBeenCalledWith({
                    pathname: routes.DOCUMENT_UPLOAD,
                    search: '',
                });
            });
        });

        it('renders patient summary fields is inset', async () => {
            renderApp(history, 1);

            const insetText = screen
                .getByText('Make sure that all files uploaded are for this patient only:')
                .closest('.nhsuk-inset-text');
            expect(insetText).toBeInTheDocument();

            const expectedFullName = getFormattedPatientFullName(patientDetails);
            expect(screen.getByText(/Patient name/i)).toBeInTheDocument();
            expect(screen.getByText(expectedFullName)).toBeInTheDocument();

            expect(screen.getByText(/NHS number/i)).toBeInTheDocument();
            const expectedNhsNumber = formatNhsNumber(patientDetails.nhsNumber);
            expect(screen.getByText(expectedNhsNumber)).toBeInTheDocument();

            expect(screen.getByText(/Date of birth/i)).toBeInTheDocument();
            const expectedDob = getFormattedDate(new Date(patientDetails.birthDate));
            expect(screen.getByText(expectedDob)).toBeInTheDocument();
        });
    });

    describe('Update Journey', () => {
        beforeEach(() => {
            delete (globalThis as any).location;
            globalThis.location = { search: '?journey=update' } as any;

            history = createMemoryHistory({
                initialEntries: ['/?journey=update'],
                initialIndex: 0,
            });
        });

        it('renders correct text for update journey', async () => {
            renderApp(history, 1);

            await waitFor(async () => {
                expect(
                    screen.getByText(
                        'Files will be added to the existing Lloyd George record to create a single PDF document.',
                    ),
                ).toBeInTheDocument();
            });
        });

        it('should navigate with journey param when change files is clicked', async () => {
            renderApp(history, 1);

            userEvent.click(await screen.findByTestId('change-files-button'));

            await waitFor(() => {
                expect(mockedUseNavigate).toHaveBeenCalledWith({
                    pathname: routes.DOCUMENT_UPLOAD,
                    search: 'journey=update',
                });
            });
        });

        it('should navigate with journey param when confirm button is clicked', async () => {
            renderApp(history, 1);

            userEvent.click(await screen.findByTestId('confirm-button'));

            await waitFor(() => {
                expect(mockedUseNavigate).toHaveBeenCalledWith({
                    pathname: routeChildren.DOCUMENT_UPLOAD_UPLOADING,
                    search: 'journey=update',
                });
            });
        });

        it('should still render all page elements correctly', async () => {
            renderApp(history, 1);

            await waitFor(async () => {
                expect(screen.getByText('Check your files before uploading')).toBeInTheDocument();
                expect(screen.getByTestId('go-back-link')).toBeInTheDocument();
                expect(screen.getByTestId('change-files-button')).toBeInTheDocument();
                expect(screen.getByTestId('confirm-button')).toBeInTheDocument();
                expect(screen.getByText('Files to be uploaded')).toBeInTheDocument();
            });
        });

        it('should render pagination when doc count is high enough in update journey', async () => {
            renderApp(history, 15);

            await waitFor(async () => {
                expect(await screen.findByTestId('page-1-button')).toBeInTheDocument();
                expect(await screen.findByTestId('page-2-button')).toBeInTheDocument();
            });
        });
    });

    const renderApp = (history: MemoryHistory, docsLength: number): RenderResult => {
        const documents: UploadDocument[] = [];
        for (let i = 1; i <= docsLength; i++) {
            documents.push({
                attempts: 0,
                id: `${i}`,
                docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                file: new File(['file'], `file ${i}.pdf`),
                state: DOCUMENT_UPLOAD_STATE.SELECTED,
            });
        }

        return render(
            <ReactRouter.Router navigator={history} location={history.location}>
                <DocumentUploadConfirmStage documents={documents} />
            </ReactRouter.Router>,
        );
    };
});
