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
    default: ({ documents }: { documents: UploadDocument[] }): React.JSX.Element => (
        <div data-testid="lloyd-george-preview">
            Lloyd George Preview for {documents.length} documents
        </div>
    ),
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
            expect(screen.getByText('Position')).toBeInTheDocument();
            expect(screen.getByText('View file')).toBeInTheDocument();
            expect(screen.getByText('Remove file')).toBeInTheDocument();
        });

        it('displays document information in the table', () => {
            renderSut(documents);

            expect(screen.getByText('testFile1.pdf')).toBeInTheDocument();
            expect(screen.getByText('View')).toBeInTheDocument();
            expect(screen.getByText('Remove')).toBeInTheDocument();
        });

        it('renders continue button when documents are present', () => {
            renderSut(documents);

            expect(screen.getByRole('button', { name: 'Continue' })).toBeInTheDocument();
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

            const continueButton = screen.getByRole('button', { name: 'Continue' });
            await user.click(continueButton);

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

    describe('Update Journey', () => {
        beforeEach(() => {
            delete (globalThis as any).location;
            globalThis.location = { search: '?journey=update' } as any;
        });

        it('navigates with journey param when continue button is clicked', async () => {
            const user = userEvent.setup();

            renderSut(documents);

            const continueButton = screen.getByRole('button', { name: 'Continue' });
            await user.click(continueButton);

            await waitFor(() => {
                expect(mockNavigate).toHaveBeenCalledWith({
                    pathname: '/patient/document-upload/in-progress',
                    search: 'journey=update',
                });
            });
        });

        it('navigates with journey param when continue button is clicked with multiple docs', async () => {
            const user = userEvent.setup();
            documents.push({
                docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                id: '2',
                file: buildLgFile(2),
                attempts: 0,
                state: DOCUMENT_UPLOAD_STATE.SELECTED,
                numPages: 3,
                position: 2,
            });

            renderSut(documents);

            const continueButton = screen.getByRole('button', { name: 'Continue' });
            await user.click(continueButton);

            await waitFor(() => {
                expect(mockNavigate).toHaveBeenCalledWith({
                    pathname: '/patient/document-upload/confirmation',
                    search: 'journey=update',
                });
            });
        });

        it('displays update journey specific instructions', () => {
            renderSut(documents);

            expect(
                screen.getByText(
                    "When you upload your files, they will be added to the end of the patient's existing Lloyd George record.",
                ),
            ).toBeInTheDocument();
            expect(
                screen.getByText('you cannot change the order of the existing files'),
            ).toBeInTheDocument();
            expect(
                screen.getByText(
                    "change the order number to put the files you've added in the order you want",
                ),
            ).toBeInTheDocument();
        });

        it('does not display standard journey instructions in update journey', () => {
            renderSut(documents);

            expect(
                screen.queryByText(
                    'When you upload your files, they will be combined into a single PDF document.',
                ),
            ).not.toBeInTheDocument();
            expect(
                screen.queryByText(
                    'put your files in the order you need them to appear in the final document by changing the position number',
                ),
            ).not.toBeInTheDocument();
        });

        it('shows existing Lloyd George record row when existingDocuments are provided', () => {
            const existingDocs = [
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: 'existing-1',
                    file: buildLgFile(99),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 10,
                    position: 1,
                },
            ];

            renderSutWithExistingDocs(documents, existingDocs);

            expect(screen.getByText('Existing Lloyd George record')).toBeInTheDocument();
        });

        it('existing Lloyd George record has position 1 and cannot be repositioned or removed', () => {
            const existingDocs = [
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: 'existing-1',
                    file: buildLgFile(99),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 10,
                    position: 1,
                },
            ];

            renderSutWithExistingDocs(documents, existingDocs);

            const rows = screen.getAllByRole('row');
            const existingRow = rows.find((row) =>
                row.textContent?.includes('Existing Lloyd George record'),
            );

            expect(existingRow).toBeInTheDocument();
            expect(existingRow?.textContent).toContain('1');
            expect(existingRow?.textContent).toContain('-'); // Shows dash for remove column
        });

        it('positions new documents starting from position 2 when existing documents are present', () => {
            const existingDocs = [
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: 'existing-1',
                    file: buildLgFile(99),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 10,
                    position: 1,
                },
            ];

            const newDocuments = [
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '1',
                    file: buildLgFile(1),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 5,
                    position: 2,
                },
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '2',
                    file: buildLgFile(2),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 3,
                    position: 3,
                },
            ];

            renderSutWithExistingDocs(newDocuments, existingDocs);

            // Check that dropdowns have options starting from 2
            const firstDocSelect: HTMLSelectElement = screen.getByTestId('1');
            const options = Array.from(firstDocSelect.options).map((opt) => opt.value);

            expect(options).toEqual(['2', '3']);
        });

        it('shows appropriate message when all new documents are removed in update journey', () => {
            const existingDocs = [
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: 'existing-1',
                    file: buildLgFile(99),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 10,
                    position: 1,
                },
            ];

            renderSutWithExistingDocs([], existingDocs);

            expect(screen.getByText(/You have removed all additional files/)).toBeInTheDocument();
            expect(screen.getByText('choose files')).toBeInTheDocument();
        });

        it('adjusts positions correctly when removing a new document in update journey', async () => {
            const user = userEvent.setup();
            const existingDocs = [
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: 'existing-1',
                    file: buildLgFile(99),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 10,
                    position: 1,
                },
            ];

            const newDocuments = [
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '1',
                    file: buildLgFile(1),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 5,
                    position: 2,
                },
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '2',
                    file: buildLgFile(2),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 3,
                    position: 3,
                },
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '3',
                    file: buildLgFile(3),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 2,
                    position: 4,
                },
            ];

            renderSutWithExistingDocs(newDocuments, existingDocs);

            // Remove the middle document (position 3)
            const removeButton = screen.getByRole('button', {
                name: /Remove testFile2.pdf from selection/,
            });
            await user.click(removeButton);

            // Verify that positions are adjusted correctly (existing doc stays at 1, new docs at 2 and 3)
            expect(mockSetDocuments).toHaveBeenCalledWith([
                expect.objectContaining({
                    id: '1',
                    position: 2, // Should remain unchanged
                }),
                expect.objectContaining({
                    id: '3',
                    position: 3, // Should be adjusted from 4 to 3
                }),
            ]);
        });

        it('validates duplicate positions including offset from existing documents', async () => {
            const user = userEvent.setup();
            const existingDocs = [
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: 'existing-1',
                    file: buildLgFile(99),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 10,
                    position: 1,
                },
            ];

            const newDocuments = [
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '1',
                    file: buildLgFile(1),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 5,
                    position: 2,
                },
                {
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    id: '2',
                    file: buildLgFile(2),
                    attempts: 0,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    numPages: 3,
                    position: 3,
                },
            ];

            renderSutWithExistingDocs(newDocuments, existingDocs);

            // Set both documents to the same position (2)
            const firstDocSelect = screen.getByTestId('1');
            const secondDocSelect = screen.getByTestId('2');

            await user.selectOptions(firstDocSelect, '2');
            await user.selectOptions(secondDocSelect, '2');

            const continueButton = screen.getByRole('button', { name: 'Continue' });
            await user.click(continueButton);

            await waitFor(() => {
                expect(screen.getByText('There is a problem')).toBeInTheDocument();
            });
            const errorMessages = screen.getAllByText(
                fileUploadErrorMessages.duplicatePositionError.inline,
            );
            expect(errorMessages.length).toBeGreaterThan(0);
        });
    });
});

function renderSutWithExistingDocs(
    documents: UploadDocument[],
    existingDocuments: UploadDocument[],
): void {
    render(
        <MemoryRouter>
            <DocumentSelectOrderStage
                documents={documents}
                setDocuments={mockSetDocuments}
                setMergedPdfBlob={mockSetMergedPdfBlob}
                existingDocuments={existingDocuments}
            />
        </MemoryRouter>,
    );
}

function renderSut(documents: UploadDocument[]): void {
    render(
        <MemoryRouter>
            <DocumentSelectOrderStage
                documents={documents}
                setDocuments={mockSetDocuments}
                setMergedPdfBlob={mockSetMergedPdfBlob}
                existingDocuments={[]}
            />
        </MemoryRouter>,
    );
}
