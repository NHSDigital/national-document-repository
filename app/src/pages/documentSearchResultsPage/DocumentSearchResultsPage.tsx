import { Dispatch, SetStateAction, useEffect, useRef, useState } from 'react';
import { SearchResult } from '../../types/generic/searchResult';
import DocumentSearchResults from '../../components/blocks/_arf/documentSearchResults/DocumentSearchResults';
import { Outlet, Route, Routes, useNavigate } from 'react-router-dom';
import { routeChildren, routes } from '../../types/generic/routes';
import { SUBMISSION_STATE } from '../../types/pages/documentSearchResultsPage/types';
import ProgressBar from '../../components/generic/progressBar/ProgressBar';
import ServiceError from '../../components/layout/serviceErrorBox/ServiceErrorBox';
import DocumentSearchResultsOptions from '../../components/blocks/_arf/documentSearchResultsOptions/DocumentSearchResultsOptions';
import { AxiosError } from 'axios';
import getDocumentSearchResults from '../../helpers/requests/getDocumentSearchResults';
import useBaseAPIHeaders from '../../helpers/hooks/useBaseAPIHeaders';
import DeleteSubmitStage from '../../components/blocks/_delete/deleteSubmitStage/DeleteSubmitStage';
import { DOCUMENT_TYPE } from '../../types/pages/UploadDocumentsPage/types';
import usePatient from '../../helpers/hooks/usePatient';
import useBaseAPIUrl from '../../helpers/hooks/useBaseAPIUrl';
import ErrorBox from '../../components/layout/errorBox/ErrorBox';
import { errorToParams } from '../../helpers/utils/errorToParams';
import useTitle from '../../helpers/hooks/useTitle';
import { getLastURLPath } from '../../helpers/utils/urlManipulations';
import PatientSummary from '../../components/generic/patientSummary/PatientSummary';
import { isMock } from '../../helpers/utils/isLocal';
import useConfig from '../../helpers/hooks/useConfig';
import { buildSearchResult } from '../../helpers/test/testBuilders';

const DocumentSearchResultsPage = (): React.JSX.Element => {
    const patientDetails = usePatient();

    const nhsNumber: string = patientDetails?.nhsNumber ?? '';
    const [searchResults, setSearchResults] = useState<Array<SearchResult>>([]);
    const [submissionState, setSubmissionState] = useState(SUBMISSION_STATE.INITIAL);
    const [downloadState, setDownloadState] = useState(SUBMISSION_STATE.INITIAL);
    const navigate = useNavigate();
    const baseUrl = useBaseAPIUrl();
    const baseHeaders = useBaseAPIHeaders();
    const config = useConfig();
    const mounted = useRef(false);

    useEffect(() => {
        const onPageLoad = async (): Promise<void> => {
            setSubmissionState(SUBMISSION_STATE.PENDING);

            try {
                const results = await getDocumentSearchResults({
                    nhsNumber,
                    baseUrl,
                    baseHeaders,
                });
                setSearchResults(results ?? []);

                setSubmissionState(SUBMISSION_STATE.SUCCEEDED);
            } catch (e) {
                const error = e as AxiosError;
                if (isMock(error)) {
                    if (config.mockLocal.uploading) {
                        setSubmissionState(SUBMISSION_STATE.BLOCKED);
                    } else if (config.mockLocal.recordUploaded) {
                        setSearchResults([buildSearchResult(), buildSearchResult()]);
                        setSubmissionState(SUBMISSION_STATE.SUCCEEDED);
                    }
                } else if (error.response?.status === 403) {
                    navigate(routes.SESSION_EXPIRED);
                } else if (error.response?.status && error.response?.status >= 500) {
                    navigate(routes.SERVER_ERROR + errorToParams(error));
                } else if (error.response?.status === 423) {
                    setSubmissionState(SUBMISSION_STATE.BLOCKED);
                } else {
                    setSubmissionState(SUBMISSION_STATE.FAILED);
                }
            }
        };
        if (!mounted.current) {
            mounted.current = true;
            void onPageLoad();
        }
    }, [nhsNumber, navigate, baseUrl, baseHeaders, config]);
    const pageHeader = 'Manage this Lloyd George record';
    useTitle({ pageTitle: pageHeader });

    return (
        <>
            <div>
                <Routes>
                    <Route
                        index
                        element={
                            <DocumentSearchResultsPageIndex
                                submissionState={submissionState}
                                nhsNumber={nhsNumber}
                                downloadState={downloadState}
                                setDownloadState={setDownloadState}
                                searchResults={searchResults}
                                pageHeader={pageHeader}
                            />
                        }
                    />
                    <Route
                        path={getLastURLPath(routeChildren.ARF_DELETE) + '/*'}
                        element={
                            <DeleteSubmitStage
                                recordType="Lloyd George"
                                numberOfFiles={searchResults.length}
                                docType={DOCUMENT_TYPE.ALL}
                                resetDocState={(): null => null}
                            />
                        }
                    />
                </Routes>

                <Outlet />
            </div>
        </>
    );
};

type PageIndexArgs = {
    submissionState: SUBMISSION_STATE;
    downloadState: SUBMISSION_STATE;
    setDownloadState: Dispatch<SetStateAction<SUBMISSION_STATE>>;
    searchResults: SearchResult[];
    pageHeader: string;
    nhsNumber: string;
};
const DocumentSearchResultsPageIndex = ({
    submissionState,
    downloadState,
    searchResults,
    nhsNumber,
    setDownloadState,
}: PageIndexArgs): React.JSX.Element => {
    const pageHeader = 'Manage this Lloyd George record';
    useTitle({ pageTitle: pageHeader });

    return (
        <>
            <h1 id="download-page-title">{pageHeader}</h1>

            {(submissionState === SUBMISSION_STATE.FAILED ||
                downloadState === SUBMISSION_STATE.FAILED) && <ServiceError />}

            <PatientSummary showDeceasedTag />

            {submissionState === SUBMISSION_STATE.PENDING && (
                <ProgressBar status="Loading..."></ProgressBar>
            )}
            {submissionState === SUBMISSION_STATE.BLOCKED && (
                <p>
                    There are already files being uploaded for this patient, please try again in a
                    few minutes.
                </p>
            )}

            {submissionState === SUBMISSION_STATE.SUCCEEDED && (
                <>
                    {searchResults.length && nhsNumber ? (
                        <>
                            <DocumentSearchResults searchResults={searchResults} />
                            <DocumentSearchResultsOptions
                                nhsNumber={nhsNumber}
                                downloadState={downloadState}
                                updateDownloadState={setDownloadState}
                            />
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

            {downloadState === SUBMISSION_STATE.FAILED && (
                <ErrorBox
                    messageTitle={'There is a problem with the documents'}
                    messageBody={'An error has occurred while preparing your download'}
                    errorBoxSummaryId={'error-box-summary'}
                />
            )}
        </>
    );
};

export default DocumentSearchResultsPage;
