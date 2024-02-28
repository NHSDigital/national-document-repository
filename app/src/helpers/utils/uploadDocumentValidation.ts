import { UploadDocument, UploadFilesErrors } from '../../types/pages/UploadDocumentsPage/types';
import { fileUploadErrorMessages } from './fileUploadErrorMessages';
import { PatientDetails } from '../../types/generic/patientDetails';
import moment from 'moment/moment';

let REGEX_ACCENT_MARKS_IN_NFD = '';
for (let i = 0x300; i < 0x371; i++) {
    REGEX_ACCENT_MARKS_IN_NFD += String.fromCharCode(i);
}
const REGEX_ACCENT_CHARS_IN_NFC = 'À-ž';
const REGEX_PATIENT_NAME_PATTERN = `[A-Za-z ${REGEX_ACCENT_CHARS_IN_NFC}${REGEX_ACCENT_MARKS_IN_NFD}]+`;
const REGEX_NHS_NUMBER_REGEX = '[0-9]{10}';
const REGEX_LLOYD_GEORGE_FILENAME = new RegExp(
    `[0-9]+of[0-9]+_Lloyd_George_Record_\\[(?<patient_name>${REGEX_PATIENT_NAME_PATTERN})]_\\[(?<nhs_number>${REGEX_NHS_NUMBER_REGEX})]_\\[(?<dob>\\d\\d-\\d\\d-\\d\\d\\d\\d)].pdf`,
);

export const validateFilenamesWithPatientDetail = (
    uploadDocuments: UploadDocument[],
    patientDetails: PatientDetails,
) => {
    const dateOfBirth = new Date(patientDetails.birthDate);
    const dateOfBirthString = moment(dateOfBirth).format('DD-MM-YYYY');
    const patientNameFromPds = [...patientDetails.givenName, patientDetails.familyName].join(' ');
    const nhsNumber = patientDetails.nhsNumber;

    const errors: UploadFilesErrors[] = [];

    for (let doc of uploadDocuments) {
        const filename = doc.file.name;
        const match = REGEX_LLOYD_GEORGE_FILENAME.exec(filename);

        if (match?.groups?.nhs_number !== nhsNumber) {
            errors.push({ file: doc, error: fileUploadErrorMessages.nhsNumberError });
        }

        if (match?.groups?.dob !== dateOfBirthString) {
            errors.push({ file: doc, error: fileUploadErrorMessages.dateOfBirthError });
        }

        const patientNameInFilename = match?.groups?.patient_name as string;
        if (!patientNameMatches(patientNameInFilename, patientNameFromPds)) {
            errors.push({ file: doc, error: fileUploadErrorMessages.patientNameError });
        }
    }
    return errors;
};

export const dateOfBirthMatches = (
    dateOfBirthInFilename: string,
    dateOfBirthFromPds: Date,
): boolean => {
    return moment(dateOfBirthFromPds).format('DD-MM-YYYY') === dateOfBirthInFilename;
};

export const patientNameMatches = (
    patientNameInFileName: string,
    patientNameFromPds: string,
): boolean => {
    return (
        patientNameInFileName.normalize('NFD').toLowerCase() ===
        patientNameFromPds.normalize('NFD').toLowerCase()
    );
};

export const uploadDocumentValidation = (
    uploadDocuments: UploadDocument[],
    patientDetails: PatientDetails | null,
) => {
    const errors: UploadFilesErrors[] = [];
    const lgFilesNumber = /of[0-9]+/;
    const FIVEGB = 5 * Math.pow(1024, 3);
    for (let document of uploadDocuments) {
        const currentFile = document.file;
        if (currentFile.size > FIVEGB) {
            errors.push({
                file: document,
                error: fileUploadErrorMessages.fileSizeError,
            });
            continue;
        }
        if (currentFile.type !== 'application/pdf') {
            errors.push({
                file: document,
                error: fileUploadErrorMessages.fileTypeError,
            });
            continue;
        }
        const isDuplicate = uploadDocuments?.some((compare: UploadDocument) => {
            return (
                document.file.name === compare.file.name &&
                document.file.size === compare.file.size &&
                document.id !== compare.id
            );
        });
        if (isDuplicate) {
            errors.push({
                file: document,
                error: fileUploadErrorMessages.duplicateFile,
            });
            continue;
        }

        const expectedNumberOfFiles = currentFile.name.match(lgFilesNumber);
        const doesPassRegex = REGEX_LLOYD_GEORGE_FILENAME.exec(currentFile.name);
        const doFilesTotalMatch =
            expectedNumberOfFiles &&
            uploadDocuments.length === parseInt(expectedNumberOfFiles[0].slice(2));
        const isFileNumberBiggerThanTotal =
            expectedNumberOfFiles &&
            parseInt(currentFile.name.split(lgFilesNumber)[0]) >
                parseInt(expectedNumberOfFiles[0].slice(2));
        const isFileNumberZero = currentFile.name.split(lgFilesNumber)[0] === '0';
        const doesFileNameMatchEachOther =
            currentFile.name.split(lgFilesNumber)[1] ===
            uploadDocuments[0].file.name.split(lgFilesNumber)[1];
        if (
            !doesPassRegex ||
            !doFilesTotalMatch ||
            isFileNumberBiggerThanTotal ||
            isFileNumberZero ||
            !doesFileNameMatchEachOther
        ) {
            errors.push({
                file: document,
                error: fileUploadErrorMessages.fileNameError,
            });
        }
    }

    if (errors.length === 0 && patientDetails) {
        const validateWithPds = validateFilenamesWithPatientDetail(uploadDocuments, patientDetails);
        return validateWithPds;
    }
    return errors;
};
