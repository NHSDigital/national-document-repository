// need to use happy-dom for this test file as jsdom doesn't support DOMMatrix https://github.com/jsdom/jsdom/issues/2647
// @vitest-environment happy-dom
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';
import DocumentSelectFileErrorsPage from './DocumentSelectFileErrorsPage';
import {
    UploadDocument,
    DOCUMENT_UPLOAD_STATE,
} from '../../../../types/pages/UploadDocumentsPage/types';
import { UPLOAD_FILE_ERROR_TYPE } from '../../../../helpers/utils/fileUploadErrorMessages';
import { routes } from '../../../../types/generic/routes';
import { useLocation } from 'react-router-dom';

vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return {
        ...actual,
        useLocation: vi.fn(),
    };
});

const mockedUseLocation = vi.mocked(useLocation);

const createFailedDocument = (name: string, error: UPLOAD_FILE_ERROR_TYPE): UploadDocument => ({
    id: `${name}-id`,
    file: new File(['test content'], name, { type: 'application/pdf' }),
    state: DOCUMENT_UPLOAD_STATE.FAILED,
    docType: undefined as any,
    error,
    attempts: 0,
    progress: 0,
    numPages: 0,
    validated: true,
});

const setup = (failedDocuments: UploadDocument[] = []): void => {
    mockedUseLocation.mockReturnValue({
        state: { failedDocuments },
    } as any);
    render(
        <MemoryRouter>
            <DocumentSelectFileErrorsPage />
        </MemoryRouter>,
    );
};

describe('DocumentSelectFileErrorsPage', () => {
    afterEach(() => {
        vi.clearAllMocks();
    });

    it('renders all static page content', () => {
        setup([]);

        expect(
            screen.getByRole('heading', { name: 'We could not upload your files' }),
        ).toBeInTheDocument();

        expect(
            screen.getByText('There was a problem with your files, so we stopped the upload.'),
        ).toBeInTheDocument();

        expect(screen.getByText('Files with problems')).toBeInTheDocument();

        expect(screen.getByText('What you need to do')).toBeInTheDocument();

        expect(
            screen.getByText(
                "You'll need to resolve the problems with these files then upload all the files again. To make sure patient records are complete, you must upload all files patient at the same time.",
            ),
        ).toBeInTheDocument();

        expect(screen.getByText('Get help')).toBeInTheDocument();

        expect(
            screen.getByText(
                'Contact your local IT support desk to resolve the problems with these files.',
            ),
        ).toBeInTheDocument();

        const helpLink = screen.getByRole('link', {
            name: /Help and guidance - this link will open in a new tab/i,
        });
        expect(helpLink).toBeInTheDocument();
        expect(helpLink).toHaveAttribute(
            'href',
            'https://digital.nhs.uk/services/access-and-store-digital-patient-documents/help-and-guidance',
        );
        expect(helpLink).toHaveAttribute('target', '_blank');
        expect(helpLink).toHaveAttribute('rel', 'noreferrer');

        const backLink = screen.getByRole('link', { name: 'Go to home' });
        expect(backLink).toHaveAttribute('href', routes.HOME);
    });

    it.each([
        {
            error: UPLOAD_FILE_ERROR_TYPE.invalidPdf,
            expectedMessage: 'This file is damaged or unreadable.',
        },
        {
            error: UPLOAD_FILE_ERROR_TYPE.emptyPdf,
            expectedMessage: 'This file is empty.',
        },
        {
            error: UPLOAD_FILE_ERROR_TYPE.passwordProtected,
            expectedMessage: 'This file is password protected.',
        },
    ])('displays correct error message for "$error" file', ({ error, expectedMessage }) => {
        const fileName = `file-${error}.pdf`;
        const doc = createFailedDocument(fileName, error);
        setup([doc]);

        expect(screen.getByText(fileName)).toBeInTheDocument();
        expect(screen.getByText(expectedMessage)).toBeInTheDocument();
    });

    it('renders multiple error files correctly', () => {
        const docs = [
            createFailedDocument('bad1.pdf', UPLOAD_FILE_ERROR_TYPE.invalidPdf),
            createFailedDocument('bad2.pdf', UPLOAD_FILE_ERROR_TYPE.passwordProtected),
        ];
        setup(docs);

        const expectedMessageInvalidPdf = 'This file is damaged or unreadable.';
        const expectedMessagePasswordProtected = 'This file is password protected.';

        expect(screen.getByText('bad1.pdf')).toBeInTheDocument();
        expect(screen.getByText(expectedMessageInvalidPdf)).toBeInTheDocument();

        expect(screen.getByText('bad2.pdf')).toBeInTheDocument();
        expect(screen.getByText(expectedMessagePasswordProtected)).toBeInTheDocument();
    });
});
