import { AuthHeaders } from '../../types/blocks/authHeaders';
import { endpoints } from '../../types/generic/endpoints';
import {
    DOCUMENT_TYPE,
    DOCUMENT_UPLOAD_STATE,
    UploadDocument,
} from '../../types/pages/UploadDocumentsPage/types';
import axios, { AxiosError } from 'axios';
import { S3Upload, S3UploadFields, UploadSession } from '../../types/generic/uploadResult';
import { Dispatch, SetStateAction } from 'react';

type FileKeyBuilder = {
    [key in DOCUMENT_TYPE]: string[];
};

type UploadDocumentsArgs = {
    setDocuments: Dispatch<SetStateAction<UploadDocument[]>>;
    documents: UploadDocument[];
    nhsNumber: string;
    baseUrl: string;
    baseHeaders: AuthHeaders;
};

type UploadDocumentsToS3Args = {
    setDocuments: Dispatch<SetStateAction<UploadDocument[]>>;
    document: UploadDocument;
    uploadSession: UploadSession;
};

type DocRefResponse = {
    data: UploadSession;
};

type DocumentStateProps = {
    id: string;
    state: DOCUMENT_UPLOAD_STATE;
    progress?: number | 'scan';
    attempts?: number;
};

type VirusScanArgs = {
    documentReference: string;
    baseUrl: string;
    baseHeaders: AuthHeaders;
};
type UploadConfirmationArgs = {
    baseUrl: string;
    baseHeaders: AuthHeaders;
    nhsNumber: string;
    documents: Array<UploadDocument>;
    uploadSession: UploadSession;
};

export const setDocument = (
    setDocuments: Dispatch<SetStateAction<UploadDocument[]>>,
    { id, state, progress, attempts }: DocumentStateProps,
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

export const virusScanResult = async ({
    documentReference,
    baseUrl,
    baseHeaders,
}: VirusScanArgs) => {
    const virusScanGatewayUrl = baseUrl + endpoints.VIRUS_SCAN;
    const body = { documentReference };
    try {
        await axios.post(virusScanGatewayUrl, body, {
            headers: {
                ...baseHeaders,
            },
        });
        return DOCUMENT_UPLOAD_STATE.CLEAN;
    } catch (e) {
        return DOCUMENT_UPLOAD_STATE.INFECTED;
    }
};

export const uploadConfirmation = async ({
    baseUrl,
    baseHeaders,
    nhsNumber,
    documents,
    uploadSession,
}: UploadConfirmationArgs) => {
    const fileKeyBuilder = documents.reduce((acc, doc) => {
        const documentMetadata = uploadSession[doc.file.name];
        const fileKey = documentMetadata.fields.key.split('/');
        const previousKeys = acc[doc.docType] ?? [];

        return {
            ...acc,
            [doc.docType]: [...previousKeys, fileKey[3]],
        };
    }, {} as FileKeyBuilder);

    const uploadConfirmationGatewayUrl = baseUrl + endpoints.UPLOAD_CONFIRMATION;
    const confirmationBody = {
        patientId: nhsNumber,
        documents: { ...fileKeyBuilder },
    };
    try {
        await axios.post(uploadConfirmationGatewayUrl, confirmationBody, {
            headers: {
                ...baseHeaders,
            },
        });
        return DOCUMENT_UPLOAD_STATE.SUCCEEDED;
    } catch (e) {
        const error = e as AxiosError;
        if (error.response?.status === 403) {
            throw e;
        }
        return DOCUMENT_UPLOAD_STATE.FAILED;
    }
};

export const uploadDocumentToS3 = async ({
    setDocuments,
    uploadSession,
    document,
}: UploadDocumentsToS3Args) => {
    const documentMetadata: S3Upload = uploadSession[document.file.name];
    const formData = new FormData();
    const docFields: S3UploadFields = documentMetadata.fields;
    Object.entries(docFields).forEach(([key, value]) => {
        formData.append(key, value);
    });
    formData.append('file', document.file);
    const s3url = documentMetadata.url;
    try {
        await axios.post(s3url, formData, {
            onUploadProgress: (progress) => {
                const { loaded, total } = progress;
                if (total) {
                    setDocument(setDocuments, {
                        id: document.id,
                        state: DOCUMENT_UPLOAD_STATE.UPLOADING,
                        progress: (loaded / total) * 100,
                    });
                }
            },
        });

        setDocument(setDocuments, {
            id: document.id,
            state: DOCUMENT_UPLOAD_STATE.SCANNING,
            progress: 'scan',
        });
        return documentMetadata.fields.key;
    } catch (e) {
        const error = e as AxiosError;
        if (error.response?.status === 403) {
            throw e;
        }
        setDocument(setDocuments, {
            id: document.id,
            state: DOCUMENT_UPLOAD_STATE.FAILED,
            attempts: document.attempts + 1,
            progress: 0,
        });
        throw e;
    }
};

const uploadDocuments = async ({
    nhsNumber,
    setDocuments,
    documents,
    baseUrl,
    baseHeaders,
}: UploadDocumentsArgs) => {
    const requestBody = {
        resourceType: 'DocumentReference',
        subject: {
            identifier: {
                system: 'https://fhir.nhs.uk/Id/nhs-number',
                value: nhsNumber,
            },
        },
        type: {
            coding: [
                {
                    system: 'http://snomed.info/sct',
                    code: '22151000087106',
                },
            ],
        },
        content: [
            {
                attachment: documents.map((doc) => ({
                    fileName: doc.file.name,
                    contentType: doc.file.type,
                    docType: doc.docType,
                })),
            },
        ],
        created: new Date(Date.now()).toISOString(),
    };

    const gatewayUrl = baseUrl + endpoints.DOCUMENT_UPLOAD;

    try {
        const { data }: DocRefResponse = await axios.post(gatewayUrl, JSON.stringify(requestBody), {
            headers: {
                ...baseHeaders,
            },
        });
        return data;
    } catch (e) {
        const error = e as AxiosError;
        if (error.response?.status === 403) {
            throw e;
        }

        const failedDocuments = documents.map((doc) => ({
            ...doc,
            state: DOCUMENT_UPLOAD_STATE.FAILED,
            attempts: doc.attempts + 1,
            progress: 0,
        }));
        setDocuments(failedDocuments);
        throw e;
    }
};

export default uploadDocuments;
