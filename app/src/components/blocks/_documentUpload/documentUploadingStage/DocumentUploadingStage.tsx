import { Table, WarningCallout } from 'nhsuk-react-components';
import useTitle from '../../../../helpers/hooks/useTitle';
import {
    DOCUMENT_TYPE,
    DOCUMENT_UPLOAD_STATE,
    UploadDocument,
} from '../../../../types/pages/UploadDocumentsPage/types';
import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { routes } from '../../../../types/generic/routes';
import { allDocsHaveState } from '../../../../helpers/utils/uploadDocumentHelpers';
import { getJourney } from '../../../../helpers/utils/urlManipulations';

type Props = {
    documents: UploadDocument[];
    startUpload: () => Promise<void>;
};

const DocumentUploadingStage = ({ documents, startUpload }: Props): React.JSX.Element => {
    const journey = getJourney();
    const pageHeader =
        journey === 'update' ? 'Uploading additional files' : 'Your documents are uploading';

    useTitle({ pageTitle: 'Uploading documents' });
    const navigate = useNavigate();
    const uploadStartedRef = useRef<boolean>(false);

    useEffect(() => {
        if (!uploadStartedRef.current) {
            if (!allDocsHaveState(documents, DOCUMENT_UPLOAD_STATE.SELECTED)) {
                navigate(routes.HOME);
                return;
            }

            uploadStartedRef.current = true;
            startUpload();
        }
    }, []);

    if (!uploadStartedRef.current && !allDocsHaveState(documents, DOCUMENT_UPLOAD_STATE.SELECTED)) {
        return <></>;
    }

    return (
        <>
            <h1 data-testid="arf-upload-uploading-stage-header">{pageHeader}</h1>
            <WarningCallout id="upload-stage-warning">
                <WarningCallout.Label headingLevel="h2">Stay on this page</WarningCallout.Label>
                <p>
                    Do not close or navigate away from this page until upload is complete.{' '}
                    {documents.some((doc) => doc.docType === DOCUMENT_TYPE.LLOYD_GEORGE) && (
                        <span>
                            Your Lloyd George files will be combined into one document when the
                            upload is complete.{' '}
                            {journey === 'update' &&
                                'your files will be added to the existing Lloyd George record when upload is complete.'}
                        </span>
                    )}
                </p>
            </WarningCallout>
            <Table
                responsive
                caption="Your documents are uploading"
                captionProps={{
                    className: 'nhsuk-u-visually-hidden',
                }}
            >
                <Table.Head>
                    <Table.Row>
                        <Table.Cell width="63%">Filename</Table.Cell>
                        <Table.Cell>Upload progress</Table.Cell>
                    </Table.Row>
                </Table.Head>
                <Table.Body>
                    {documents.map((document) => (
                        <Table.Row key={document.id}>
                            <Table.Cell>{document.file.name}</Table.Cell>
                            <Table.Cell className="table-cell-uploading-cell-wide">
                                <progress
                                    aria-label={`Uploading ${document.file.name}`}
                                    max="100"
                                    value={document.progress}
                                    className={`${document.progress === 100 ? 'complete' : ''}`}
                                ></progress>
                                <output
                                    className="ml-4"
                                    aria-label={`${document.file.name} upload status`}
                                >
                                    {`${Math.round(document.progress!)}% uploaded`}
                                </output>
                            </Table.Cell>
                        </Table.Row>
                    ))}
                </Table.Body>
            </Table>
            {documents.some((d) => d.state === DOCUMENT_UPLOAD_STATE.SCANNING) && (
                <div id="virus-scan-status">
                    <div className="nhsuk-inset-text">
                        <span className="nhsuk-u-visually-hidden">Information: </span>
                        <p>Virus scan in progress...</p>
                    </div>
                </div>
            )}
        </>
    );
};

export default DocumentUploadingStage;
