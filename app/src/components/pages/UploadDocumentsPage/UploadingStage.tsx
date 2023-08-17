import React from 'react';
import {
  DOCUMENT_UPLOAD_STATE,
  StageProps,
  UploadDocument
} from '../../../types/pages/UploadDocumentsPage/types';
import { Table, WarningCallout } from "nhsuk-react-components";
import formatFileSize from "../../../helpers/utils/formatFileSize";


function UploadingStage({ stage, setStage, documents }: StageProps) {
  const uploadStateMessages : any = {
        [DOCUMENT_UPLOAD_STATE.SELECTED]: "Waiting...",
        [DOCUMENT_UPLOAD_STATE.UPLOADING]: "Uploading...",
        [DOCUMENT_UPLOAD_STATE.SUCCEEDED]: "Uploaded",
        [DOCUMENT_UPLOAD_STATE.FAILED]: "Upload failed",
    };
  const docs = documents.map((doc: UploadDocument) => ({
    ...doc,
    file: doc.file.name
  }));
  return  <>
                    <h1>Your documents are uploading</h1>
                    <WarningCallout>
                        <WarningCallout.Label>Stay on this page</WarningCallout.Label>
                        <p>Do not close or navigate away from this browser until upload is complete.</p>
                    </WarningCallout>
                    <Table
                        responsive
                        caption="Your documents are uploading"
                        captionProps={{
                            className: "nhsuk-u-visually-hidden",
                        }}
                    >
                        <Table.Head role="rowgroup">
                            <Table.Row>
                                <Table.Cell>File Name</Table.Cell>
                                <Table.Cell>File Size</Table.Cell>
                                {/*<Table.Cell>File Upload Progress</Table.Cell>*/}
                            </Table.Row>
                        </Table.Head>
                        <Table.Body>
                            {documents.map((document) => (
                                <Table.Row key={document.id}>
                                    <Table.Cell>{document.file.name}</Table.Cell>
                                    <Table.Cell>{formatFileSize(document.file.size)}</Table.Cell>
                                    {/*<Table.Cell>*/}
                                    {/*    <progress*/}
                                    {/*        aria-label={`Uploading ${document.file.name}`}*/}
                                    {/*        max="100"*/}
                                    {/*        value={document.progress}*/}
                                    {/*    ></progress>*/}
                                    {/*    <p role="status" aria-label={`${document.file.name} upload status`}>*/}
                                    {/*        {document.state === DOCUMENT_UPLOAD_STATE.UPLOADING ? (*/}
                                    {/*            <> {Math.round(document.progress)}% uploaded... </>*/}
                                    {/*        ) : (*/}
                                    {/*            uploadStateMessages[document.state]*/}
                                    {/*        )}*/}
                                    {/*    </p>*/}
                                    {/*</Table.Cell>*/}
                                </Table.Row>
                            ))}
                        </Table.Body>
                    </Table>
                </>;
}

export default UploadingStage;
