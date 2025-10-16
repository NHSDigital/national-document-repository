import React from 'react';
import {
    DOCUMENT_UPLOAD_STATE,
    UploadDocument,
} from '../../../../types/pages/UploadDocumentsPage/types';
import { Table, WarningCallout } from 'nhsuk-react-components';
import formatFileSize from '../../../../helpers/utils/formatFileSize';
import useTitle from '../../../../helpers/hooks/useTitle';
import { getUploadMessage } from '../../../../helpers/utils/uploadDocumentHelpers';

interface Props {
    documents: Array<UploadDocument>;
}

const UploadingStage = ({ documents }: Props): React.JSX.Element => {
    const pageHeader = 'Your documents are uploading';
    useTitle({ pageTitle: 'Uploading documents' });

    return (
        <>
            <h1 data-testid="arf-upload-uploading-stage-header">{pageHeader}</h1>
            <WarningCallout id="upload-stage-warning">
                <WarningCallout.Label headingLevel="h2">Stay on this page</WarningCallout.Label>
                <p>Do not close or navigate away from this browser until upload is complete.</p>
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
                        <Table.Cell>File Name</Table.Cell>
                        <Table.Cell>File Size</Table.Cell>
                        <Table.Cell>File Upload Progress</Table.Cell>
                    </Table.Row>
                </Table.Head>
                <Table.Body>
                    {documents.map((document) => {
                        const isScanning = document.state === DOCUMENT_UPLOAD_STATE.SCANNING;
                        return (
                            <Table.Row key={document.id}>
                                <Table.Cell>{document.file.name}</Table.Cell>
                                <Table.Cell className="table-cell-uploading-cell-thin">
                                    {formatFileSize(document.file.size)}
                                </Table.Cell>
                                <Table.Cell className="table-cell-uploading-cell-wide">
                                    <progress
                                        aria-label={`Uploading ${document.file.name}`}
                                        max="100"
                                        value={isScanning ? undefined : document.progress}
                                    ></progress>
                                    <output aria-label={`${document.file.name} upload status`}>
                                        {getUploadMessage(document)}
                                    </output>
                                </Table.Cell>
                            </Table.Row>
                        );
                    })}
                </Table.Body>
            </Table>
        </>
    );
};

export default UploadingStage;
