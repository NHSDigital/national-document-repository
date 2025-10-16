import { Button, Table } from 'nhsuk-react-components';
import useTitle from '../../../../helpers/hooks/useTitle';
import { DOCUMENT_TYPE, UploadDocument } from '../../../../types/pages/UploadDocumentsPage/types';
import BackButton from '../../../generic/backButton/BackButton';
import { useNavigate } from 'react-router-dom';
import { routeChildren, routes } from '../../../../types/generic/routes';
import { useState } from 'react';
import Pagination from '../../../generic/pagination/Pagination';
import PatientSummary, { PatientInfo } from '../../../generic/patientSummary/PatientSummary';

type Props = {
    documents: UploadDocument[];
};

const DocumentUploadConfirmStage = ({ documents }: Props): React.JSX.Element => {
    const [currentPage, setCurrentPage] = useState<number>(0);
    const navigate = useNavigate();
    const pageSize = 10;

    const pageTitle = 'Check your files before uploading';
    useTitle({ pageTitle });

    const currentItems = (): UploadDocument[] => {
        const skipCount = currentPage * pageSize;
        return documents.slice(skipCount, skipCount + pageSize);
    };

    const totalPages = (): number => {
        return Math.ceil(documents.length / pageSize);
    };

    return (
        <div className="document-upload-confirm">
            <BackButton dataTestid="go-back-link" />
            <h1>{pageTitle}</h1>

            <div className="nhsuk-inset-text">
                <p>Make sure that all files uploaded are for this patient only:</p>
                <PatientSummary>
                    <PatientSummary.Child item={PatientInfo.FULL_NAME} />
                    <PatientSummary.Child item={PatientInfo.NHS_NUMBER} />
                    <PatientSummary.Child item={PatientInfo.BIRTH_DATE} />
                </PatientSummary>
            </div>

            <p>
                Files will be combined into a single PDF document to create a Lloyd George record
                for this patient.
            </p>

            <h4>Files to be uploaded</h4>

            <Table id="selected-documents-table">
                <Table.Head>
                    <Table.Row>
                        <Table.Cell>Filename</Table.Cell>
                        <Table.Cell width="25%" className="word-break-keep-all">
                            Position
                        </Table.Cell>
                        <Table.Cell width="10%" className="word-break-keep-all">
                            <button
                                className="govuk-link"
                                rel="change"
                                data-testid="change-files-button"
                                onClick={(e): void => {
                                    e.preventDefault();
                                    navigate(routes.DOCUMENT_UPLOAD);
                                }}
                            >
                                Change files
                            </button>
                        </Table.Cell>
                    </Table.Row>
                </Table.Head>

                <Table.Body>
                    {currentItems().map((document: UploadDocument) => {
                        return (
                            <Table.Row key={document.id} id={document.file.name}>
                                <Table.Cell>
                                    <div>
                                        <strong>{document.file.name}</strong>
                                    </div>
                                </Table.Cell>
                                <Table.Cell>
                                    <div>
                                        {document.docType === DOCUMENT_TYPE.LLOYD_GEORGE
                                            ? document.position
                                            : 'N/A'}
                                    </div>
                                </Table.Cell>
                                <Table.Cell></Table.Cell>
                            </Table.Row>
                        );
                    })}
                </Table.Body>
            </Table>

            <Pagination
                totalPages={totalPages()}
                currentPage={currentPage}
                setCurrentPage={setCurrentPage}
            />

            <Button
                data-testid="confirm-button"
                onClick={(): void => {
                    navigate(routeChildren.DOCUMENT_UPLOAD_UPLOADING);
                }}
            >
                Confirm file order and upload files
            </Button>
        </div>
    );
};

export default DocumentUploadConfirmStage;
