import {
    DOCUMENT_TYPE,
    DOCUMENT_UPLOAD_STATE,
    UploadDocument,
    DOCUMENT_UPLOAD_STATE as documentUploadStates,
} from '../../types/pages/UploadDocumentsPage/types';
import { PatientDetails } from '../../types/generic/patientDetails';
import { SearchResult } from '../../types/generic/searchResult';
import { LloydGeorgeStitchResult } from '../requests/lloydGeorgeSearchResult';

const buildPatientDetails = (patientDetailsOverride?: Partial<PatientDetails>) => {
    const patient: PatientDetails = {
        birthDate: '1970-01-01',
        familyName: 'Doe',
        givenName: ['John'],
        nhsNumber: '9000000009',
        postalCode: 'BS3 3NQ',
        superseded: false,
        restricted: false,
        ...patientDetailsOverride,
    };

    return patient;
};

const buildTextFile = (name: string, size?: number) => {
    const file = new File(['test'], `${name}.txt`, {
        type: 'text/plain',
    });

    if (size) {
        Object.defineProperty(file, 'size', {
            value: size,
        });
    }

    return file;
};

const buildDocument = (
    file: File,
    uploadStatus: DOCUMENT_UPLOAD_STATE,
    docType?: DOCUMENT_TYPE,
) => {
    const mockDocument: UploadDocument = {
        file,
        state: uploadStatus ?? documentUploadStates.SUCCEEDED,
        progress: 0,
        id: Math.floor(Math.random() * 1000000).toString(),
        docType: docType ?? DOCUMENT_TYPE.ARF,
    };
    return mockDocument;
};

const buildSearchResult = (searchResultOverride?: Partial<SearchResult>) => {
    const result: SearchResult = {
        fileName: 'Some description',
        created: '2023-09-06T10:41:51.899908Z',
        virusScannerResult: 'Clean',
        ...searchResultOverride,
    };
    return result;
};

const buildLgSearchResult = () => {
    const result: LloydGeorgeStitchResult = {
        number_of_files: 7,
        total_file_size_in_byte: 7,
        last_updated: '2023-10-03T09:11:54.618694Z',
        presign_url: 'https://test-url',
    };
    return result;
};

export {
    buildPatientDetails,
    buildTextFile,
    buildDocument,
    buildSearchResult,
    buildLgSearchResult,
};
