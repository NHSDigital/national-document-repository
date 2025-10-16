import React from 'react';
import { Button, Card } from 'nhsuk-react-components';
import ReducedPatientInfo from '../../../generic/reducedPatientInfo/ReducedPatientInfo';
import useTitle from '../../../../helpers/hooks/useTitle';
import { useNavigate } from 'react-router-dom';
import { routes } from '../../../../types/generic/routes';
import DocumentsListView from '../../../generic/documentsListView/DocumentsListView';
import { SearchResult } from '../../../../types/generic/searchResult';
import { GenericDocument } from '../../../../types/generic/genericDocument';

export type Props = {
    numberOfFiles: number;
    selectedDocuments?: Array<string>;
    searchResults?: Array<SearchResult>;
};

const LloydGeorgeDownloadComplete = ({
    numberOfFiles,
    selectedDocuments,
    searchResults,
}: Props): React.JSX.Element => {
    const navigate = useNavigate();

    const selectedFilesDownload = !!selectedDocuments?.length;
    const pageHeader = 'Download complete';
    useTitle({ pageTitle: pageHeader });

    const handleReturnButtonClick = (): void => {
        navigate(routes.LLOYD_GEORGE);
    };

    const documentsList = searchResults
        ?.filter((document) => selectedDocuments?.includes(document.id))
        .map((document) => {
            return {
                ref: document.id,
                id: document.id,
                fileName: document.fileName,
            };
        }) as GenericDocument[];

    const getCardHeader = (): React.JSX.Element => {
        if (selectedFilesDownload) {
            return (
                <div data-testid="downloaded-files-card-header">
                    You have downloaded files from the record of:
                </div>
            );
        } else if (selectedDocuments) {
            return (
                <div data-testid="downloaded-record-card-header">
                    You have downloaded the record of:
                </div>
            );
        } else {
            return <div data-testid="download-complete-card-header">Download complete</div>;
        }
    };
    const pageDownloadCountId = 'downloaded-files-' + numberOfFiles + '-files';

    return (
        <div className="lloydgeorge_download-complete">
            <Card className="lloydgeorge_download-complete_details">
                <Card.Content className="lloydgeorge_download-complete_details-content">
                    <Card.Heading
                        className="lloydgeorge_download-complete_details-content_header"
                        data-testid="lloyd-george-download-complete-header"
                        headingLevel="h1"
                    >
                        {getCardHeader()}
                    </Card.Heading>
                    {!selectedDocuments && (
                        <Card.Description
                            className="lloydgeorge_download-complete_details-content_description"
                            data-testid="lloyd-george-download-complete-card-content"
                        >
                            You have successfully downloaded the{'\n'}
                            Lloyd George record of:
                        </Card.Description>
                    )}
                    <ReducedPatientInfo
                        className={'lloydgeorge_download-complete_details-content_subheader'}
                    />
                </Card.Content>
            </Card>
            {selectedFilesDownload && (
                <>
                    <p data-testid={pageDownloadCountId}>
                        You have successfully downloaded {numberOfFiles} file(s)
                    </p>
                    <DocumentsListView
                        documentsList={documentsList}
                        ariaLabel={'selected-document-list'}
                    />
                </>
            )}
            <h2 className="nhsuk-heading-l">Your responsibilities with this record</h2>
            <p>
                Everyone in a health and care organisation is responsible for managing records
                appropriately. It is important all general practice staff understand their
                responsibilities for creating, maintaining, and disposing of records appropriately.
            </p>
            <h3 className="nhsuk-heading-m">Follow the Record Management Code of Practice</h3>
            <p>
                The{' '}
                <a href="https://transform.england.nhs.uk/information-governance/guidance/records-management-code">
                    Record Management Code of Practice
                </a>{' '}
                provides a framework for consistent and effective records management, based on
                established standards.
            </p>
            <Button onClick={handleReturnButtonClick} data-testid="return-btn">
                Return to patient record
            </Button>
        </div>
    );
};

export default LloydGeorgeDownloadComplete;
