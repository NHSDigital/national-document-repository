import React, { useEffect, useRef, useState } from 'react';
import LloydGeorgeUploadingStage from '../../components/blocks/lloydGeorgeUploadingStage/LloydGeorgeUploadingStage';
import { DOCUMENT_UPLOAD_STATE, UploadDocument } from '../../types/pages/UploadDocumentsPage/types';
import LloydGeorgeFileInputStage from '../../components/blocks/lloydGeorgeFileInputStage/LloydGeorgeFileInputStage';
import LloydGeorgeUploadInfectedStage from '../../components/blocks/lloydGeorgeUploadInfectedStage/LloydGeorgeUploadInfectedStage';
import LloydGeorgeUploadCompleteStage from '../../components/blocks/lloydGeorgeUploadCompleteStage/LloydGeorgeUploadCompleteStage';
import LloydGeorgeUploadFailedStage from '../../components/blocks/lloydGeorgeUploadFailedStage/LloydGeorgeUploadFailedStage';
import { UploadSession } from '../../types/generic/uploadResult';
import uploadDocuments, {
    setDocument,
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

export enum LG_UPLOAD_STAGE {
    SELECT = 0,
    UPLOAD = 1,
    COMPLETE = 2,
    INFECTED = 3,
    FAILED = 4,
    CONFIRMATION = 5,
}

function LloydGeorgeUploadPage() {
    const patientDetails = usePatient();
    const nhsNumber: string = patientDetails?.nhsNumber ?? '';
    const baseUrl = useBaseAPIUrl();
    const baseHeaders = useBaseAPIHeaders();
    const [stage, setStage] = useState<LG_UPLOAD_STAGE>(LG_UPLOAD_STAGE.SELECT);
    const [documents, setDocuments] = useState<Array<UploadDocument>>([]);
    const [uploadSession, setUploadSession] = useState<UploadSession | null>(null);
    const mounted = useRef(false);

    useEffect(() => {
        const hasExceededUploadAttempts = documents.length && documents.some((d) => d.attempts > 1);
        const hasVirus =
            documents.length && documents.some((d) => d.state === DOCUMENT_UPLOAD_STATE.INFECTED);
        const hasNoVirus =
            documents.length && documents.every((d) => d.state === DOCUMENT_UPLOAD_STATE.CLEAN);

        const boolTest = documents.every((d) => d.state === DOCUMENT_UPLOAD_STATE.CLEAN);
        console.log('HAS NO VIRUS:', hasNoVirus);
        console.log('TEST NO VIRUS:', boolTest);

        const confirmUpload = async () => {
            if (uploadSession) {
                mounted.current = true;
                console.log('SETTING STAGE');

                setStage(LG_UPLOAD_STAGE.CONFIRMATION);
                console.log('SENDING REQUEST');

                await uploadConfirmation({
                    baseUrl,
                    baseHeaders,
                    nhsNumber,
                    uploadSession,
                    documents,
                });
                setDocuments((prevState) =>
                    prevState.map((document) => ({
                        ...document,
                        state: DOCUMENT_UPLOAD_STATE.SUCCEEDED,
                    })),
                );
                setStage(LG_UPLOAD_STAGE.COMPLETE);
            }
        };

        if (hasExceededUploadAttempts) {
            setStage(LG_UPLOAD_STAGE.FAILED);
        }
        if (hasVirus) {
            setStage(LG_UPLOAD_STAGE.INFECTED);
        }
        if (hasNoVirus && !mounted.current) {
            console.log('ATTEMPTING CONFIRMATION');
            void confirmUpload();
        }
    }, [baseHeaders, baseUrl, documents, nhsNumber, setDocuments, setStage, uploadSession]);

    const uploadAndScanDocuments = (
        documents: Array<UploadDocument>,
        uploadSession: UploadSession,
    ) => {
        documents.forEach(async (document) => {
            const documentMetadata = uploadSession[document.file.name];
            const documentReference = documentMetadata.fields.key;
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
            setDocument(setDocuments, {
                id: document.id,
                state: virusDocumentState,
                progress: 100,
            });
        });
    };

    const submitDocuments = async () => {
        try {
            setStage(LG_UPLOAD_STAGE.UPLOAD);
            const uploadSession = await uploadDocuments({
                nhsNumber,
                setDocuments,
                documents,
                baseUrl,
                baseHeaders,
            });
            setUploadSession(uploadSession);
            uploadAndScanDocuments(documents, uploadSession);
        } catch (e) {
            const error = e as AxiosError;
            if (isMock(error)) {
                setDocuments(
                    documents.map((document) => ({
                        ...document,
                        state: DOCUMENT_UPLOAD_STATE.SUCCEEDED,
                    })),
                );
                setStage(LG_UPLOAD_STAGE.COMPLETE);
            }
        }
    };

    const restartUpload = () => {
        setDocuments([]);
        setStage(LG_UPLOAD_STAGE.SELECT);
    };

    switch (stage) {
        case LG_UPLOAD_STAGE.SELECT:
            return (
                <LloydGeorgeFileInputStage
                    documents={documents}
                    setDocuments={setDocuments}
                    submitDocuments={submitDocuments}
                />
            );
        case LG_UPLOAD_STAGE.UPLOAD:
            return (
                <LloydGeorgeUploadingStage
                    documents={documents}
                    uploadSession={uploadSession}
                    uploadAndScanDocuments={uploadAndScanDocuments}
                />
            );
        case LG_UPLOAD_STAGE.COMPLETE:
            return <LloydGeorgeUploadCompleteStage documents={documents} />;
        case LG_UPLOAD_STAGE.INFECTED:
            return (
                <LloydGeorgeUploadInfectedStage
                    documents={documents}
                    restartUpload={restartUpload}
                />
            );
        case LG_UPLOAD_STAGE.FAILED:
            return <LloydGeorgeUploadFailedStage restartUpload={restartUpload} />;
        case LG_UPLOAD_STAGE.CONFIRMATION:
            return <Spinner status="Uploading..." />;
        default:
            return null;
    }
}

export default LloydGeorgeUploadPage;
