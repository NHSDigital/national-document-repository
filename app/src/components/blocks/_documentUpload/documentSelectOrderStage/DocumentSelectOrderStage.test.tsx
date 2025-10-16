import { render, waitFor, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DocumentSelectOrderStage from './DocumentSelectOrderStage';
import {
    DOCUMENT_TYPE,
    DOCUMENT_UPLOAD_STATE,
    UploadDocument,
} from '../../../../types/pages/UploadDocumentsPage/types';
import { MemoryRouter } from 'react-router-dom';
import { fileUploadErrorMessages } from '../../../../helpers/utils/fileUploadErrorMessages';
import { buildLgFile } from '../../../../helpers/test/testBuilders';
import { Mock } from 'vitest';

const mockNavigate = vi.fn();
const mockSetDocuments = vi.fn();
const mockSetMergedPdfBlob = vi.fn();

vi.mock('../../../../helpers/hooks/usePatient');
vi.mock('../../../../helpers/hooks/useTitle');
vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return {
        ...actual,
        useNavigate: (): Mock => mockNavigate,
    };
});

URL.createObjectURL = vi.fn(() => 'mocked-url');

// Mock scrollIntoView which is not available in JSDOM
Element.prototype.scrollIntoView = vi.fn();

vi.mock('../documentUploadLloydGeorgePreview/DocumentUploadLloydGeorgePreview', () => ({
    default: ({
        documents,
        stitchedBlobLoaded,
    }: {
        documents: UploadDocument[];
        stitchedBlobLoaded?: (loaded: boolean) => void;
    }): React.JSX.Element => {
        // Simulate the PDF stitching completion
        if (stitchedBlobLoaded) {
            setTimeout(() => stitchedBlobLoaded(true), 0);
        }
        return (
            <div data-testid="lloyd-george-preview">
                Lloyd George Preview for {documents.length} documents
            </div>
        );
    },
}));

describe('DocumentSelectOrderStage', () => {
    let documents: UploadDocument[] = [];

    beforeEach(() => {
        import.meta.env.VITE_ENVIRONMENT = 'vitest';
        documents = [
            {
                docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                id: '1',
                file: buildLgFile(1),
                attempts: 0,
                state: DOCUMENT_UPLOAD_STATE.SELECTED,
                numPages: 5,
                position: 1,
            },
        ];
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    describe('Rendering', () => {
        it('renders the component with page title and instructions', async () => {
            renderSut(documents);

            await waitFor(() => {
                expect(
                    screen.getByText('What order do you want these files in?'),
                ).toBeInTheDocument();
                expect(
                    screen.getByText(
                        'If you have more than one file, they may not be in the correct order:',
                    ),
                ).toBeInTheDocument();
                expect(
                    screen.getByText(
                        'When you upload your files, they will be combined into a single PDF document.',
                    ),
                ).toBeInTheDocument();
            });
        });

        it('renders the document table with headers', () => {
            renderSut(documents);

            expect(screen.getByText('Filename')).toBeInTheDocument();
            expect(screen.getByText('Pages')).toBeInTheDocument();
            expect(screen.getByText('Position')).toBeInTheDocument();
            expect(screen.getByText('View file')).toBeInTheDocument();
            expect(screen.getByText('Remove file')).toBeInTheDocument();
        });

        it('displays document information in the table', () => {
            renderSut(documents);

            expect(screen.getByText('testFile1.pdf')).toBeInTheDocument();
            expect(screen.getByText('5')).toBeInTheDocument();
            expect(screen.getByText('View')).toBeInTheDocument();
            expect(screen.getByText('Remove')).toBeInTheDocument();
        });

        it('renders continue button when documents are present', async () => {
            renderSut(documents);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: 'Continue' })).toBeInTheDocument();
            });
        });

        it('does not show "Remove all" button when there is only one document', () => {
            renderSut(documents);

            expect(screen.queryByText('Remove all')).not.toBeInTheDocument();
        });

        it('shows Lloyd George preview when documents contain Lloyd George type and form is valid', async () => {
            renderSut(documents);

            await waitFor(() => {
                expect(screen.getByText('Preview this Lloyd George record')).toBeInTheDocument();
                expect(screen.getByTestId('lloyd-george-preview')).toBeInTheDocument();
            });
        });

        it('shows message when no documents are present', () => {
            renderSut([]);

            expect(screen.getByText(/You have removed all files/)).toBeInTheDocument();
            expect(screen.getByText('choose files')).toBeInTheDocument();
        });
    });

    describe('Position Selection', () => {
        it('renders position dropdown for each document', () => {
            const multipleDocuments = [
                ...documents,
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '2',
                    file: buildLgFile(2),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 3,
                    position: 2,
                },
            ];

            renderSut(multipleDocuments);

            expect(screen.getByTestId('1')).toBeInTheDocument();
            expect(screen.getByTestId('2')).toBeInTheDocument();
        });

        it('updates document position when dropdown value changes', async () => {
            const user = userEvent.setup();
            const multipleDocuments = [
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '1',
                    file: buildLgFile(1),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 5,
                    position: 1,
                },
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '2',
                    file: buildLgFile(2),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 3,
                    position: 2,
                },
            ];

            renderSut(multipleDocuments);

            const positionSelect = screen.getByTestId('1');
            await user.selectOptions(positionSelect, '2');

            expect(mockSetDocuments).toHaveBeenCalled();
        });
    });

    describe('Document Removal', () => {
        it('calls onRemove when remove button is clicked', async () => {
            const user = userEvent.setup();

            renderSut(documents);

            const removeButton = screen.getByRole('button', {
                name: /Remove testFile1.pdf from selection/,
            });
            await user.click(removeButton);

            expect(mockSetDocuments).toHaveBeenCalledWith([]);
        });

        it('adjusts positions when removing a document from the middle of the list', async () => {
            const user = userEvent.setup();
            const multipleDocuments = [
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '1',
                    file: buildLgFile(1),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 5,
                    position: 1,
                },
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '2',
                    file: buildLgFile(2),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 3,
                    position: 2,
                },
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '3',
                    file: buildLgFile(3),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 2,
                    position: 3,
                },
            ];

            renderSut(multipleDocuments);

            // Remove the middle document (position 2)
            const removeButton = screen.getByRole('button', {
                name: /Remove testFile2.pdf from selection/,
            });
            await user.click(removeButton);

            // Verify that setDocuments was called with the correct updated list
            expect(mockSetDocuments).toHaveBeenCalledWith([
                expect.objectContaining({
                    id: '1',
                    position: 1, // Should remain unchanged
                }),
                expect.objectContaining({
                    id: '3',
                    position: 2, // Should be adjusted from 3 to 2
                }),
            ]);
        });

        it('removes document without affecting positions of documents with lower positions', async () => {
            const user = userEvent.setup();
            const multipleDocuments = [
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '1',
                    file: buildLgFile(1),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 5,
                    position: 1,
                },
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '2',
                    file: buildLgFile(2),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 3,
                    position: 2,
                },
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '3',
                    file: buildLgFile(3),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 2,
                    position: 3,
                },
            ];

            renderSut(multipleDocuments);

            // Remove the last document (position 3)
            const removeButton = screen.getByRole('button', {
                name: /Remove testFile3.pdf from selection/,
            });
            await user.click(removeButton);

            // Verify that documents with lower positions remain unchanged
            expect(mockSetDocuments).toHaveBeenCalledWith([
                expect.objectContaining({
                    id: '1',
                    position: 1, // Should remain unchanged
                }),
                expect.objectContaining({
                    id: '2',
                    position: 2, // Should remain unchanged
                }),
            ]);
        });

        it('handles removal of document without position set', async () => {
            const user = userEvent.setup();
            const documentsWithoutPosition = [
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '1',
                    file: buildLgFile(1),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 5,
                    position: undefined, // No position set
                },
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '2',
                    file: buildLgFile(2),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 3,
                    position: 1,
                },
            ];

            renderSut(documentsWithoutPosition);

            const removeButton = screen.getByRole('button', {
                name: /Remove testFile1.pdf from selection/,
            });
            await user.click(removeButton);

            // Should remove the document and leave the other unchanged
            expect(mockSetDocuments).toHaveBeenCalledWith([
                expect.objectContaining({
                    id: '2',
                    position: 1,
                }),
            ]);
        });

        it('displays correct aria-label for each remove button', () => {
            const multipleDocuments = [
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '1',
                    file: buildLgFile(1),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 5,
                    position: 1,
                },
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '2',
                    file: buildLgFile(2),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 3,
                    position: 2,
                },
            ];

            renderSut(multipleDocuments);

            expect(
                screen.getByRole('button', {
                    name: 'Remove testFile1.pdf from selection',
                }),
            ).toBeInTheDocument();
            expect(
                screen.getByRole('button', {
                    name: 'Remove testFile2.pdf from selection',
                }),
            ).toBeInTheDocument();
        });

        it('shows appropriate message when all documents are removed', () => {
            renderSut([]);

            expect(screen.getByText(/You have removed all files/)).toBeInTheDocument();
            expect(screen.getByText('choose files')).toBeInTheDocument();
        });
    });

    describe('Form Validation', () => {
        it('shows error when duplicate positions are selected and continue is clicked', async () => {
            const user = userEvent.setup();
            const documentsWithDuplicatePositions = [
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '1',
                    file: buildLgFile(1),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 5,
                    position: 1,
                },
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '2',
                    file: buildLgFile(2),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 3,
                    position: 1, // Duplicate position
                },
            ];

            renderSut(documentsWithDuplicatePositions);

            let continueButton;
            await waitFor(() => {
                continueButton = screen.getByRole('button', { name: 'Continue' });
                expect(continueButton).toBeInTheDocument();
            });

            await user.click(continueButton!);

            await waitFor(() => {
                expect(screen.getByText('There is a problem')).toBeInTheDocument();
            });
            const errorMessages = screen.getAllByText(
                fileUploadErrorMessages.duplicatePositionError.inline,
            );
            expect(errorMessages.length).toBe(3);
        });
    });

    describe('PDF Viewer Integration', () => {
        it('renders PDF viewer when Lloyd George preview is shown', async () => {
            renderSut(documents);

            await waitFor(() => {
                expect(screen.getByTestId('lloyd-george-preview')).toBeInTheDocument();
            });
        });

        it('passes correct documents to Lloyd George preview component', async () => {
            const multipleDocuments = [
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '1',
                    file: buildLgFile(1),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 5,
                    position: 1,
                },
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '2',
                    file: buildLgFile(2),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 3,
                    position: 2,
                },
            ];

            renderSut(multipleDocuments);

            await waitFor(() => {
                expect(
                    screen.getByText('Lloyd George Preview for 2 documents'),
                ).toBeInTheDocument();
            });
        });
    });
});

function renderSut(documents: UploadDocument[]): void {
    render(
        <MemoryRouter>
            <DocumentSelectOrderStage
                documents={documents}
                setDocuments={mockSetDocuments}
                setMergedPdfBlob={mockSetMergedPdfBlob}
            />
        </MemoryRouter>,
    );
}
