import { BackLink } from 'nhsuk-react-components';
import { useLocation } from 'react-router-dom';
import { UploadDocument } from '../../../../types/pages/UploadDocumentsPage/types';
import { UPLOAD_FILE_ERROR_TYPE } from '../../../../helpers/utils/fileUploadErrorMessages';
import { JSX } from 'react';
import { routes } from '../../../../types/generic/routes';

const helpAndGuidanceLink =
    'https://digital.nhs.uk/services/access-and-store-digital-patient-documents/help-and-guidance';

type ErrorPageState = {
    failedDocuments: UploadDocument[];
};

const fileErrorText = (errorType: UPLOAD_FILE_ERROR_TYPE): string => {
    switch (errorType) {
        case UPLOAD_FILE_ERROR_TYPE.invalidPdf:
            return 'This file is damaged or unreadable.';
        case UPLOAD_FILE_ERROR_TYPE.emptyPdf:
            return 'This file is empty.';
        case UPLOAD_FILE_ERROR_TYPE.passwordProtected:
            return 'This file is password protected.';
        default:
            return 'There was a problem with this file.';
    }
};

const DocumentSelectFileErrorsPage = (): JSX.Element => {
    const location = useLocation();
    const state = location.state as ErrorPageState;

    const failedDocuments = state?.failedDocuments || [];

    return (
        <>
            <h1>We could not upload your files</h1>

            <p>There was a problem with your files, so we stopped the upload. </p>

            <h2 className="nhsuk-heading-m">Files with problems</h2>

            {failedDocuments.map((doc) => (
                <div key={doc.id} style={{ marginBottom: '1rem' }}>
                    <p style={{ color: 'red', fontWeight: 'bold', marginBottom: 0 }}>
                        {doc.file.name}
                    </p>
                    <p style={{ marginTop: 0 }}>{fileErrorText(doc.error!)}</p>
                </div>
            ))}

            <h2 className="nhsuk-heading-m">What you need to do</h2>
            <p>
                You'll need to resolve the problems with these files then upload all the files
                again. again. To make sure patient records are complete, you must upload all files
                for a patient at the same time.
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

            <BackLink asElement="a" href={routes.HOME}>
                Go to home
            </BackLink>
        </>
    );
};

export default DocumentSelectFileErrorsPage;
