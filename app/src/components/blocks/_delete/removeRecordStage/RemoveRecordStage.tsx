import React, { Dispatch, SetStateAction, useEffect, useRef, useState } from 'react';
import useTitle from '../../../../helpers/hooks/useTitle';
import { Button, Table, WarningCallout } from 'nhsuk-react-components';
import { SearchResult } from '../../../../types/generic/searchResult';
import getDocumentSearchResults from '../../../../helpers/requests/getDocumentSearchResults';
import usePatient from '../../../../helpers/hooks/usePatient';
import { SUBMISSION_STATE } from '../../../../types/pages/documentSearchResultsPage/types';
import useBaseAPIUrl from '../../../../helpers/hooks/useBaseAPIUrl';
import useBaseAPIHeaders from '../../../../helpers/hooks/useBaseAPIHeaders';
import { AxiosError } from 'axios';
import { Outlet, Route, Routes, useNavigate } from 'react-router-dom';
import { routeChildren, routes } from '../../../../types/generic/routes';
import { errorToParams } from '../../../../helpers/utils/errorToParams';
import ServiceError from '../../../layout/serviceErrorBox/ServiceErrorBox';
import { getFormattedDatetime } from '../../../../helpers/utils/formatDatetime';
import ProgressBar from '../../../generic/progressBar/ProgressBar';
import { isMock } from '../../../../helpers/utils/isLocal';
import { buildSearchResult } from '../../../../helpers/test/testBuilders';
import { getLastURLPath } from '../../../../helpers/utils/urlManipulations';
import DeleteSubmitStage from '../deleteSubmitStage/DeleteSubmitStage';
import { DOCUMENT_TYPE } from '../../../../types/pages/UploadDocumentsPage/types';
import DeleteResultStage from '../deleteResultStage/DeleteResultStage';
import { DOWNLOAD_STAGE } from '../../../../types/generic/downloadStage';
import PatientSummary from '../../../generic/patientSummary/PatientSummary';
import BackButton from '../../../generic/backButton/BackButton';
import useRole from '../../../../helpers/hooks/useRole';
import { REPOSITORY_ROLE } from '../../../../types/generic/authRole';

export type Props = {
    numberOfFiles: number;
    recordType: string;
    setDownloadStage: Dispatch<SetStateAction<DOWNLOAD_STAGE>>;
    resetDocState: () => void;
};

const RemoveRecordStage = ({
    numberOfFiles,
    recordType,
    setDownloadStage,
    resetDocState,
}: Props): React.JSX.Element => {
    useTitle({ pageTitle: 'Remove record' });
    const patientDetails = usePatient();
    const [submissionState, setSubmissionState] = useState(SUBMISSION_STATE.PENDING);

    const role = useRole();

    const baseUrl = useBaseAPIUrl();
    const baseHeaders = useBaseAPIHeaders();
    const nhsNumber: string = patientDetails?.nhsNumber ?? '';
    const navigate = useNavigate();

    const [searchResults, setSearchResults] = useState<Array<SearchResult>>([]);

    const mounted = useRef(false);
    useEffect(() => {
        const onSuccess = (result: Array<SearchResult>): void => {
            setSearchResults(result);
            setSubmissionState(SUBMISSION_STATE.SUCCEEDED);
        };

        const onPageLoad = async (): Promise<void> => {
            try {
                const results = await getDocumentSearchResults({
                    nhsNumber,
                    baseUrl,
                    baseHeaders,
                });
                onSuccess(results ?? []);
            } catch (e) {
                const error = e as AxiosError;
                if (isMock(error)) {
                    onSuccess([buildSearchResult(), buildSearchResult()]);
                } else if (error.response?.status === 403) {
                    navigate(routes.SESSION_EXPIRED);
                } else if (error.response?.status && error.response?.status >= 500) {
                    navigate(routes.SERVER_ERROR + errorToParams(error));
                } else {
                    setSubmissionState(SUBMISSION_STATE.FAILED);
                }
            }
        };
        if (!mounted.current) {
            mounted.current = true;
            void onPageLoad();
        }
    }, [
        patientDetails,
        searchResults,
        nhsNumber,
        setSearchResults,
        setSubmissionState,
        navigate,
        baseUrl,
        baseHeaders,
    ]);

    const hasDocuments = !!searchResults.length && !!patientDetails;

    const PageIndexView = (): React.JSX.Element => (
        <>
            <BackButton />
            <h1>Remove this {recordType} record</h1>

            {role !== REPOSITORY_ROLE.PCSE && (
                <WarningCallout>
                    <WarningCallout.Label>Before removing</WarningCallout.Label>
                    <p data-testid="remove-record-warning-text">
                        Only permanently remove this patient record if you have a valid reason to.
                        For example, you confirmed these files have reached the end of their{' '}
                        <a
                            href="https://transform.england.nhs.uk/information-governance/guidance/records-management-code/records-management-code-of-practice/#appendix-ii-retention-schedule"
                            target="_blank"
                            rel="noreferrer"
                            aria-label="Retention schedule - this link will open in a new tab"
                        >
                            retention period
                        </a>
                        .
                    </p>
                </WarningCallout>
            )}

            <PatientSummary showDeceasedTag />

            {submissionState === SUBMISSION_STATE.PENDING && <ProgressBar status="Loading..." />}

            {submissionState === SUBMISSION_STATE.FAILED && <ServiceError />}

            {submissionState === SUBMISSION_STATE.SUCCEEDED && (
                <>
                    {hasDocuments ? (
                        <>
                            <Table caption="List of files in record" id="current-documents-table">
                                <Table.Head>
                                    <Table.Row>
                                        <Table.Cell>Filename</Table.Cell>
                                        <Table.Cell>Upload date</Table.Cell>
                                    </Table.Row>
                                </Table.Head>

                                <Table.Body>
                                    {searchResults.map(({ fileName, created }: SearchResult) => {
                                        return (
                                            <Table.Row key={fileName}>
                                                <Table.Cell>
                                                    <div>{fileName}</div>
                                                </Table.Cell>
                                                <Table.Cell>
                                                    {getFormattedDatetime(new Date(created))}
                                                </Table.Cell>
                                            </Table.Row>
                                        );
                                    })}
                                </Table.Body>
                            </Table>
                        </>
                    ) : (
                        <p>
                            <strong id="no-files-message">
                                There are no documents available for this patient.
                            </strong>
                        </p>
                    )}
                </>
            )}

            {(submissionState === SUBMISSION_STATE.FAILED ||
                submissionState === SUBMISSION_STATE.SUCCEEDED) && (
                <div className="align-bottom h-100">
                    {submissionState === SUBMISSION_STATE.SUCCEEDED && (
                        <Button
                            data-testid="remove-btn"
                            onClick={(): void => {
                                navigate(routeChildren.LLOYD_GEORGE_DELETE_CONFIRMATION);
                            }}
                        >
                            Remove all files
                        </Button>
                    )}
                </div>
            )}
        </>
    );

    return (
        <>
            <Routes>
                <Route index element={PageIndexView()}></Route>
                <Route
                    path={getLastURLPath(routeChildren.LLOYD_GEORGE_DELETE_CONFIRMATION)}
                    element={
                        <DeleteSubmitStage
                            docType={DOCUMENT_TYPE.LLOYD_GEORGE}
                            numberOfFiles={numberOfFiles}
                            recordType="Lloyd George"
                            resetDocState={resetDocState}
                        />
                    }
                ></Route>
                <Route
                    path={getLastURLPath(routeChildren.ARF_DELETE_CONFIRMATION)}
                    element={
                        <DeleteSubmitStage
                            docType={DOCUMENT_TYPE.LLOYD_GEORGE}
                            numberOfFiles={numberOfFiles}
                            recordType="Lloyd George"
                            resetDocState={resetDocState}
                        />
                    }
                ></Route>
                <Route
                    path={getLastURLPath(routeChildren.LLOYD_GEORGE_DELETE_COMPLETE)}
                    element={
                        <DeleteResultStage
                            numberOfFiles={numberOfFiles}
                            setDownloadStage={setDownloadStage}
                        />
                    }
                ></Route>
            </Routes>
            <Outlet></Outlet>
        </>
    );
};
export default RemoveRecordStage;
