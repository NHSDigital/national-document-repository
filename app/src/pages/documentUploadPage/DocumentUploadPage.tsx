import { useEffect, useRef, useState } from 'react';
import {
    DOCUMENT_STATUS,
    DOCUMENT_TYPE,
    DOCUMENT_UPLOAD_STATE,
    UploadDocument,
} from '../../types/pages/UploadDocumentsPage/types';
import {
    DocumentStatusResult,
    S3UploadFields,
    UploadSession,
} from '../../types/generic/uploadResult';
import uploadDocuments, {
    generateFileName,
    getDocumentStatus,
    uploadDocumentToS3,
} from '../../helpers/requests/uploadDocuments';
import usePatient from '../../helpers/hooks/usePatient';
import useBaseAPIUrl from '../../helpers/hooks/useBaseAPIUrl';
import useBaseAPIHeaders from '../../helpers/hooks/useBaseAPIHeaders';
import { AxiosError } from 'axios';
import { isLocal, isMock } from '../../helpers/utils/isLocal';
import { routeChildren, routes } from '../../types/generic/routes';
import { Outlet, Route, Routes, useLocation } from 'react-router-dom';
import { errorCodeToParams, errorToParams } from '../../helpers/utils/errorToParams';
import { getLastURLPath, useEnhancedNavigate } from '../../helpers/utils/urlManipulations';
import {
    markDocumentsAsUploading,
    setSingleDocument,
} from '../../helpers/utils/uploadDocumentHelpers';
import DocumentSelectStage from '../../components/blocks/_documentUpload/documentSelectStage/DocumentSelectStage';
import DocumentSelectOrderStage from '../../components/blocks/_documentUpload/documentSelectOrderStage/DocumentSelectOrderStage';
import DocumentUploadConfirmStage from '../../components/blocks/_documentUpload/documentUploadConfirmStage/DocumentUploadConfirmStage';
import DocumentUploadingStage from '../../components/blocks/_documentUpload/documentUploadingStage/DocumentUploadingStage';
import { v4 as uuidv4 } from 'uuid';
import DocumentUploadCompleteStage from '../../components/blocks/_documentUpload/documentUploadCompleteStage/DocumentUploadCompleteStage';
import DocumentUploadRemoveFilesStage from '../../components/blocks/_documentUpload/documentUploadRemoveFilesStage/DocumentUploadRemoveFilesStage';
import useConfig from '../../helpers/hooks/useConfig';
import DocumentUploadInfectedStage from '../../components/blocks/_documentUpload/documentUploadInfectedStage/DocumentUploadInfectedStage';
import DocumentSelectFileErrorsPage from '../../components/blocks/_documentUpload/documentSelectFileErrorsPage/DocumentSelectFileErrorsPage';

type LocationState = {
    existingDocuments?: [
        {
            docType: DOCUMENT_TYPE | null;
            blob: Blob | null;
            fileName: string | null;
        },
    ];
};

type LocationParams<T> = {
    pathname: string;
    state: T | undefined;
    search: string;
    hash: string;
    key: string;
};

const DocumentUploadPage = (): React.JSX.Element => {
    const patientDetails = usePatient();
    const nhsNumber: string = patientDetails?.nhsNumber ?? '';
    const baseUrl = useBaseAPIUrl();
    const location: LocationParams<LocationState> = useLocation();
    const baseHeaders = useBaseAPIHeaders();
    const [documents, setDocuments] = useState<Array<UploadDocument>>([]);
    const [existingDocuments, setExistingDocuments] = useState<Array<UploadDocument>>([]);
    const [uploadSession, setUploadSession] = useState<UploadSession | null>(null);
    const completeRef = useRef(false);
    const virusReference = useRef(false);
    const navigate = useEnhancedNavigate();
    const [intervalTimer, setIntervalTimer] = useState(0);
    const [mergedPdfBlob, setMergedPdfBlob] = useState<Blob>();
    const config = useConfig();
    const interval = useRef<number>(0);
    const filesErrorPageRef = useRef(false);

    const UPDATE_DOCUMENT_STATE_FREQUENCY_MILLISECONDS = 5000;
    const MAX_POLLING_TIME = 120000;

    useEffect(() => {
        const searchParams = new URLSearchParams(location.search);
        const journey = searchParams.get('journey');

        if (journey === 'upload' && !location.state?.existingDocuments?.[0]?.blob) {
            // TODO: request new record
            return;
        }

        const newDocuments: Array<UploadDocument> =
            location.state?.existingDocuments?.map(
                (doc) =>
                    ({
                        id: uuidv4(),
                        file: new File([doc.blob!], doc.fileName!, { type: 'application/pdf' }),
                        state: DOCUMENT_UPLOAD_STATE.SELECTED,
                        docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                        progress: 0,
                    }) as UploadDocument,
            ) ?? [];

        setExistingDocuments(newDocuments);
    }, []);

    useEffect(() => {
        if (interval.current * UPDATE_DOCUMENT_STATE_FREQUENCY_MILLISECONDS > MAX_POLLING_TIME) {
            window.clearInterval(intervalTimer);
            navigate(routes.SERVER_ERROR);
            return;
        }

        const hasVirus = documents.some((d) => d.state === DOCUMENT_UPLOAD_STATE.INFECTED);
        const docWithError = documents.find((d) => d.state === DOCUMENT_UPLOAD_STATE.ERROR);
        const allFinished =
            documents.length > 0 &&
            documents.every((d) => d.state === DOCUMENT_UPLOAD_STATE.SUCCEEDED);

        if (hasVirus && !virusReference.current) {
            virusReference.current = true;
            window.clearInterval(intervalTimer);
            navigate(routeChildren.DOCUMENT_UPLOAD_INFECTED);
        } else if (docWithError) {
            const errorParams = docWithError.error ? errorCodeToParams(docWithError.error) : '';
            navigate(routes.SERVER_ERROR + errorParams);
        } else if (allFinished && !completeRef.current) {
            completeRef.current = true;
            window.clearInterval(intervalTimer);
            navigate.withParams(routeChildren.DOCUMENT_UPLOAD_COMPLETED);
        }
    }, [
        baseHeaders,
        baseUrl,
        documents,
        navigate,
        nhsNumber,
        setDocuments,
        uploadSession,
        intervalTimer,
    ]);

    useEffect(() => {
        return (): void => {
            window.clearInterval(intervalTimer);
        };
    }, [intervalTimer]);

    const uploadSingleLloydGeorgeDocument = async (
        document: UploadDocument,
        uploadSession: UploadSession,
    ): Promise<void> => {
        try {
            await uploadDocumentToS3({
                document,
                uploadSession,
                setDocuments,
            });
        } catch (e) {
            window.clearInterval(intervalTimer);
            markDocumentAsFailed(document);

            const error = e as AxiosError;
            navigate(routes.SERVER_ERROR + errorToParams(error));
        }
    };

    const markDocumentAsFailed = (document: UploadDocument): void => {
        setSingleDocument(setDocuments, {
            id: document.id,
            state: DOCUMENT_UPLOAD_STATE.ERROR,
            progress: 0,
        });
    };

    const uploadAllDocuments = (
        uploadDocuments: Array<UploadDocument>,
        uploadSession: UploadSession,
    ): void => {
        uploadDocuments.forEach((document) => {
            if (document.docType === DOCUMENT_TYPE.LLOYD_GEORGE) {
                void uploadSingleLloydGeorgeDocument(document, uploadSession);
            }
        });
    };

    const getMockUploadSession = (documents: UploadDocument[]): UploadSession => {
        const session: UploadSession = {};
        documents.forEach((doc) => {
            session[doc.id] = {
                url: 'https://example.com',
                fields: {
                    key: `https://example.com/${uuidv4()}`,
                } as S3UploadFields,
            };
        });

        return session;
    };

    const startUpload = async (): Promise<void> => {
        try {
            let reducedDocuments = documents;

            if (
                reducedDocuments.some((doc) => doc.docType === DOCUMENT_TYPE.LLOYD_GEORGE) &&
                mergedPdfBlob
            ) {
                reducedDocuments = reducedDocuments.filter(
                    (doc) => doc.docType !== DOCUMENT_TYPE.LLOYD_GEORGE,
                );

                const filename = generateFileName(patientDetails);
                reducedDocuments.push({
                    id: uuidv4(),
                    file: new File([mergedPdfBlob], filename, { type: 'application/pdf' }),
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    progress: 0,
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    attempts: 0,
                });
            }

            const uploadSession: UploadSession = isLocal
                ? getMockUploadSession(reducedDocuments)
                : await uploadDocuments({
                      nhsNumber,
                      documents: reducedDocuments,
                      baseUrl,
                      baseHeaders,
                  });

            setUploadSession(uploadSession);
            const uploadingDocuments = markDocumentsAsUploading(reducedDocuments, uploadSession);
            setDocuments(uploadingDocuments);

            if (!isLocal) {
                uploadAllDocuments(uploadingDocuments, uploadSession);
            }

            const updateStateInterval = startIntervalTimer(uploadingDocuments);
            setIntervalTimer(updateStateInterval);
        } catch (e) {
            const error = e as AxiosError;
            if (error.response?.status === 403) {
                navigate(routes.SESSION_EXPIRED);
            } else if (isMock(error)) {
                setDocuments((prevState) =>
                    prevState.map((doc) => ({
                        ...doc,
                        state: DOCUMENT_UPLOAD_STATE.SUCCEEDED,
                    })),
                );
                window.clearInterval(intervalTimer);
                navigate.withParams(routeChildren.DOCUMENT_UPLOAD_COMPLETED);
            } else {
                navigate(routes.SERVER_ERROR + errorToParams(error));
            }
        }
    };

    const handleDocStatusResult = (documentStatusResult: DocumentStatusResult): void => {
        setDocuments((previousState) =>
            previousState.map((doc) => {
                const docStatus = documentStatusResult[doc.ref!];

                const updatedDoc = {
                    ...doc,
                };

                switch (docStatus?.status) {
                    case DOCUMENT_STATUS.FINAL:
                        updatedDoc.state = DOCUMENT_UPLOAD_STATE.SUCCEEDED;
                        break;

                    case DOCUMENT_STATUS.INFECTED:
                        updatedDoc.state = DOCUMENT_UPLOAD_STATE.INFECTED;
                        break;

                    case DOCUMENT_STATUS.NOT_FOUND:
                    case DOCUMENT_STATUS.CANCELLED:
                        updatedDoc.state = DOCUMENT_UPLOAD_STATE.ERROR;
                        updatedDoc.errorCode = docStatus.error_code;
                        break;
                }

                return updatedDoc;
            }),
        );
    };

    const startIntervalTimer = (uploadDocuments: Array<UploadDocument>): number => {
        return window.setInterval(async () => {
            interval.current = interval.current + 1;
            if (isLocal) {
                const updatedDocuments = uploadDocuments.map((doc) => {
                    const min = (doc.progress ?? 0) + 40;
                    const max = 70;
                    doc.progress = Math.random() * (min + max - (min + 1)) + min;
                    doc.progress = doc.progress > 100 ? 100 : doc.progress;
                    if (doc.progress < 100) {
                        doc.state = DOCUMENT_UPLOAD_STATE.UPLOADING;
                    } else if (doc.state !== DOCUMENT_UPLOAD_STATE.SCANNING) {
                        doc.state = DOCUMENT_UPLOAD_STATE.SCANNING;
                    } else {
                        const hasVirusFile = documents.filter(
                            (d) => d.file.name.toLocaleLowerCase() === 'virus.pdf',
                        );
                        const hasFailedFile = documents.filter(
                            (d) => d.file.name.toLocaleLowerCase() === 'virus-failed.pdf',
                        );
                        hasVirusFile.length > 0
                            ? (doc.state = DOCUMENT_UPLOAD_STATE.INFECTED)
                            : hasFailedFile.length > 0
                              ? (doc.state = DOCUMENT_UPLOAD_STATE.FAILED)
                              : (doc.state = DOCUMENT_UPLOAD_STATE.SUCCEEDED);
                    }

                    return doc;
                });
                setDocuments(updatedDocuments);
            } else {
                try {
                    const documentStatusResult = await getDocumentStatus({
                        documents: uploadDocuments,
                        baseUrl,
                        baseHeaders,
                        nhsNumber,
                    });

                    handleDocStatusResult(documentStatusResult);
                } catch (e) {
                    const error = e as AxiosError;
                    navigate(routes.SERVER_ERROR + errorToParams(error));
                }
            }
        }, UPDATE_DOCUMENT_STATE_FREQUENCY_MILLISECONDS);
    };

    if (
        !config.featureFlags.uploadLambdaEnabled ||
        !config.featureFlags.uploadLloydGeorgeWorkflowEnabled
    ) {
        navigate(routes.HOME);
        return <></>;
    }

    return (
        <div>
            <Routes>
                <Route
                    index
                    element={
                        <DocumentSelectStage
                            documents={documents}
                            setDocuments={setDocuments}
                            documentType={DOCUMENT_TYPE.LLOYD_GEORGE}
                            filesErrorRef={filesErrorPageRef}
                        />
                    }
                />
                <Route
                    path={getLastURLPath(routeChildren.DOCUMENT_UPLOAD_SELECT_ORDER) + '/*'}
                    element={
                        <DocumentSelectOrderStage
                            documents={documents}
                            setDocuments={setDocuments}
                            setMergedPdfBlob={setMergedPdfBlob}
                            existingDocuments={existingDocuments}
                        />
                    }
                />
                <Route
                    path={getLastURLPath(routeChildren.DOCUMENT_UPLOAD_REMOVE_ALL) + '/*'}
                    element={
                        <DocumentUploadRemoveFilesStage
                            documents={documents}
                            setDocuments={setDocuments}
                            documentType={DOCUMENT_TYPE.LLOYD_GEORGE}
                        />
                    }
                />
                <Route
                    path={getLastURLPath(routeChildren.DOCUMENT_UPLOAD_CONFIRMATION) + '/*'}
                    element={<DocumentUploadConfirmStage documents={documents} />}
                />
                <Route
                    path={getLastURLPath(routeChildren.DOCUMENT_UPLOAD_UPLOADING) + '/*'}
                    element={
                        <DocumentUploadingStage documents={documents} startUpload={startUpload} />
                    }
                />
                <Route
                    path={getLastURLPath(routeChildren.DOCUMENT_UPLOAD_COMPLETED) + '/*'}
                    element={<DocumentUploadCompleteStage documents={documents} />}
                />
                <Route
                    path={getLastURLPath(routeChildren.DOCUMENT_UPLOAD_INFECTED) + '/*'}
                    element={<DocumentUploadInfectedStage />}
                />
                <Route
                    path={getLastURLPath(routeChildren.DOCUMENT_UPLOAD_FILE_ERRORS) + '/*'}
                    element={<DocumentSelectFileErrorsPage documents={documents} />}
                />
            </Routes>

            <Outlet />
        </div>
    );
};

export default DocumentUploadPage;
