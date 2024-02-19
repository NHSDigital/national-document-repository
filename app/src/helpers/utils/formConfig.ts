import { UploadDocument } from '../../types/pages/UploadDocumentsPage/types';
import { Control, FieldValues } from 'react-hook-form';

export const lloydGeorgeFormConfig = (control: Control<FieldValues>) => {
    let REGEX_ACCENT_MARKS_IN_NFD = '';
    for (let i = 300; i < 371; i++) {
        REGEX_ACCENT_MARKS_IN_NFD += String.fromCharCode(i);
    }

    const REGEX_ACCENT_CHARS_IN_NFC = 'À-ž';
    const REGEX_PATIENT_NAME_PATTERN = `[A-Za-z ${REGEX_ACCENT_CHARS_IN_NFC}${REGEX_ACCENT_MARKS_IN_NFD}]+`;
    const REGEX_NHS_NUMBER_REGEX = '[0-9]{10}';
    const REGEX_LLOYD_GEORGE_FILENAME = new RegExp(
        `[0-9]+of[0-9]+_Lloyd_George_Record_\\[${REGEX_PATIENT_NAME_PATTERN}]_\\[${REGEX_NHS_NUMBER_REGEX}]_\\[\\d\\d-\\d\\d-\\d\\d\\d\\d].pdf`,
    );

    const lgFilesNumber = /of[0-9]+/;
    const FIVEGB = 5 * Math.pow(1024, 3);
    return {
        name: 'lg-documents',
        control,
        rules: {
            validate: {
                perFileValidation: (value?: Array<UploadDocument>) => {
                    if (Array.isArray(value)) {
                        for (let i = 0; i < value.length; i++) {
                            const currentFile = value[i].file;
                            if (currentFile.size > FIVEGB) {
                                return 'Please ensure that all files are less than 5GB in size';
                            }
                            if (currentFile.type !== 'application/pdf') {
                                return 'One or more of the files do not match the required file type. Please check the file(s) and try again';
                            }
                            const expectedNumberOfFiles = currentFile.name.match(lgFilesNumber);
                            const doesPassRegex = REGEX_LLOYD_GEORGE_FILENAME.exec(
                                currentFile.name,
                            );
                            const doFilesTotalMatch =
                                expectedNumberOfFiles &&
                                value.length === parseInt(expectedNumberOfFiles[0].slice(2));
                            const isFileNumberBiggerThanTotal =
                                expectedNumberOfFiles &&
                                parseInt(currentFile.name.split(lgFilesNumber)[0]) >
                                    parseInt(expectedNumberOfFiles[0].slice(2));
                            const isFileNumberZero =
                                currentFile.name.split(lgFilesNumber)[0] === '0';
                            const doesFileNameMatchEachOther =
                                currentFile.name.split(lgFilesNumber)[1] ===
                                value[0].file.name.split(lgFilesNumber)[1];
                            if (
                                !doesPassRegex ||
                                !doFilesTotalMatch ||
                                isFileNumberBiggerThanTotal ||
                                isFileNumberZero ||
                                !doesFileNameMatchEachOther
                            ) {
                                return 'One or more of the files do not match the required filename format. Please check the file(s) and try again';
                            }
                        }
                    }
                },
                hasDuplicateFile: (value?: Array<UploadDocument>) => {
                    if (
                        value?.some((doc: UploadDocument) => {
                            return value?.some(
                                (compare: UploadDocument) =>
                                    doc.file.name === compare.file.name &&
                                    doc.file.size === compare.file.size &&
                                    doc.id !== compare.id,
                            );
                        })
                    ) {
                        return 'There are documents chosen that have the same name, a record with duplicate file names can not be uploaded because it does not match the required file format. Please check the files(s) and try again.';
                    }
                },
            },
        },
    };
};

export const ARFFormConfig = (control: Control<FieldValues>) => {
    const FIVEGB = 5 * Math.pow(1024, 3);
    return {
        name: 'arf-documents',
        control,
        rules: {
            validate: {
                perFileValidation: (value?: Array<UploadDocument>) => {
                    if (Array.isArray(value)) {
                        for (let i = 0; i < value.length; i++) {
                            const currentFile = value[i].file;
                            if (currentFile.size > FIVEGB) {
                                return 'Please ensure that all files are less than 5GB in size';
                            }
                        }
                    }
                },
            },
        },
    };
};
