import { PatientDetails } from '../../types/generic/patientDetails';
import { buildPatientDetails } from './testBuilders';
import {
    DOCUMENT_TYPE,
    DOCUMENT_UPLOAD_STATE as documentUploadStates,
    UploadDocument,
} from '../../types/pages/UploadDocumentsPage/types';
import { v4 as uuidv4 } from 'uuid';

type PdsNameMatchingTestCase = {
    patientDetails: PatientDetails;
    patientNameInFileName: string;
    shouldAcceptName: boolean;
};

type TestCaseJsonFormat = {
    pds_name: {
        family: string;
        given: string[];
    };
    accept: string[];
    reject: string[];
};

export const TEST_CASES_FOR_TWO_WORDS_FAMILY_NAME = {
    pds_name: { family: 'Smith Anderson', given: ['Jane', 'Bob'] },
    accept: ['Jane Bob Smith Anderson', 'Jane Smith Anderson', 'Jane B Smith Anderson'],
    reject: ['Bob Smith Anderson', 'Jane Smith', 'Jane Anderson', 'Jane Anderson Smith'],
};

export const TEST_CASES_FOR_FAMILY_NAME_WITH_HYPHEN = {
    pds_name: { family: 'Smith-Anderson', given: ['Jane'] },
    accept: ['Jane Smith-Anderson'],
    reject: ['Jane Smith Anderson', 'Jane Smith', 'Jane Anderson'],
};

export const TEST_CASES_FOR_TWO_WORDS_GIVEN_NAME = {
    pds_name: { family: 'Smith', given: ['Jane Bob'] },
    accept: ['Jane Bob Smith'],
    reject: ['Jane Smith', 'Jane B Smith', 'Jane-Bob Smith', 'Bob Smith'],
};

export const TEST_CASES_FOR_TWO_WORDS_FAMILY_NAME_AND_GIVEN_NAME = {
    pds_name: { family: 'Smith Anderson', given: ['Jane Bob'] },
    accept: ['Jane Bob Smith Anderson'],
    reject: [
        'Jane Smith Anderson',
        'Bob Smith Anderson',
        'Jane B Smith Anderson',
        'Jane Bob Smith',
        'Jane Bob Anderson',
    ],
};

export const loadTestCases = (testCaseJson: TestCaseJsonFormat): Array<PdsNameMatchingTestCase> => {
    const patientDetails = buildPatientDetails({
        givenName: testCaseJson['pds_name']['given'],
        familyName: testCaseJson['pds_name']['family'],
    });

    const testCasesForAccept = testCaseJson['accept'].map((patientNameInFileName) => ({
        patientDetails,
        patientNameInFileName,
        shouldAcceptName: true,
    }));

    const testCasesForReject = testCaseJson['reject'].map((patientNameInFileName) => ({
        patientDetails,
        patientNameInFileName,
        shouldAcceptName: false,
    }));

    return [...testCasesForAccept, ...testCasesForReject];
};

export const buildLGUploadDocsFromFilenames = (filenames: string[]): UploadDocument[] => {
    const fileObjects = filenames.map(
        (filename) =>
            new File(['test'], filename, {
                type: 'application/pdf',
            }),
    );

    return fileObjects.map((file) => ({
        file,
        state: documentUploadStates.SELECTED,
        progress: 0,
        id: uuidv4(),
        docType: DOCUMENT_TYPE.LLOYD_GEORGE,
        attempts: 0,
    }));
};
