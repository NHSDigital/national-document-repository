import { Button, Checkboxes, Table } from 'nhsuk-react-components';
import { SearchResult } from '../../../../types/generic/searchResult';
import { getFormattedDatetime } from '../../../../helpers/utils/formatDatetime';
import { Link, useNavigate } from 'react-router-dom';
import { routeChildren, routes } from '../../../../types/generic/routes';
import React, { Dispatch, ReactNode, SetStateAction, SyntheticEvent, useState } from 'react';
import { SEARCH_AND_DOWNLOAD_STATE } from '../../../../types/pages/documentSearchResultsPage/types';
import ErrorBox from '../../../layout/errorBox/ErrorBox';
import PatientSummary from '../../../generic/patientSummary/PatientSummary';
import BackButton from '../../../generic/backButton/BackButton';

export type Props = {
    searchResults: Array<SearchResult>;
    setSubmissionSearchState: Dispatch<SetStateAction<SEARCH_AND_DOWNLOAD_STATE>>;
    setSelectedDocuments: Dispatch<React.SetStateAction<Array<string>>>;
    selectedDocuments: Array<string>;
};

type AvailableFilesTableProps = {
    tableCaption: ReactNode;
    searchResults: Array<SearchResult>;
    setSelectedDocuments: Dispatch<React.SetStateAction<Array<string>>>;
    selectedDocuments: Array<string>;
    allowSelectDocument: boolean;
};

const AvailableFilesTable = ({
    tableCaption,
    searchResults,
    selectedDocuments,
    setSelectedDocuments,
    allowSelectDocument,
}: AvailableFilesTableProps) => {
    const toggleSelectAllFilesToDownload = () => {
        if (selectedDocuments.length < searchResults.length) {
            const downloadableItems: string[] = [];
            searchResults.forEach((result) => {
                downloadableItems.push(result.ID);
            });
            setSelectedDocuments(downloadableItems);
        } else {
            setSelectedDocuments([]);
        }
    };
    const handleChangeCheckboxes = (e: SyntheticEvent<HTMLInputElement>) => {
        const target = e.target as HTMLInputElement;
        const toggledDocumentId = target.value;
        if (target.checked) {
            setSelectedDocuments([...selectedDocuments, toggledDocumentId]);
        } else {
            setSelectedDocuments(selectedDocuments.filter((id) => id !== toggledDocumentId));
        }
    };
    return (
        <>
            {tableCaption}
            {allowSelectDocument && (
                <div>
                    <Button
                        onClick={toggleSelectAllFilesToDownload}
                        secondary={true}
                        data-testid="toggle-selection-btn"
                        type="button"
                    >
                        {selectedDocuments.length === searchResults.length && 'Deselect all files'}
                        {selectedDocuments.length < searchResults.length && 'Select all files'}
                    </Button>
                    <p>Or select individual files</p>
                </div>
            )}

            <Table
                id="available-files-table-title"
                data-testid="available-files-table-title"
                aria-label="List of files in record"
            >
                <Table.Head>
                    <Table.Row>
                        {allowSelectDocument && (
                            <Table.Cell className={'table-column-header'}>Selected</Table.Cell>
                        )}
                        <Table.Cell className={'table-column-header'}>Filename</Table.Cell>
                        <Table.Cell className={'table-column-header'}>Upload date</Table.Cell>
                    </Table.Row>
                </Table.Head>
                <Table.Body>
                    {searchResults.map((result, index) => (
                        <Table.Row
                            className="available-files-row"
                            id={`search-result-${index}`}
                            key={`document-${result.fileName + result.created}`}
                            data-testid={`search-result-${index}`}
                        >
                            {allowSelectDocument && (
                                <Table.Cell id={`selected-files-row-${index}`}>
                                    <Checkboxes onChange={handleChangeCheckboxes}>
                                        <Checkboxes.Box
                                            value={result.ID}
                                            data-testid={`checkbox-${index}`}
                                            checked={selectedDocuments.includes(result.ID)}
                                        >
                                            <span className="nhsuk-u-visually-hidden">
                                                {result.fileName}
                                            </span>
                                        </Checkboxes.Box>
                                    </Checkboxes>
                                </Table.Cell>
                            )}
                            <Table.Cell
                                id={'available-files-row-' + index + '-filename'}
                                data-testid="filename"
                            >
                                {result.fileName}
                            </Table.Cell>
                            <Table.Cell
                                id={'available-files-row-' + index + '-created-date'}
                                data-testid="created"
                            >
                                {getFormattedDatetime(new Date(result.created))}
                            </Table.Cell>
                        </Table.Row>
                    ))}
                </Table.Body>
            </Table>
        </>
    );
};

const LloydGeorgeSelectSearchResults = ({
    searchResults,
    setSubmissionSearchState,
    setSelectedDocuments,
    selectedDocuments,
}: Props) => {
    const sortByFileName = (a: SearchResult, b: SearchResult) => {
        const fileNumberOfA = parseInt(a.fileName.substring(0, a.fileName.indexOf('of')));
        const fileNumberOfB = parseInt(b.fileName.substring(0, a.fileName.indexOf('of')));
        if (fileNumberOfA && fileNumberOfB) {
            return fileNumberOfA > fileNumberOfB ? 1 : -1;
        } else {
            return a.fileName > b.fileName ? 1 : -1;
        }
    };
    const navigate = useNavigate();
    const orderedResults = [...searchResults].sort(sortByFileName);
    const tableCaption = <h2 className="nhsuk-heading-l">List of files in record</h2>;
    const [showNoOptionSelectedMessage, setShowNoOptionSelectedMessage] = useState<boolean>(false);
    const noOptionSelectedError = 'You must select a file to download or download all files';
    const pageHeader = 'Download the Lloyd George record for this patient';

    const allowSelectDocument = searchResults.length > 1;

    const handleClickSelectedDownload = () => {
        if (selectedDocuments.length === searchResults.length) {
            handleClickDownloadAll();
        } else if (selectedDocuments.length) {
            setSubmissionSearchState(SEARCH_AND_DOWNLOAD_STATE.DOWNLOAD_SELECTED);
            navigate(routeChildren.LLOYD_GEORGE_DOWNLOAD_IN_PROGRESS);
        } else {
            setShowNoOptionSelectedMessage(true);
            window.scrollTo(0, 0);
        }
    };
    const handleClickDownloadAll = () => {
        setSelectedDocuments([]);
        setSubmissionSearchState(SEARCH_AND_DOWNLOAD_STATE.DOWNLOAD_SELECTED);
        navigate(routeChildren.LLOYD_GEORGE_DOWNLOAD_IN_PROGRESS);
    };

    return (
        <>
            <BackButton />
            {showNoOptionSelectedMessage && (
                <ErrorBox
                    messageTitle={'There is a problem'}
                    messageLinkBody={noOptionSelectedError}
                    errorBoxSummaryId={'error-box-summary'}
                    errorInputLink={'#available-files-table-title'}
                    dataTestId={'download-selection-error-box'}
                />
            )}
            <h1 id="download-page-title">{pageHeader}</h1>
            <PatientSummary />
            <AvailableFilesTable
                tableCaption={tableCaption}
                searchResults={orderedResults}
                selectedDocuments={selectedDocuments}
                setSelectedDocuments={setSelectedDocuments}
                allowSelectDocument={allowSelectDocument}
            />
            <div className="align-baseline gap-4">
                {allowSelectDocument && (
                    <Button
                        onClick={handleClickSelectedDownload}
                        data-testid="download-selected-files-btn"
                    >
                        Download selected files
                    </Button>
                )}
                {!allowSelectDocument && (
                    <Button onClick={handleClickDownloadAll} data-testid="download-file-btn">
                        Download
                    </Button>
                )}
                <Link
                    id="start-again-link"
                    data-testid="start-again-link"
                    to=""
                    onClick={(e) => {
                        e.preventDefault();
                        navigate(routes.START);
                    }}
                >
                    Start again
                </Link>
            </div>
        </>
    );
};

export default LloydGeorgeSelectSearchResults;
