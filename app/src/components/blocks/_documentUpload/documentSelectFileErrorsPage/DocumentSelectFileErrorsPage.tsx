import { ErrorMessage } from 'nhsuk-react-components';
import { useNavigate } from 'react-router-dom';
import { UploadDocument } from '../../../../types/pages/UploadDocumentsPage/types';
import {
    fileUploadErrorMessages,
    UPLOAD_FILE_ERROR_TYPE,
} from '../../../../helpers/utils/fileUploadErrorMessages';
import { JSX, useEffect } from 'react';
import { routes } from '../../../../types/generic/routes';

const helpAndGuidanceLink =
    'https://digital.nhs.uk/services/access-and-store-digital-patient-documents/help-and-guidance';

type Props = {
    documents: Array<UploadDocument>;
};

const DocumentSelectFileErrorsPage = ({ documents }: Props): JSX.Element => {
    const navigate = useNavigate();

    const fileErrorText = (errorType: UPLOAD_FILE_ERROR_TYPE): string | undefined => {
        switch (errorType) {
            case UPLOAD_FILE_ERROR_TYPE.invalidPdf:
                return fileUploadErrorMessages.invalidPdf.selectFileError;
            case UPLOAD_FILE_ERROR_TYPE.emptyPdf:
                return fileUploadErrorMessages.emptyPdf.selectFileError;
            case UPLOAD_FILE_ERROR_TYPE.passwordProtected:
                return fileUploadErrorMessages.passwordProtected.selectFileError;
        }
    };

    useEffect(() => {
        if (documents.length === 0) {
            navigate(routes.HOME);
            return;
        }
    }, []);

    return (
        <>
            <h1>We could not upload your files</h1>

            <p>There was a problem with your files, so we stopped the upload. </p>

            <h2 className="nhsuk-heading-m">Files with problems</h2>

            {documents.map((doc) => (
                <div key={doc.id}>
                    <ErrorMessage className="mb-1">{doc.file.name}</ErrorMessage>
                    <p>{fileErrorText(doc.error!)}</p>
                </div>
            ))}

            <h2 className="nhsuk-heading-m">What you need to do</h2>
            <p>
                You'll need to resolve the problems with these files then upload all the files
                again. To make sure patient records are complete, you must upload all files for a
                patient at the same time.
            </p>

            <h2 className="nhsuk-heading-m">Get help</h2>
            <p>Contact your local IT support desk to resolve the problems with these files. </p>

            <p>
                For information on removing passwords from files, see our{' '}
                <a
                    href={helpAndGuidanceLink}
                    title="help and guidance"
                    target="_blank"
                    rel="noreferrer"
                    aria-label="Help and guidance - this link will open in a new tab"
                >
                    help and guidance
                </a>{' '}
                pages.
            </p>

            <p>
                <a href={routes.HOME}>Go to home</a>
            </p>
        </>
    );
};

export default DocumentSelectFileErrorsPage;
