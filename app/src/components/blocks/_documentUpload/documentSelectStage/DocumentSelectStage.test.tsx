// need to use happy-dom for this test file as jsdom doesn't support DOMMatrix https://github.com/jsdom/jsdom/issues/2647
// @vitest-environment happy-dom
import { fireEvent, render, RenderResult, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryHistory, MemoryHistory } from 'history';
import { getDocument } from 'pdfjs-dist';
import { JSX, useRef, useState } from 'react';
import * as ReactRouter from 'react-router-dom';
import usePatient from '../../../../helpers/hooks/usePatient';
import { buildLgFile, buildPatientDetails } from '../../../../helpers/test/testBuilders';
import { PDF_PARSING_ERROR_TYPE, UPLOAD_FILE_ERROR_TYPE } from '../../../../helpers/utils/fileUploadErrorMessages';
import { getFormattedDate } from '../../../../helpers/utils/formatDate';
import { formatNhsNumber } from '../../../../helpers/utils/formatNhsNumber';
import { routeChildren, routes } from '../../../../types/generic/routes';
import { DOCUMENT_TYPE, UploadDocument } from '../../../../types/pages/UploadDocumentsPage/types';
import DocumentSelectStage, { Props } from './DocumentSelectStage';
import { getFormattedPatientFullName } from '../../../../helpers/utils/formatPatientFullName';

vi.mock('../../../../helpers/hooks/usePatient');
vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return {
        ...actual,
        Link: (props: ReactRouter.LinkProps): JSX.Element => <a {...props} role="link" />,
        useNavigate: (): typeof mockedUseNavigate => mockedUseNavigate,
    };
});
vi.mock('pdfjs-dist');

const patientDetails = buildPatientDetails();

URL.createObjectURL = vi.fn();
const mockedUseNavigate = vi.fn();

let history = createMemoryHistory({
    initialEntries: ['/'],
    initialIndex: 0,
});

describe('DocumentSelectStage', () => {
    beforeEach(() => {
        vi.mocked(usePatient).mockReturnValue(patientDetails);

        import.meta.env.VITE_ENVIRONMENT = 'vitest';
        history = createMemoryHistory({ initialEntries: ['/'], initialIndex: 0 });
    });
    afterEach(() => {
        vi.clearAllMocks();
    });

    it('renders correctly', async () => {
        renderApp(history);

        await waitFor(async () => {
            expect(screen.getByText('Choose Lloyd George files to upload')).toBeInTheDocument();
        });
    });

    it.each([
        { doc_type: DOCUMENT_TYPE.LLOYD_GEORGE, title: 'Lloyd George files' },
        { doc_type: DOCUMENT_TYPE.ALL, title: 'files' },
    ])('should render the correct title based on document type', async (theory) => {
        renderApp(history, theory.doc_type);

        await waitFor(async () => {
            expect(screen.getByText(`Choose ${theory.title} to upload`)).toBeInTheDocument();
        });
    });

    describe('file handling', () => {
        let lgDocumentOne: File, lgDocumentTwo: File;
        beforeEach(async () => {
            lgDocumentOne = await buildLgFile(1);
            lgDocumentTwo = await buildLgFile(2);
        });

        it('can upload PDF file using drag and drop and button', async () => {
            renderApp(history);

            const uploadInput = screen.getByTestId('button-input');
            const dropzone = screen.getByTestId('dropzone');

            expect(
                screen.getByText('Drag and drop a file or multiple files here'),
            ).toBeInTheDocument();
            expect(dropzone);

            fireEvent.drop(dropzone, { dataTransfer: { files: [lgDocumentOne] } });

            const file1 = await screen.findByText(lgDocumentOne.name);
            expect(file1).toBeInTheDocument();

            await userEvent.upload(uploadInput, lgDocumentTwo);

            const file2 = await screen.findByText(lgDocumentTwo.name);
            expect(file2).toBeInTheDocument();

            const fileSelectedCount = screen.getAllByTestId('file-selected-count');
            expect(fileSelectedCount).toHaveLength(2);
            expect(fileSelectedCount[0]).toHaveTextContent('2 files chosen');
            expect(fileSelectedCount[1]).toHaveTextContent('2 files chosen');
        });

        it('can select and then remove a file', async () => {
            renderApp(history);

            await userEvent.upload(screen.getByTestId('button-input'), [
                lgDocumentOne,
                lgDocumentTwo,
            ]);

            let removeFile: HTMLElement;
            await waitFor(async () => {
                removeFile = await screen.findByRole('button', {
                    name: `Remove ${lgDocumentTwo.name} from selection`,
                });
            });

            await userEvent.click(removeFile!);

            await waitFor(async () => {
                expect(screen.getByText(lgDocumentOne.name)).toBeInTheDocument();
                expect(screen.queryByText(lgDocumentTwo.name)).not.toBeInTheDocument();
            });

            expect(
                screen.getByRole('heading', { level: 2, name: 'Before you upload' }),
            ).toBeInTheDocument();
        });

        it('renders patient summary fields is inset', async () => {
            renderApp(history);

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

    describe('Navigation', () => {
        let lgDocumentOne: File;
        beforeEach(async () => {
            lgDocumentOne = await buildLgFile(1);
        });

        it('should navigate to the remove all screen when clicking remove all files', async () => {
            renderApp(history);
            const lgDocumentOne = await buildLgFile(1);

            await userEvent.upload(screen.getByTestId('button-input'), [lgDocumentOne]);

            await userEvent.click(await screen.findByTestId('remove-all-button'));

            await waitFor(() => {
                expect(mockedUseNavigate).toHaveBeenCalledWith(
                    routeChildren.DOCUMENT_UPLOAD_REMOVE_ALL,
                );
            });
        });

        it('should navigate to the previous screen when go back is clicked', async () => {
            renderApp(history);

            await userEvent.click(await screen.findByTestId('back-button'));

            await waitFor(() => {
                expect(mockedUseNavigate).toHaveBeenCalledWith(routes.VERIFY_PATIENT);
            });
        });

        const errorCases = [
            ['password protected file', PDF_PARSING_ERROR_TYPE.PASSWORD_MISSING],
            ['invalid PDF structure', PDF_PARSING_ERROR_TYPE.INVALID_PDF_STRUCTURE],
            ['empty PDF', PDF_PARSING_ERROR_TYPE.EMPTY_PDF],
        ];

        it.each(errorCases)(
            'should navigate to file errors page when user selects a file that is a %s',
            async (_description, errorType) => {
                renderApp(history);

                vi.mocked(getDocument).mockImplementation(() => {
                    throw new Error(errorType);
                });

                const dropzone = screen.getByTestId('dropzone');
                fireEvent.drop(dropzone, {
                    dataTransfer: { files: [lgDocumentOne] },
                });

                await waitFor(() => {
                    expect(mockedUseNavigate).toHaveBeenCalledWith(
                        routeChildren.DOCUMENT_UPLOAD_FILE_ERRORS,
                    );
                });
            },
        );

        it('should navigate to file errors page when user selects a file that is not a PDF', async () => {
            renderApp(history);
            const dropzone = screen.getByTestId('dropzone');
            const nonPdfFile = {...lgDocumentOne, type: 'text/plain' };
            fireEvent.drop(dropzone, {
                dataTransfer: { files: [nonPdfFile] },
            });

            await waitFor(() => {
                expect(mockedUseNavigate).toHaveBeenCalledWith(
                    routeChildren.DOCUMENT_UPLOAD_FILE_ERRORS,
                );
            });
        });

        it('should navigate to file errors page when user selects a file that is a duplicate file name', async () => {
            renderApp(history);
            const dropzone = screen.getByTestId('dropzone');
            fireEvent.drop(dropzone, {
                dataTransfer: { files: [lgDocumentOne] },
            });

            await waitFor(() => {
                expect(screen.getByText(lgDocumentOne.name)).toBeInTheDocument();
            });

            fireEvent.drop(dropzone, {
                dataTransfer: { files: [lgDocumentOne] },
            });

            await waitFor(() => {
                expect(mockedUseNavigate).toHaveBeenCalledWith(
                    routeChildren.DOCUMENT_UPLOAD_FILE_ERRORS,
                );
            });
        });
    });

    const TestApp = (props: Partial<Props>): JSX.Element => {
        const [documents, setDocuments] = useState<Array<UploadDocument>>([]);
        const filesErrorRef = useRef<boolean>(false);

        return (
            <DocumentSelectStage
                documents={documents}
                setDocuments={setDocuments}
                documentType={props.documentType || DOCUMENT_TYPE.LLOYD_GEORGE}
                filesErrorRef={filesErrorRef}
            />
        );
    };

    const renderApp = (
        history: MemoryHistory,
        docType: DOCUMENT_TYPE = DOCUMENT_TYPE.LLOYD_GEORGE,
    ): RenderResult => {
        return render(
            <ReactRouter.Router navigator={history} location={history.location}>
                <TestApp documentType={docType} />
            </ReactRouter.Router>,
        );
    };
});
