import { render, screen } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import {
    DOCUMENT_TYPE,
    DOCUMENT_UPLOAD_STATE,
    UploadDocument,
} from '../../../types/pages/UploadDocumentsPage/types';
import { buildPatientDetails, buildTextFile } from '../../../helpers/test/testBuilders';
import LloydGeorgeUploadStage from './LloydGeorgeUploadingStage';
import usePatient from '../../../helpers/hooks/usePatient';
const mockSetDocuments = jest.fn();
const mockSetStage = jest.fn();
jest.mock('../../../helpers/hooks/usePatient');
jest.mock('../../../helpers/hooks/useBaseAPIHeaders');
const mockedUsePatient = usePatient as jest.Mock;
const mockPatient = buildPatientDetails();
describe('<LloydGeorgeUploadingStage />', () => {
    beforeEach(() => {
        process.env.REACT_APP_ENVIRONMENT = 'jest';
        mockedUsePatient.mockReturnValue(mockPatient);
    });
    afterEach(() => {
        jest.clearAllMocks();
    });

    describe('with NHS number', () => {
        const triggerUploadStateChange = (
            document: UploadDocument,
            state: DOCUMENT_UPLOAD_STATE,
            progress: number,
            attempts: number = 0,
        ) => {
            act(() => {
                document.state = state;
                document.progress = progress;
                document.attempts = attempts;
            });
        };

        it('uploads documents and displays the progress', async () => {
            const documentOne = {
                file: buildTextFile('one', 100),
                state: DOCUMENT_UPLOAD_STATE.UPLOADING,
                id: '1',
                progress: 50,
                docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                attempts: 0,
            };
            render(
                <LloydGeorgeUploadStage
                    documents={[documentOne]}
                    setDocuments={mockSetDocuments}
                    setStage={mockSetStage}
                />,
            );

            triggerUploadStateChange(documentOne, DOCUMENT_UPLOAD_STATE.UPLOADING, 0);

            expect(screen.queryByTestId('upload-document-form')).not.toBeInTheDocument();
            expect(
                screen.getByText(
                    'Do not close or navigate away from this browser until upload is complete. Each file will be uploaded and combined into one record.',
                ),
            ).toBeInTheDocument();
            expect(screen.getByText('50% uploaded...')).toBeInTheDocument();
        });

        it('progress bar reflect the upload progress', async () => {
            const documentOne = {
                file: buildTextFile('one', 100),
                state: DOCUMENT_UPLOAD_STATE.SELECTED,
                id: '1',
                progress: 0,
                docType: DOCUMENT_TYPE.ARF,
                attempts: 0,
            };
            const documentTwo = {
                file: buildTextFile('two', 200),
                state: DOCUMENT_UPLOAD_STATE.SELECTED,
                id: '2',
                progress: 0,
                docType: DOCUMENT_TYPE.ARF,
                attempts: 0,
            };
            const documentThree = {
                file: buildTextFile('three', 100),
                state: DOCUMENT_UPLOAD_STATE.SELECTED,
                id: '3',
                progress: 0,
                docType: DOCUMENT_TYPE.ARF,
                attempts: 0,
            };

            const { rerender } = render(
                <LloydGeorgeUploadStage
                    documents={[documentOne, documentTwo, documentThree]}
                    setDocuments={mockSetDocuments}
                    setStage={mockSetStage}
                />,
            );
            const getProgressBarValue = (document: UploadDocument) => {
                const progressBar: HTMLProgressElement = screen.getByRole('progressbar', {
                    name: `Uploading ${document.file.name}`,
                });
                return progressBar.value;
            };
            const getProgressText = (document: UploadDocument) => {
                return screen.getByRole('status', {
                    name: `${document.file.name} upload status`,
                }).textContent;
            };

            triggerUploadStateChange(documentOne, DOCUMENT_UPLOAD_STATE.UPLOADING, 10);
            rerender(
                <LloydGeorgeUploadStage
                    documents={[documentOne, documentTwo, documentThree]}
                    setDocuments={mockSetDocuments}
                    setStage={mockSetStage}
                />,
            );
            expect(getProgressBarValue(documentOne)).toEqual(10);
            expect(getProgressText(documentOne)).toContain('10% uploaded...');

            triggerUploadStateChange(documentOne, DOCUMENT_UPLOAD_STATE.UPLOADING, 70);
            rerender(
                <LloydGeorgeUploadStage
                    documents={[documentOne, documentTwo, documentThree]}
                    setDocuments={mockSetDocuments}
                    setStage={mockSetStage}
                />,
            );
            expect(getProgressBarValue(documentOne)).toEqual(70);
            expect(getProgressText(documentOne)).toContain('70% uploaded...');

            triggerUploadStateChange(documentTwo, DOCUMENT_UPLOAD_STATE.UPLOADING, 20);
            rerender(
                <LloydGeorgeUploadStage
                    documents={[documentOne, documentTwo, documentThree]}
                    setDocuments={mockSetDocuments}
                    setStage={mockSetStage}
                />,
            );
            expect(getProgressBarValue(documentTwo)).toEqual(20);
            expect(getProgressText(documentTwo)).toContain('20% uploaded...');

            triggerUploadStateChange(documentTwo, DOCUMENT_UPLOAD_STATE.SUCCEEDED, 100);
            rerender(
                <LloydGeorgeUploadStage
                    documents={[documentOne, documentTwo, documentThree]}
                    setDocuments={mockSetDocuments}
                    setStage={mockSetStage}
                />,
            );
            expect(getProgressBarValue(documentTwo)).toEqual(100);
            expect(getProgressText(documentTwo)).toContain('Upload successful');

            //TODO: ADD CASE FOR RETRY UPLOAD

            triggerUploadStateChange(documentOne, DOCUMENT_UPLOAD_STATE.FAILED, 0, 2);
            rerender(
                <LloydGeorgeUploadStage
                    documents={[documentOne, documentTwo, documentThree]}
                    setDocuments={mockSetDocuments}
                    setStage={mockSetStage}
                />,
            );
            expect(getProgressBarValue(documentOne)).toEqual(0);
            expect(getProgressText(documentOne)).toContain('Upload failed');
        });
    });
});
