import { UploadDocument, UploadFilesErrors } from '../../types/pages/UploadDocumentsPage/types';
import { UPLOAD_FILE_ERROR_TYPE } from './fileUploadErrorMessages';
import { PatientDetails } from '../../types/generic/patientDetails';
import moment from 'moment/moment';
import { countElements, fromOneToN, joinNumbersAsWords, unique } from './validationHelpers';

let REGEX_ACCENT_MARKS_IN_NFD = '';
for (let i = 0x300; i < 0x371; i++) {
    REGEX_ACCENT_MARKS_IN_NFD += String.fromCharCode(i);
}
const REGEX_ACCENT_CHARS_IN_NFC = 'À-ž';
const REGEX_PATIENT_NAME_PATTERN = `[A-Za-z ${REGEX_ACCENT_CHARS_IN_NFC}${REGEX_ACCENT_MARKS_IN_NFD}'-]+`;
const REGEX_NHS_NUMBER_REGEX = '[0-9]{10}';
const REGEX_LLOYD_GEORGE_FILENAME = new RegExp(
    `^(?<file_number>[0-9]+)of(?<total_number>[0-9]+)_Lloyd_George_Record_\\[(?<patient_name>${REGEX_PATIENT_NAME_PATTERN})]_\\[(?<nhs_number>${REGEX_NHS_NUMBER_REGEX})]_\\[(?<dob>\\d\\d-\\d\\d-\\d\\d\\d\\d)].pdf$`,
);

export const uploadLloydGeorgeDocumentValidation = (
    uploadDocuments: UploadDocument[],
    patientDetails: PatientDetails | null,
): UploadFilesErrors[] => {
    const errors: UploadFilesErrors[] = [];

    const FIVEGB = 5 * Math.pow(1024, 3);

    const filesPassedRegexCheck = [];

    for (const document of uploadDocuments) {
        const currentFile = document.file;
        if (currentFile.size > FIVEGB) {
            errors.push({
                filename: currentFile.name,
                error: UPLOAD_FILE_ERROR_TYPE.fileSizeError,
            });
            continue;
        }
        if (currentFile.type !== 'application/pdf') {
            errors.push({
                filename: currentFile.name,
                error: UPLOAD_FILE_ERROR_TYPE.fileTypeError,
            });
            continue;
        }

        const regexMatchResult = REGEX_LLOYD_GEORGE_FILENAME.exec(currentFile.name);
        if (regexMatchResult) {
            filesPassedRegexCheck.push(regexMatchResult);
        } else {
            errors.push({
                filename: currentFile.name,
                error: UPLOAD_FILE_ERROR_TYPE.generalFileNameError,
            });
        }
    }

    if (patientDetails) {
        const errorsWhenCompareWithPdsData = filesPassedRegexCheck.flatMap((regexMatchResult) =>
            validateWithPatientDetails(regexMatchResult, patientDetails),
        );
        errors.push(...errorsWhenCompareWithPdsData);
    }

    const fileNumberErrors = validateFileNumbers(filesPassedRegexCheck);
    errors.push(...fileNumberErrors);

    return unique(errors);
};

const validateFileNumbers = (regexMatchResults: RegExpExecArray[]): UploadFilesErrors[] => {
    const errors: UploadFilesErrors[] = [];
    const allFileNames = regexMatchResults.map((match) => match.input);

    const totalNumberInFiles = regexMatchResults.map((match) => match?.groups?.total_number);
    const allTotalNumbersAreTheSame =
        totalNumberInFiles.length > 0 &&
        totalNumberInFiles.every((n) => n === totalNumberInFiles[0]);

    if (!allTotalNumbersAreTheSame) {
        const totalNumberUnmatchErrors = allFileNames.map((filename) => ({
            filename,
            error: UPLOAD_FILE_ERROR_TYPE.totalFileNumberUnmatchError,
        }));
        // early return here
        return totalNumberUnmatchErrors;
    }

    const totalFileNumber = Number(totalNumberInFiles[0]);

    const allowedFileNumbers = new Set(fromOneToN(totalFileNumber));
    const actualFileNumbersFound = regexMatchResults.map((match) =>
        Number(match?.groups?.file_number),
    );
    const actualFileNumberCounts = countElements(actualFileNumbersFound);

    const missingFileNumbers = [...allowedFileNumbers].filter(
        (fileNumber) => !(fileNumber in actualFileNumberCounts),
    );

    regexMatchResults.forEach((match) => {
        const filename = match.input;
        const fileNumber = Number(match?.groups?.file_number);

        if (!allowedFileNumbers.has(fileNumber)) {
            errors.push({ filename, error: UPLOAD_FILE_ERROR_TYPE.fileNumberOutOfRangeError });
        }
        if (actualFileNumberCounts[fileNumber] > 1) {
            errors.push({ filename, error: UPLOAD_FILE_ERROR_TYPE.duplicateFile });
        }
        if (missingFileNumbers.length > 0 && allowedFileNumbers.has(fileNumber)) {
            errors.push({
                filename,
                error: UPLOAD_FILE_ERROR_TYPE.fileNumberMissingError,
                details: `with file numbers: ${joinNumbersAsWords(missingFileNumbers)}`,
            });
        }
    });

    return errors;
};

const validateWithPatientDetails = (
    regexMatchResult: RegExpExecArray,
    patientDetails: PatientDetails,
): UploadFilesErrors[] => {
    const dateOfBirth = new Date(patientDetails.birthDate);
    const dateOfBirthString = moment(dateOfBirth).format('DD-MM-YYYY');
    const nhsNumber = patientDetails.nhsNumber;

    const errors: UploadFilesErrors[] = [];
    const filename = regexMatchResult.input;

    if (regexMatchResult?.groups?.nhs_number !== nhsNumber) {
        errors.push({ filename, error: UPLOAD_FILE_ERROR_TYPE.nhsNumberError });
    }

    if (regexMatchResult?.groups?.dob !== dateOfBirthString) {
        errors.push({ filename, error: UPLOAD_FILE_ERROR_TYPE.dateOfBirthError });
    }

    const patientNameInFilename = regexMatchResult?.groups?.patient_name as string;
    if (!patientNameMatchesPds(patientNameInFilename, patientDetails)) {
        errors.push({ filename, error: UPLOAD_FILE_ERROR_TYPE.patientNameError });
    }

    return errors;
};

export const patientNameMatchesPds = (
    patientNameInFileName: string,
    patientDetailsFromPds: PatientDetails,
): boolean => {
    const patientNameInFileNameNormalised = patientNameInFileName.normalize('NFD').toLowerCase();

    const firstName = patientDetailsFromPds.givenName[0].normalize('NFD').toLowerCase();
    const firstNameMatches = patientNameInFileNameNormalised.startsWith(firstName);

    const familyName = patientDetailsFromPds.familyName.normalize('NFD').toLowerCase();
    const familyNameMarches = patientNameInFileNameNormalised.endsWith(familyName);

    return firstNameMatches && familyNameMarches;
};
