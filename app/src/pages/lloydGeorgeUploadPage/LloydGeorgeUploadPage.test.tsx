import { render, screen, waitFor } from '@testing-library/react';
import usePatient from '../../helpers/hooks/usePatient';
import {
    buildLgFile,
    buildPatientDetails,
    buildUploadSession,
} from '../../helpers/test/testBuilders';
import LloydGeorgeUploadPage from './LloydGeorgeUploadPage';
import userEvent from '@testing-library/user-event';
import uploadDocuments, {
    uploadConfirmation,
    uploadDocumentToS3,
    virusScanResult,
} from '../../helpers/requests/uploadDocuments';
import { act } from 'react-dom/test-utils';
import { DOCUMENT_TYPE, DOCUMENT_UPLOAD_STATE } from '../../types/pages/UploadDocumentsPage/types';
import { Props } from '../../components/blocks/lloydGeorgeUploadingStage/LloydGeorgeUploadingStage';
jest.mock('../../helpers/requests/uploadDocuments');
jest.mock('../../helpers/hooks/useBaseAPIHeaders');
jest.mock('../../helpers/hooks/useBaseAPIUrl');
jest.mock('../../helpers/hooks/usePatient');
jest.mock('react-router');
const mockedUsePatient = usePatient as jest.Mock;
const mockUploadDocuments = uploadDocuments as jest.Mock;
const mockS3Upload = uploadDocumentToS3 as jest.Mock;
const mockVirusScan = virusScanResult as jest.Mock;
const mockUploadConfirmation = uploadConfirmation as jest.Mock;

const mockPatient = buildPatientDetails();
const lgFile = buildLgFile(1, 1, 'John Doe');
const uploadDocument = {
    file: lgFile,
    state: DOCUMENT_UPLOAD_STATE.SELECTED,
    id: '1',
    progress: 50,
    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
    attempts: 0,
};
jest.mock(
    '../../components/blocks/lloydGeorgeUploadingStage/LloydGeorgeUploadingStage',
    () =>
        ({ documents }: Props) => (
            <>
                <h1>Mock files are uploading stage</h1>
                {documents.map((d) => (
                    <output key={d.id}>{d.file.name}</output>
                ))}
            </>
        ),
);
jest.mock(
    '../../components/blocks/lloydGeorgeUploadCompleteStage/LloydGeorgeUploadCompleteStage',
    () => () => <h1>Mock complete stage</h1>,
);
jest.mock(
    '../../components/blocks/lloydGeorgeUploadInfectedStage/LloydGeorgeUploadInfectedStage',
    () => () => <h1>Mock virus infected stage</h1>,
);
jest.mock(
    '../../components/blocks/lloydGeorgeUploadFailedStage/LloydGeorgeUploadFailedStage',
    () => () => <h1>Mock file failed stage</h1>,
);

describe('UploadDocumentsPage', () => {
    beforeEach(() => {
        process.env.REACT_APP_ENVIRONMENT = 'jest';
        mockedUsePatient.mockReturnValue(mockPatient);
        mockUploadDocuments.mockReturnValue(buildUploadSession([uploadDocument]));
    });
    afterEach(() => {
        jest.clearAllMocks();
    });
    describe('Rendering', () => {
        it('renders initial file input stage', () => {
            render(<LloydGeorgeUploadPage />);
            expect(
                screen.getByRole('heading', { name: 'Upload a Lloyd George record' }),
            ).toBeInTheDocument();
            act(() => {
                userEvent.upload(screen.getByTestId(`button-input`), [lgFile]);
            });
            expect(screen.getByText(lgFile.name)).toBeInTheDocument();
        });

        it('renders uploading stage when submit documents is clicked', async () => {
            mockS3Upload.mockReturnValue(Promise.resolve());
            mockVirusScan.mockReturnValue(DOCUMENT_UPLOAD_STATE.CLEAN);
            mockUploadConfirmation.mockReturnValue(DOCUMENT_UPLOAD_STATE.SUCCEEDED);
            render(<LloydGeorgeUploadPage />);
            expect(
                screen.getByRole('heading', { name: 'Upload a Lloyd George record' }),
            ).toBeInTheDocument();
            act(() => {
                userEvent.upload(screen.getByTestId(`button-input`), [lgFile]);
            });
            expect(screen.getByText(lgFile.name)).toBeInTheDocument();
            expect(screen.getByRole('button', { name: 'Upload' })).toBeInTheDocument();

            act(() => {
                userEvent.click(screen.getByRole('button', { name: 'Upload' }));
            });
            expect(mockUploadDocuments).toHaveBeenCalled();

            expect(
                screen.getByRole('heading', {
                    name: 'Mock files are uploading stage',
                }),
            ).toBeInTheDocument();
            expect(screen.getByText(uploadDocument.file.name)).toBeInTheDocument();

            await waitFor(() => {
                expect(mockS3Upload).toHaveBeenCalled();
            });
            expect(mockVirusScan).toHaveBeenCalled();
            await waitFor(() => {
                expect(mockUploadConfirmation).toHaveBeenCalled();
            });
            await waitFor(() => {
                expect(screen.getByText('Mock complete stage')).toBeInTheDocument();
            });
        });

        it('renders confirmation stage when submit documents is processing', async () => {
            mockS3Upload.mockReturnValue(Promise.resolve());
            mockVirusScan.mockReturnValue(DOCUMENT_UPLOAD_STATE.CLEAN);
            render(<LloydGeorgeUploadPage />);
            expect(
                screen.getByRole('heading', { name: 'Upload a Lloyd George record' }),
            ).toBeInTheDocument();
            act(() => {
                userEvent.upload(screen.getByTestId(`button-input`), [lgFile]);
            });
            expect(screen.getByText(lgFile.name)).toBeInTheDocument();
            expect(screen.getByRole('button', { name: 'Upload' })).toBeInTheDocument();

            act(() => {
                userEvent.click(screen.getByRole('button', { name: 'Upload' }));
            });
            expect(mockUploadDocuments).toHaveBeenCalled();
            await waitFor(() => {
                expect(mockS3Upload).toHaveBeenCalled();
            });
            expect(mockVirusScan).toHaveBeenCalled();
            expect(screen.getByRole('status')).toBeInTheDocument();
            expect(screen.getByText('Checking uploads...')).toBeInTheDocument();
        });

        it('renders complete stage when submit documents is finished', async () => {
            mockS3Upload.mockReturnValue(Promise.resolve());
            mockVirusScan.mockReturnValue(DOCUMENT_UPLOAD_STATE.CLEAN);
            mockUploadConfirmation.mockReturnValue(DOCUMENT_UPLOAD_STATE.SUCCEEDED);
            render(<LloydGeorgeUploadPage />);
            expect(
                screen.getByRole('heading', { name: 'Upload a Lloyd George record' }),
            ).toBeInTheDocument();
            act(() => {
                userEvent.upload(screen.getByTestId(`button-input`), [lgFile]);
            });
            expect(screen.getByText(lgFile.name)).toBeInTheDocument();
            expect(screen.getByRole('button', { name: 'Upload' })).toBeInTheDocument();

            act(() => {
                userEvent.click(screen.getByRole('button', { name: 'Upload' }));
            });
            expect(mockUploadDocuments).toHaveBeenCalled();
            await waitFor(() => {
                expect(mockS3Upload).toHaveBeenCalled();
            });
            expect(mockVirusScan).toHaveBeenCalled();
            await waitFor(() => {
                expect(mockUploadConfirmation).toHaveBeenCalled();
            });
            await waitFor(() => {
                expect(screen.getByText('Mock complete stage')).toBeInTheDocument();
            });
        });

        it('renders file infected stage when virus scan fails', async () => {
            mockS3Upload.mockReturnValue(Promise.resolve());
            mockVirusScan.mockReturnValue(DOCUMENT_UPLOAD_STATE.INFECTED);
            render(<LloydGeorgeUploadPage />);
            expect(
                screen.getByRole('heading', { name: 'Upload a Lloyd George record' }),
            ).toBeInTheDocument();
            act(() => {
                userEvent.upload(screen.getByTestId(`button-input`), [lgFile]);
            });
            expect(screen.getByText(lgFile.name)).toBeInTheDocument();
            expect(screen.getByRole('button', { name: 'Upload' })).toBeInTheDocument();

            act(() => {
                userEvent.click(screen.getByRole('button', { name: 'Upload' }));
            });
            expect(mockUploadDocuments).toHaveBeenCalled();
            await waitFor(() => {
                expect(mockS3Upload).toHaveBeenCalled();
            });
            expect(mockVirusScan).toHaveBeenCalled();
            expect(screen.getByText('Mock virus infected stage')).toBeInTheDocument();
        });

        it('renders file upload failed stage when file upload fails', async () => {
            mockS3Upload.mockReturnValue(Promise.resolve());
            mockVirusScan.mockReturnValue(DOCUMENT_UPLOAD_STATE.CLEAN);
            mockUploadConfirmation.mockImplementation(() =>
                Promise.reject({
                    response: {
                        status: 400,
                    },
                }),
            );
            render(<LloydGeorgeUploadPage />);
            expect(
                screen.getByRole('heading', { name: 'Upload a Lloyd George record' }),
            ).toBeInTheDocument();
            act(() => {
                userEvent.upload(screen.getByTestId(`button-input`), [lgFile]);
            });
            expect(screen.getByText(lgFile.name)).toBeInTheDocument();
            expect(screen.getByRole('button', { name: 'Upload' })).toBeInTheDocument();

            act(() => {
                userEvent.click(screen.getByRole('button', { name: 'Upload' }));
            });
            expect(mockUploadDocuments).toHaveBeenCalled();
            await waitFor(() => {
                expect(mockS3Upload).toHaveBeenCalled();
            });
            expect(mockVirusScan).toHaveBeenCalled();
            await waitFor(() => {
                expect(mockUploadConfirmation).toHaveBeenCalled();
            });
            await waitFor(() => {
                expect(screen.getByText('Mock file failed stage')).toBeInTheDocument();
            });
        });
    });
});
