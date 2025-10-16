import { AuthHeaders } from '../../types/blocks/authHeaders';
import { endpoints } from '../../types/generic/endpoints';
import { DOCUMENT_UPLOAD_STATE, UploadDocument } from '../../types/pages/UploadDocumentsPage/types';

import axios, { AxiosError } from 'axios';
import {
    DocumentStatusResult,
    S3Upload,
    S3UploadFields,
    UploadSession,
} from '../../types/generic/uploadResult';
import { Dispatch, SetStateAction } from 'react';
import { setSingleDocument } from '../utils/uploadDocumentHelpers';
import { PatientDetails } from '../../types/generic/patientDetails';
import { formatDateWithDashes } from '../utils/formatDate';

type UploadDocumentsArgs = {
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

export const uploadDocumentToS3 = async ({
    setDocuments,
    uploadSession,
    document,
}: UploadDocumentsToS3Args): Promise<void> => {
    const documentMetadata: S3Upload = uploadSession[document.id];
    const formData = new FormData();
    const docFields: S3UploadFields = documentMetadata.fields;
    Object.entries(docFields).forEach(([key, value]) => {
        formData.append(key, value);
    });
    formData.append('file', document.file);
    const s3url = documentMetadata.url;

    try {
        return await axios.post(s3url, formData, {
            onUploadProgress: (progress): void => {
                const { loaded, total } = progress;
                if (total) {
                    setSingleDocument(setDocuments, {
                        id: document.id,
                        state:
                            total >= 100
                                ? DOCUMENT_UPLOAD_STATE.SCANNING
                                : DOCUMENT_UPLOAD_STATE.UPLOADING,
                        progress: (loaded / total) * 100,
                    });
                }
            },
        });
    } catch (e) {
        const error = e as AxiosError;
        throw error;
    }
};

export const generateFileName = (patientDetails: PatientDetails | null): string => {
    if (!patientDetails) {
        throw new Error('Patient details are required to generate filename');
    }

    // replace commas and other characters unfriendly characters to file paths
    const givenName = patientDetails.givenName.join(' ').replace(/[,/\\?%*:|"<>]/g, '-');
    const filename = `1of1_Lloyd_George_Record_[${givenName} ${patientDetails.familyName.toUpperCase()}]_[${patientDetails.nhsNumber}]_[${formatDateWithDashes(new Date(patientDetails.birthDate))}].pdf`;
    return filename;
};

const uploadDocuments = async ({
    nhsNumber,
    documents,
    baseUrl,
    baseHeaders,
}: UploadDocumentsArgs): Promise<UploadSession> => {
    const requestBody = {
        resourceType: 'CreateDocumentReference',
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
                    clientId: doc.id,
                })),
            },
        ],
        created: new Date(Date.now()).toISOString(),
    };

    const gatewayUrl = baseUrl + endpoints.DOCUMENT_UPLOAD;

    try {
        const { data } = await axios.post<UploadSession>(gatewayUrl, JSON.stringify(requestBody), {
            headers: {
                ...baseHeaders,
            },
            params: {
                patientId: nhsNumber,
            },
        });

        return data;
    } catch (e) {
        const error = e as AxiosError;
        throw error;
    }
};

export const getDocumentStatus = async ({
    documents,
    baseUrl,
    baseHeaders,
    nhsNumber,
}: UploadDocumentsArgs): Promise<DocumentStatusResult> => {
    const documentStatusUrl = baseUrl + endpoints.DOCUMENT_STATUS;

    try {
        const { data } = await axios.get<DocumentStatusResult>(documentStatusUrl, {
            headers: {
                ...baseHeaders,
            },
            params: {
                patientId: nhsNumber,
                docIds: documents.map((d) => d.ref).join(','),
            },
        });

        return data;
    } catch (e) {
        const error = e as AxiosError;
        throw error;
    }
};

export default uploadDocuments;
