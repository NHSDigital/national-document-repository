import { Button } from 'nhsuk-react-components';
import SpinnerButton from '../../../generic/spinnerButton/SpinnerButton';
import { routeChildren, routes } from '../../../../types/generic/routes';
import { SUBMISSION_STATE } from '../../../../types/pages/documentSearchResultsPage/types';
import { useNavigate } from 'react-router-dom';
import getPresignedUrlForZip from '../../../../helpers/requests/getPresignedUrlForZip';
import { AxiosError } from 'axios';
import { useEffect, useRef, useState } from 'react';
import useBaseAPIHeaders from '../../../../helpers/hooks/useBaseAPIHeaders';
import { DOCUMENT_TYPE } from '../../../../types/pages/UploadDocumentsPage/types';
import useBaseAPIUrl from '../../../../helpers/hooks/useBaseAPIUrl';
import { errorToParams } from '../../../../helpers/utils/errorToParams';

type Props = {
    nhsNumber: string;
    downloadState: string;
    updateDownloadState: (newState: SUBMISSION_STATE) => void;
};

interface DownloadLinkAttributes {
    url: string;
    filename: string;
}

const DocumentSearchResultsOptions = (props: Props): React.JSX.Element => {
    const navigate = useNavigate();
    const baseUrl = useBaseAPIUrl();
    const baseHeaders = useBaseAPIHeaders();
    const [linkAttributes, setLinkAttributes] = useState<DownloadLinkAttributes>({
        url: '',
        filename: '',
    });
    const linkRef = useRef<HTMLAnchorElement | null>(null);
    const [statusMessage, setStatusMessage] = useState('');
    useEffect(() => {
        switch (props.downloadState) {
            case SUBMISSION_STATE.PENDING:
                setStatusMessage('Download in progress.');
                break;
            case SUBMISSION_STATE.SUCCEEDED:
                setStatusMessage('Download complete.');
                break;
            case SUBMISSION_STATE.FAILED:
                setStatusMessage('Download failed.');
                break;
            default:
                setStatusMessage('');
        }
    }, [props.downloadState]);

    useEffect(() => {
        if (linkRef.current && linkAttributes.url) {
            linkRef.current.click();
        }
    }, [linkAttributes]);

    const downloadAll = async (): Promise<void> => {
        props.updateDownloadState(SUBMISSION_STATE.PENDING);
        try {
            const preSignedUrl = await getPresignedUrlForZip({
                nhsNumber: props.nhsNumber,
                baseUrl: baseUrl,
                baseHeaders,
                docType: DOCUMENT_TYPE.ALL,
            });

            const filename = `patient-record-${props.nhsNumber}`;

            setLinkAttributes({ url: preSignedUrl, filename: filename });

            props.updateDownloadState(SUBMISSION_STATE.SUCCEEDED);
        } catch (e) {
            const error = e as AxiosError;
            if (error.response?.status === 403) {
                navigate(routes.SESSION_EXPIRED);
            } else {
                navigate(routes.SERVER_ERROR + errorToParams(error));
            }
            props.updateDownloadState(SUBMISSION_STATE.FAILED);
        }
    };

    const deleteAllDocuments = (): void => {
        navigate(routeChildren.ARF_DELETE_CONFIRMATION);
    };

    return (
        <>
            <div
                id="download-status"
                aria-live="polite"
                role="status"
                className="nhsuk-u-visually-hidden"
            >
                {statusMessage}
            </div>
            <div className="search-result-spinner-div">
                {props.downloadState === SUBMISSION_STATE.PENDING ? (
                    <SpinnerButton
                        id="download-spinner"
                        status="Downloading documents"
                        disabled={true}
                    />
                ) : (
                    <Button type="button" id="download-documents" onClick={downloadAll}>
                        Download all documents
                    </Button>
                )}
                <a
                    hidden
                    id="download-link"
                    ref={linkRef}
                    href={linkAttributes.url}
                    download={linkAttributes.filename}
                >
                    Download Manifest URL
                </a>
                <Button
                    className="nhsuk-button nhsuk-button--secondary left-margin"
                    data-testid="delete-all-documents-btn"
                    onClick={deleteAllDocuments}
                >
                    Remove all documents
                </Button>
            </div>
            {props.downloadState === SUBMISSION_STATE.SUCCEEDED && (
                <p>
                    <strong>All documents have been successfully downloaded.</strong>
                </p>
            )}
        </>
    );
};

export default DocumentSearchResultsOptions;
