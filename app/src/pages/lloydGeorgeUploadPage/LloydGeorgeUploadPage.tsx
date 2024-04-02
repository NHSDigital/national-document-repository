import React, { Dispatch, SetStateAction, useEffect, useRef, useState } from 'react';
import LloydGeorgeUploadingStage from '../../components/blocks/lloydGeorgeUploadingStage/LloydGeorgeUploadingStage';
import { DOCUMENT_UPLOAD_STATE, UploadDocument } from '../../types/pages/UploadDocumentsPage/types';
import LloydGeorgeFileInputStage from '../../components/blocks/lloydGeorgeFileInputStage/LloydGeorgeFileInputStage';
import LloydGeorgeUploadInfectedStage from '../../components/blocks/lloydGeorgeUploadInfectedStage/LloydGeorgeUploadInfectedStage';
import LloydGeorgeUploadCompleteStage from '../../components/blocks/lloydGeorgeUploadCompleteStage/LloydGeorgeUploadCompleteStage';
import LloydGeorgeUploadFailedStage from '../../components/blocks/lloydGeorgeUploadFailedStage/LloydGeorgeUploadFailedStage';
import { UploadSession } from '../../types/generic/uploadResult';
import uploadDocuments, {
    updateDocumentState,
    uploadConfirmation,
    uploadDocumentToS3,
    virusScanResult,
} from '../../helpers/requests/uploadDocuments';
import usePatient from '../../helpers/hooks/usePatient';
import useBaseAPIUrl from '../../helpers/hooks/useBaseAPIUrl';
import useBaseAPIHeaders from '../../helpers/hooks/useBaseAPIHeaders';
import { AxiosError } from 'axios';
import { isMock } from '../../helpers/utils/isLocal';
import Spinner from '../../components/generic/spinner/Spinner';
import { routes } from '../../types/generic/routes';
import { useNavigate } from 'react-router';
import { errorToParams } from '../../helpers/utils/errorToParams';

export enum LG_UPLOAD_STAGE {
    SELECT = 0,
    UPLOAD = 1,
    COMPLETE = 2,
    INFECTED = 3,
    FAILED = 4,
    CONFIRMATION = 5,
}

type UpdateDocumentArgs = {
    id: string;
    state: DOCUMENT_UPLOAD_STATE;
    progress?: number | 'scan';
    attempts?: number;
};

export const setDocument = (
    setDocuments: Dispatch<SetStateAction<UploadDocument[]>>,
    { id, state, progress, attempts }: UpdateDocumentArgs,
) => {
    setDocuments((prevState) =>
        prevState.map((document) => {
            if (document.id === id) {
                if (progress === 'scan') {
                    progress = undefined;
                } else {
                    progress = progress ?? document.progress;
                }
                attempts = attempts ?? document.attempts;
                state = state ?? document.state;

                return { ...document, state, progress, attempts };
            }
            return document;
        }),
    );
};

function LloydGeorgeUploadPage() {
    const patientDetails = usePatient();
    const nhsNumber: string = patientDetails?.nhsNumber ?? '';
    const baseUrl = useBaseAPIUrl();
    const baseHeaders = useBaseAPIHeaders();
    const [stage, setStage] = useState<LG_UPLOAD_STAGE>(LG_UPLOAD_STAGE.SELECT);
    const [documents, setDocuments] = useState<Array<UploadDocument>>([]);
    const [uploadSession, setUploadSession] = useState<UploadSession | null>(null);
    const confirmed = useRef(false);
    const navigate = useNavigate();
    let intervalTimer: number = 0;

    useEffect(() => {
        const hasExceededUploadAttempts = documents.some((d) => d.attempts > 1);
        const hasVirus = documents.some((d) => d.state === DOCUMENT_UPLOAD_STATE.INFECTED);
        const hasNoVirus =
            documents.length && documents.every((d) => d.state === DOCUMENT_UPLOAD_STATE.CLEAN);
        window.clearInterval(intervalTimer);

        const confirmUpload = async () => {
            if (uploadSession) {
                setStage(LG_UPLOAD_STAGE.CONFIRMATION);
                try {
                    const confirmDocumentState = await uploadConfirmation({
                        baseUrl,
                        baseHeaders,
                        nhsNumber,
                        uploadSession,
                        documents,
                    });
                    setDocuments((prevState) =>
                        prevState.map((document) => ({
                            ...document,
                            state: confirmDocumentState,
                        })),
                    );
                    setStage(LG_UPLOAD_STAGE.COMPLETE);
                } catch (e) {
                    const error = e as AxiosError;
                    if (error.response?.status === 403) {
                        navigate(routes.START);
                        return;
                    }
                    setStage(LG_UPLOAD_STAGE.FAILED);
                }
            }
        };

        if (hasExceededUploadAttempts) {
            setStage(LG_UPLOAD_STAGE.FAILED);
        } else if (hasVirus) {
            setStage(LG_UPLOAD_STAGE.INFECTED);
        } else if (hasNoVirus && !confirmed.current) {
            confirmed.current = true;
            void confirmUpload();
        }
    }, [
        baseHeaders,
        baseUrl,
        documents,
        navigate,
        nhsNumber,
        setDocuments,
        setStage,
        uploadSession,
        intervalTimer,
    ]);

    const uploadAndScanDocuments = (
        uploadDocuments: Array<UploadDocument>,
        uploadSession: UploadSession,
    ) => {
        uploadDocuments.forEach(async (document) => {
            const documentMetadata = uploadSession[document.file.name];
            const documentReference = documentMetadata.fields.key;
            intervalTimer = startIntervalTimer(documentReference, document);
            try {
                await uploadDocumentToS3({ setDocuments, document, uploadSession });
                setDocument(setDocuments, {
                    id: document.id,
                    state: DOCUMENT_UPLOAD_STATE.SCANNING,
                    progress: 'scan',
                });
                const virusDocumentState = await virusScanResult({
                    documentReference,
                    baseUrl,
                    baseHeaders,
                });
                window.clearInterval(intervalTimer);
                setDocument(setDocuments, {
                    id: document.id,
                    state: virusDocumentState,
                    progress: 100,
                });
            } catch (e) {
                window.clearInterval(intervalTimer);
                setDocument(setDocuments, {
                    id: document.id,
                    state: DOCUMENT_UPLOAD_STATE.FAILED,
                    attempts: document.attempts + 1,
                    progress: 0,
                });
                await updateDocumentUploadingState(documentReference, document, false);
            }
        });
    };

    const submitDocuments = async () => {
        try {
            setStage(LG_UPLOAD_STAGE.UPLOAD);
            const uploadSession = await uploadDocuments({
                nhsNumber,
                documents,
                baseUrl,
                baseHeaders,
            });
            setUploadSession(uploadSession);
            uploadAndScanDocuments(documents, uploadSession);
        } catch (e) {
            const error = e as AxiosError;
            if (error.response?.status === 403) {
                navigate(routes.START);
            } else if (error.response?.status === 423) {
                navigate(routes.SERVER_ERROR + errorToParams(error));
            } else if (isMock(error)) {
                setDocuments((prevState) =>
                    prevState.map((doc) => ({
                        ...doc,
                        state: DOCUMENT_UPLOAD_STATE.SUCCEEDED,
                    })),
                );
                setStage(LG_UPLOAD_STAGE.COMPLETE);
            } else {
                setDocuments((prevState) =>
                    prevState.map((doc) => ({
                        ...doc,
                        state: DOCUMENT_UPLOAD_STATE.FAILED,
                        attempts: doc.attempts + 1,
                        progress: 0,
                    })),
                );
            }
        }
    };
    const updateDocumentUploadingState = async (
        documentReference: string,
        document: UploadDocument,
        uploadingState: boolean,
    ) => {
        await updateDocumentState({
            document,
            uploadingState: uploadingState,
            documentReference,
            baseUrl,
            baseHeaders,
        });
    };
    const restartUpload = () => {
        setDocuments([]);
        setStage(LG_UPLOAD_STAGE.SELECT);
    };
    const startIntervalTimer = (documentReference: string, document: UploadDocument) => {
        return window.setInterval(async () => {
            await updateDocumentUploadingState(documentReference, document, true);
        }, 120000);
    };

    switch (stage) {
        case LG_UPLOAD_STAGE.SELECT:
            window.clearInterval(intervalTimer);
            return (
                <LloydGeorgeFileInputStage
                    documents={documents}
                    setDocuments={setDocuments}
                    submitDocuments={submitDocuments}
                />
            );
        case LG_UPLOAD_STAGE.UPLOAD:
            window.clearInterval(intervalTimer);
            return (
                <LloydGeorgeUploadingStage
                    documents={documents}
                    uploadSession={uploadSession}
                    uploadAndScanDocuments={uploadAndScanDocuments}
                />
            );
        case LG_UPLOAD_STAGE.COMPLETE:
            window.clearInterval(intervalTimer);
            return <LloydGeorgeUploadCompleteStage documents={documents} />;
        case LG_UPLOAD_STAGE.INFECTED:
            window.clearInterval(intervalTimer);
            return (
                <LloydGeorgeUploadInfectedStage
                    documents={documents}
                    restartUpload={restartUpload}
                />
            );
        case LG_UPLOAD_STAGE.FAILED:
            window.clearInterval(intervalTimer);
            return <LloydGeorgeUploadFailedStage restartUpload={restartUpload} />;
        case LG_UPLOAD_STAGE.CONFIRMATION:
            window.clearInterval(intervalTimer);
            return <Spinner status="Checking uploads..." />;
        default:
            window.clearInterval(intervalTimer);
            return null;
    }
}

export default LloydGeorgeUploadPage;
