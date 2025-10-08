import { ErrorMessageListItem } from '../../types/pages/genericPageErrors';
import { getMappedErrorMessage, groupErrorsByType } from './errorMessages';

type UploadFilesError = ErrorMessageListItem<UPLOAD_FILE_ERROR_TYPE>;

export enum UPLOAD_FILE_ERROR_TYPE {
    noFiles = 'noFiles',
    passwordProtected = 'passwordProtected',
    invalidPdf = 'invalidPdf',
    emptyPdf = 'emptyPdf',
    duplicatePositionError = 'duplicatePositionError',
}

export enum PDF_PARSING_ERROR_TYPE {
    INVALID_PDF_STRUCTURE = 'Invalid PDF structure.',
    PASSWORD_MISSING = 'No password given',
    EMPTY_PDF = 'The PDF file is empty, i.e. its size is zero bytes.',
}

export type fileUploadErrorMessageType = {
    inline: string;
    errorBox: string;
    selectFileError?: string;
};

export const getUploadErrorBoxErrorMessage = (error: UploadFilesError): string =>
    getMappedErrorMessage(error, fileUploadErrorMessages);

export const groupUploadErrorsByType = (
    errors: UploadFilesError[],
): Partial<Record<UPLOAD_FILE_ERROR_TYPE, { linkIds: string[]; errorMessage: string }>> =>
    groupErrorsByType(errors, getUploadErrorBoxErrorMessage);

type ErrorMessageType = { [errorType in UPLOAD_FILE_ERROR_TYPE]: fileUploadErrorMessageType };

export const fileUploadErrorMessages: ErrorMessageType = {
    noFiles: {
        inline: 'Select a file to upload',
        errorBox: 'Select a file to upload',
    },
    invalidPdf: {
        inline: 'The selected file is be damaged or unreadable. Fix it to continue with upload.',
        errorBox: 'The selected file is be damaged or unreadable. Fix it to continue with upload.',
        selectFileError: 'This file is damaged or unreadable',
    },
    passwordProtected: {
        inline: 'The selected file is password protected. Remove password and upload again.',
        errorBox: 'The selected file is password protected. Remove password and upload again.',
        selectFileError: 'This file is password protected',
    },
    emptyPdf: {
        inline: 'The selected file is empty. Check it to continue with upload.',
        errorBox: 'The selected file is empty. Check it to continue with upload.',
        selectFileError: 'This file is empty',
    },
    duplicatePositionError: {
        inline: 'You have selected the same position number for two or more files',
        errorBox: 'You have selected the same position number for two or more files',
    },
};
