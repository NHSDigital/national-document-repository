import { Dispatch, SetStateAction, useEffect, useRef, useState } from 'react';
import usePatient from '../../../../helpers/hooks/usePatient';
import { Outlet, Route, Routes, useNavigate } from 'react-router-dom';
import useTitle from '../../../../helpers/hooks/useTitle';
import { SearchResult } from '../../../../types/generic/searchResult';
import { SEARCH_AND_DOWNLOAD_STATE } from '../../../../types/pages/documentSearchResultsPage/types';
import useBaseAPIUrl from '../../../../helpers/hooks/useBaseAPIUrl';
import useBaseAPIHeaders from '../../../../helpers/hooks/useBaseAPIHeaders';
import getDocumentSearchResults from '../../../../helpers/requests/getDocumentSearchResults';
import { AxiosError } from 'axios';
import { routeChildren, routes } from '../../../../types/generic/routes';
import { errorToParams } from '../../../../helpers/utils/errorToParams';
import ProgressBar from '../../../generic/progressBar/ProgressBar';
import { DOCUMENT_TYPE } from '../../../../types/pages/UploadDocumentsPage/types';
import { isMock } from '../../../../helpers/utils/isLocal';
import LloydGeorgeSelectSearchResults from '../lloydGeorgeSelectSearchResults/LloydGeorgeSelectSearchResults';
import PatientSummary from '../../../generic/patientSummary/PatientSummary';
import LloydGeorgeDownloadStage from '../lloydGeorgeDownloadStage/LloydGeorgeDownloadStage';
import { buildSearchResult } from '../../../../helpers/test/testBuilders';
import { getLastURLPath } from '../../../../helpers/utils/urlManipulations';
import LgDownloadComplete from '../lloydGeorgeDownloadComplete/LloydGeorgeDownloadComplete';
import { DOWNLOAD_STAGE } from '../../../../types/generic/downloadStage';

export type Props = {
    numberOfFiles: number;
    setDownloadStage: Dispatch<SetStateAction<DOWNLOAD_STAGE>>;
};

const PageHeader = 'Download the Lloyd George record for this patient';

type PageIndexViewProps = {
    submissionSearchState: SEARCH_AND_DOWNLOAD_STATE;
    setSubmissionSearchState: Dispatch<SetStateAction<SEARCH_AND_DOWNLOAD_STATE>>;
    searchResults: Array<SearchResult>;
    selectedDocuments: Array<string>;
    setSelectedDocuments: Dispatch<SetStateAction<Array<string>>>;
};
const SelectDownloadPageIndexView = ({
    submissionSearchState,
    setSubmissionSearchState,
    searchResults,
    selectedDocuments,
    setSelectedDocuments,
}: PageIndexViewProps): React.JSX.Element => (
    <>
        {submissionSearchState === SEARCH_AND_DOWNLOAD_STATE.SEARCH_PENDING && (
            <>
                <h1 id="download-page-title">{PageHeader}</h1>
                <PatientSummary showDeceasedTag />
                <ProgressBar status="Loading..."></ProgressBar>
            </>
        )}
        {submissionSearchState === SEARCH_AND_DOWNLOAD_STATE.SEARCH_SUCCEEDED &&
            !!searchResults.length && (
                <LloydGeorgeSelectSearchResults
                    searchResults={searchResults}
                    setSubmissionSearchState={setSubmissionSearchState}
                    setSelectedDocuments={setSelectedDocuments}
                    selectedDocuments={selectedDocuments}
                />
            )}
    </>
);
const LloydGeorgeSelectDownloadStage = ({
    setDownloadStage,
    numberOfFiles,
}: Props): React.JSX.Element => {
    const mounted = useRef(false);
    const navigate = useNavigate();
    const patientDetails = usePatient();
    const nhsNumber = patientDetails?.nhsNumber ?? '';
    const [searchResults, setSearchResults] = useState<Array<SearchResult>>([]);
    const [submissionSearchState, setSubmissionSearchState] = useState(
        SEARCH_AND_DOWNLOAD_STATE.INITIAL,
    );
    const [selectedDocuments, setSelectedDocuments] = useState<Array<string>>([]);
    const baseUrl = useBaseAPIUrl();
    const baseHeaders = useBaseAPIHeaders();
    const numberOfFilesForDownload =
        selectedDocuments?.length || searchResults.length || numberOfFiles;
    useTitle({ pageTitle: PageHeader });

    useEffect(() => {
        const onPageLoad = async (): Promise<void> => {
            setSubmissionSearchState(SEARCH_AND_DOWNLOAD_STATE.SEARCH_PENDING);
            if (!nhsNumber) {
                navigate(routes.SEARCH_PATIENT);
                return;
            }
            try {
                // This check is in place for when we navigate directly to a full download,
                // in that instance we do not need to get a list of selectable files as we will download all files
                if (window.location.pathname === routeChildren.LLOYD_GEORGE_DOWNLOAD) {
                    const results = await getDocumentSearchResults({
                        nhsNumber,
                        baseUrl,
                        baseHeaders,
                        docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    });
                    setSearchResults(results ?? []);
                    setSubmissionSearchState(SEARCH_AND_DOWNLOAD_STATE.SEARCH_SUCCEEDED);
                }
            } catch (e) {
                const error = e as AxiosError;
                if (isMock(error)) {
                    setSearchResults([
                        buildSearchResult(),
                        buildSearchResult({ fileName: 'fileName2.pdf', id: '1234qwer-241ewewr-2' }),
                        buildSearchResult({ fileName: 'fileName3.pdf', id: '1234qwer-241ewewr-3' }),
                    ]);
                    setSubmissionSearchState(SEARCH_AND_DOWNLOAD_STATE.SEARCH_SUCCEEDED);
                } else if (error.response?.status === 403) {
                    navigate(routes.SESSION_EXPIRED);
                } else {
                    navigate(routes.SERVER_ERROR + errorToParams(error));
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
        selectedDocuments,
        nhsNumber,
        setSearchResults,
        navigate,
        baseUrl,
        baseHeaders,
    ]);

    return (
        <>
            <Routes>
                <Route
                    index
                    element={
                        <SelectDownloadPageIndexView
                            submissionSearchState={submissionSearchState}
                            setSubmissionSearchState={setSubmissionSearchState}
                            searchResults={searchResults}
                            selectedDocuments={selectedDocuments}
                            setSelectedDocuments={setSelectedDocuments}
                        />
                    }
                />
                <Route
                    path={getLastURLPath(routeChildren.LLOYD_GEORGE_DOWNLOAD_IN_PROGRESS)}
                    element={
                        <LloydGeorgeDownloadStage
                            selectedDocuments={selectedDocuments}
                            numberOfFiles={numberOfFilesForDownload}
                        />
                    }
                />
                <Route
                    path={getLastURLPath(routeChildren.LLOYD_GEORGE_DOWNLOAD_COMPLETE)}
                    element={
                        <LgDownloadComplete
                            numberOfFiles={numberOfFilesForDownload}
                            selectedDocuments={selectedDocuments}
                            searchResults={searchResults}
                        />
                    }
                />
            </Routes>

            <Outlet />
        </>
    );
};

export default LloydGeorgeSelectDownloadStage;
