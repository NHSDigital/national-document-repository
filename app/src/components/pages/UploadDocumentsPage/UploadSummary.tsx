import { Details, Table, WarningCallout } from "nhsuk-react-components";
import React from "react";
import {DOCUMENT_UPLOAD_STATE, UploadDocument} from "../../../types/pages/UploadDocumentsPage/types";
import ErrorBox from "../ErrorBox/ErrorBox";
import formatFileSize from "../../../helpers/utils/formatFileSize";
import {getFormattedDate} from "../../../helpers/utils/formatDate";
import PatientSummary from "../../patientSummary/PatientSummary";
import {PatientDetails} from "../../../types/components/types";

export interface Props {
  documents : Array<UploadDocument>
}
const UploadSummary = ({documents} : Props ) => {
    const successfulUploads = documents.filter((document) => {
        return document.state === DOCUMENT_UPLOAD_STATE.SUCCEEDED;
    });
    const failedUploads = documents.filter((document) => {
        return document.state === DOCUMENT_UPLOAD_STATE.FAILED;
    });

    const tableMargin = { marginBottom: 50 };
    const tableCaption = (
        <>
            <h3>
                {failedUploads.length} of {documents.length} files failed to upload
            </h3>
            <span className="nhsuk-error-message" id="example-error">
                <span className="nhsuk-u-visually-hidden">Error:</span>Documents that have failed to upload
            </span>
        </>
    );

    const mockPatientDetails:Partial<PatientDetails> = {
        nhsNumber: "111111111",
        familyName: "test",
        givenName: ["Gremlin", "Junior"],
        birthDate: "5/12/2022",
        postalCode: "BS37 5DH",
    }

    return (
        <section>
            {failedUploads.length > 0 && (
                <ErrorBox
                    errorBoxSummaryId={"failed-document-uploads-summary-title"}
                    errorInputLink={"#failed-uploads"}
                    messageTitle={"There is a problem"}
                    messageLinkBody={"Documents that have failed to upload"}
                    messageBody={
                        "Some documents failed to upload. You can try to upload the documents again if you wish, or they must be printed and sent via PCSE"
                    }
                ></ErrorBox>
            )}
            <h1 id="upload-summary-header">Upload Summary</h1>
            {failedUploads.length > 0 && (
                <div className={"nhsuk-form-group--error"}>
                    <Table responsive caption={tableCaption} style={tableMargin} id="failed-uploads">
                        <Table.Body>
                            {failedUploads.map((document) => {
                                return (
                                    <Table.Row key={document.id}>
                                        <Table.Cell>{document.file.name}</Table.Cell>
                                        <Table.Cell>{formatFileSize(document.file.size)}</Table.Cell>
                                    </Table.Row>
                                );
                            })}
                        </Table.Body>
                    </Table>
                </div>
            )}
            {failedUploads.length === 0 && (
                <h2 id="upload-summary-confirmation">All documents have been successfully uploaded on {getFormattedDate(new Date())}</h2>
            )}
            {successfulUploads.length > 0 && (
                <>
                    <Details style={tableMargin}>
                        <Details.Summary aria-label="View successfully uploaded documents">
                            View successfully uploaded documents
                        </Details.Summary>
                        <Details.Text>
                            <Table
                                responsive
                                caption="Successfully uploaded documents"
                                captionProps={{
                                    className: "nhsuk-u-visually-hidden",
                                }}
                                id="successful-uploads"
                            >
                                <Table.Head role="rowgroup">
                                    <Table.Row>
                                        <Table.Cell>File Name</Table.Cell>
                                        <Table.Cell>File Size</Table.Cell>
                                    </Table.Row>
                                </Table.Head>
                                <Table.Body>
                                    {successfulUploads.map((document) => {
                                        return (
                                            <Table.Row key={document.id}>
                                                <Table.Cell>{document.file.name}</Table.Cell>
                                                <Table.Cell>{formatFileSize(document.file.size)}</Table.Cell>
                                            </Table.Row>
                                        );
                                    })}
                                </Table.Body>
                            </Table>
                        </Details.Text>
                    </Details>
                </>
            )}
            <PatientSummary patientDetails={mockPatientDetails} />

            <WarningCallout id="close-page-warning" style={{ marginTop: 75 }}>
                <WarningCallout.Label>Before you close this page</WarningCallout.Label>
                <ul>
                    <li>You could take a screenshot of this summary page and attach it to the patient&apos;s record</li>
                    <li>
                        When you have finished uploading, and the patient is deducted from your practice, delete all
                        temporary files created for upload on your computer
                    </li>
                    <li>
                        If you have accidentally uploaded incorrect documents, please contact Primary Care Support
                        England (PSCE)
                    </li>
                </ul>
            </WarningCallout>
        </section>
    );
};

export default UploadSummary;
