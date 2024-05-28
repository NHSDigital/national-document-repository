import React, { useEffect } from 'react';
import { ButtonLink, Card } from 'nhsuk-react-components';
import {
    DOCUMENT_UPLOAD_STATE,
    UploadDocument,
} from '../../../../types/pages/UploadDocumentsPage/types';
import { getFormattedDate } from '../../../../helpers/utils/formatDate';
import { useNavigate } from 'react-router';
import { routes } from '../../../../types/generic/routes';
import DocumentsListView from '../../../generic/documentsListView/DocumentsListView';
import ReducedPatientInfo from '../../../generic/reducedPatientInfo/ReducedPatientInfo';
import { focusLayoutDiv } from '../../../../helpers/utils/manageFocus';
import useTitle from '../../../../helpers/hooks/useTitle';
import { GenericDocument } from '../../../../types/generic/genericDocument';

interface Props {
    documents: Array<UploadDocument>;
}

function LloydGeorgeUploadCompleteStage({ documents }: Props) {
    const navigate = useNavigate();

    // temp solution to focus on layout div so that skip-link can be selected.
    // we should remove this when this component become a separate route.
    useEffect(() => {
        focusLayoutDiv();
    }, []);

    const successfulUploads = documents.map((document) => {
        if (document.state === DOCUMENT_UPLOAD_STATE.SUCCEEDED) {
            return {
                reference: document.ref,
                id: document.id,
                fileName: document.file.name,
            };
        } else {
            return null;
        }
    }) as GenericDocument[];
    useTitle({ pageTitle: 'Record upload complete' });

    return (
        <div className="lloydgeorge_upload-complete" data-testid="upload-complete-page">
            <Card className="lloydgeorge_upload-complete_card" data-testid="upload-complete-card">
                <Card.Content className="lloydgeorge_upload-complete_card_content">
                    <Card.Heading
                        className="lloydgeorge_upload-complete_card_content_header"
                        headingLevel="h1"
                    >
                        Record uploaded for
                    </Card.Heading>
                    <ReducedPatientInfo
                        className={'lloydgeorge_upload-complete_card_content_subheader'}
                    />
                    <div className="lloydgeorge_upload-complete_card_content_subheader">
                        Date uploaded: {getFormattedDate(new Date())}
                    </div>
                </Card.Content>
            </Card>

            <div>
                <p className="lloydgeorge_upload-complete_subheader">
                    You have successfully uploaded {successfulUploads.length} file
                    {successfulUploads.length !== 1 && 's'}
                </p>
                {successfulUploads.length > 0 && (
                    <DocumentsListView
                        documentsList={successfulUploads}
                        ariaLabel={'View successfully uploaded documents'}
                    />
                )}
            </div>

            <div>
                <p className="lloydgeorge_upload-complete_subheader">What happens next</p>
                <p>
                    You have successfully created a Lloyd George record for this patient. The
                    uploaded files will be combined to make up the Lloyd George record.
                </p>
                <p>
                    You can upload more files to their record if needed, but you cannot upload
                    duplicate files with the same name as previous uploads.
                </p>
                <p style={{ marginBottom: 50 }}>
                    If you need to replace a file, you will need to remove it and re-upload it
                    again.
                </p>
            </div>

            <ButtonLink
                role="button"
                data-testid="view-record-btn"
                href="#"
                onClick={(e) => {
                    e.preventDefault();
                    navigate(routes.LLOYD_GEORGE);
                }}
            >
                View record
            </ButtonLink>

            <ButtonLink
                className="nhsuk-button nhsuk-button--secondary"
                data-testid="search-patient-btn"
                style={{ marginLeft: 18 }}
                role="button"
                href="#"
                onClick={(e) => {
                    e.preventDefault();
                    navigate(routes.SEARCH_PATIENT);
                }}
            >
                Search for a patient
            </ButtonLink>
        </div>
    );
}

export default LloydGeorgeUploadCompleteStage;
