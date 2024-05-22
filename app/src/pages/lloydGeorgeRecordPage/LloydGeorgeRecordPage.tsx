import React, { useEffect, useRef, useState } from 'react';
import { DOWNLOAD_STAGE } from '../../types/generic/downloadStage';
import useBaseAPIHeaders from '../../helpers/hooks/useBaseAPIHeaders';
import DeleteSubmitStage from '../../components/blocks/_delete/deleteSubmitStage/DeleteSubmitStage';
import { getFormattedDatetime } from '../../helpers/utils/formatDatetime';
import getLloydGeorgeRecord from '../../helpers/requests/getLloydGeorgeRecord';

import LloydGeorgeViewRecordStage from '../../components/blocks/_lloydGeorge/lloydGeorgeViewRecordStage/LloydGeorgeViewRecordStage';
import { DOCUMENT_TYPE } from '../../types/pages/UploadDocumentsPage/types';
import { LG_RECORD_STAGE } from '../../types/blocks/lloydGeorgeStages';
import useBaseAPIUrl from '../../helpers/hooks/useBaseAPIUrl';
import usePatient from '../../helpers/hooks/usePatient';
import { AxiosError } from 'axios';
import useRole from '../../helpers/hooks/useRole';
import useIsBSOL from '../../helpers/hooks/useIsBSOL';
import { REPOSITORY_ROLE } from '../../types/generic/authRole';
import { routeChildren, routes } from '../../types/generic/routes';
import { Outlet, Route, Routes, useNavigate } from 'react-router';
import { errorToParams } from '../../helpers/utils/errorToParams';
import { isMock } from '../../helpers/utils/isLocal';
import moment from 'moment';
import useConfig from '../../helpers/hooks/useConfig';
import { ErrorResponse } from '../../types/generic/errorResponse';
import { getLastURLPath } from '../../helpers/utils/urlManipulations';
import RemoveRecordStage from '../../components/blocks/_delete/removeRecordStage/RemoveRecordStage';
import LloydGeorgeSelectDownloadStage from '../../components/blocks/_lloydGeorge/lloydGeorgeSelectDownloadStage/LloydGeorgeSelectDownloadStage';
import LloydGeorgeDownloadStage from '../../components/blocks/_lloydGeorge/lloydGeorgeDownloadStage/LloydGeorgeDownloadStage';

function LloydGeorgeRecordPage() {
    const patientDetails = usePatient();
    const [downloadStage, setDownloadStage] = useState(DOWNLOAD_STAGE.INITIAL);
    const [numberOfFiles, setNumberOfFiles] = useState(0);
    const [totalFileSizeInByte, setTotalFileSizeInByte] = useState(0);
    const [lastUpdated, setLastUpdated] = useState('');
    const [lloydGeorgeUrl, setLloydGeorgeUrl] = useState('');
    const baseUrl = useBaseAPIUrl();
    const baseHeaders = useBaseAPIHeaders();
    const mounted = useRef(false);
    const [stage, setStage] = useState(LG_RECORD_STAGE.RECORD);
    const navigate = useNavigate();
    const config = useConfig();
    const role = useRole();
    const isBSOL = useIsBSOL();
    const deleteAfterDownload = role === REPOSITORY_ROLE.GP_ADMIN && !isBSOL;

    useEffect(() => {
        const onSuccess = (
            files_count: number,
            updated_date: string,
            presign_url: string,
            file_size: number,
        ) => {
            setNumberOfFiles(files_count);
            setLastUpdated(getFormattedDatetime(new Date(updated_date)));
            setLloydGeorgeUrl(presign_url);
            setDownloadStage(DOWNLOAD_STAGE.SUCCEEDED);
            setTotalFileSizeInByte(file_size);
            setDownloadStage(DOWNLOAD_STAGE.SUCCEEDED);
        };

        const onPageLoad = async () => {
            const nhsNumber: string = patientDetails?.nhsNumber ?? '';
            try {
                const { number_of_files, total_file_size_in_byte, last_updated, presign_url } =
                    await getLloydGeorgeRecord({
                        nhsNumber,
                        baseUrl,
                        baseHeaders,
                    });
                if (presign_url?.startsWith('https://')) {
                    onSuccess(number_of_files, last_updated, presign_url, total_file_size_in_byte);
                }
            } catch (e) {
                const error = e as AxiosError;
                const errorResponse = (error.response?.data as ErrorResponse) ?? {};

                if (isMock(error)) {
                    if (!!config.mockLocal.recordUploaded) {
                        onSuccess(1, moment().format(), '/dev/testFile.pdf', 59000);
                    } else {
                        setDownloadStage(DOWNLOAD_STAGE.NO_RECORDS);
                    }
                } else {
                    if (error.response?.status === 504) {
                        setDownloadStage(DOWNLOAD_STAGE.TIMEOUT);
                    } else if (
                        error.response?.status === 404 ||
                        (error.response?.status === 400 && errorResponse?.err_code === 'LGL_400')
                    ) {
                        setDownloadStage(DOWNLOAD_STAGE.NO_RECORDS);
                    } else if (error.response?.status === 403) {
                        navigate(routes.SESSION_EXPIRED);
                    } else if (error.response?.status && error.response?.status >= 500) {
                        navigate(routes.SERVER_ERROR + errorToParams(error));
                    } else if (error.response?.status === 423) {
                        setDownloadStage(DOWNLOAD_STAGE.UPLOADING);
                    } else {
                        setDownloadStage(DOWNLOAD_STAGE.FAILED);
                    }
                }
            }
        };

        if (!mounted.current || downloadStage === DOWNLOAD_STAGE.REFRESH) {
            mounted.current = true;
            setDownloadStage(DOWNLOAD_STAGE.PENDING);
            void onPageLoad();
        }
    }, [
        patientDetails,
        baseUrl,
        baseHeaders,
        setDownloadStage,
        downloadStage,
        setLloydGeorgeUrl,
        setLastUpdated,
        setNumberOfFiles,
        setTotalFileSizeInByte,
        navigate,
        config,
    ]);

    return (
        <>
            <Routes>
                <Route
                    index
                    element={
                        <LloydGeorgeViewRecordStage
                            numberOfFiles={numberOfFiles}
                            totalFileSizeInByte={totalFileSizeInByte}
                            lastUpdated={lastUpdated}
                            lloydGeorgeUrl={lloydGeorgeUrl}
                            downloadStage={downloadStage}
                            setStage={setStage}
                            stage={stage}
                        />
                    }
                />
                <Route
                    path={getLastURLPath(routeChildren.LLOYD_GEORGE_DOWNLOAD_SELECT) + '/*'}
                    element={
                        <LloydGeorgeSelectDownloadStage
                            setStage={setStage}
                            deleteAfterDownload={deleteAfterDownload}
                            setDownloadStage={setDownloadStage}
                        />
                    }
                />
                <Route
                    path={getLastURLPath(routeChildren.LLOYD_GEORGE_DOWNLOAD) + '/*'}
                    element={
                        <LloydGeorgeDownloadStage
                            numberOfFiles={numberOfFiles}
                            deleteAfterDownload={deleteAfterDownload}
                        />
                    }
                />
                <Route
                    path={getLastURLPath(routeChildren.LLOYD_GEORGE_DELETE) + '/*'}
                    element={
                        <DeleteSubmitStage
                            docType={DOCUMENT_TYPE.LLOYD_GEORGE}
                            numberOfFiles={numberOfFiles}
                            setStage={setStage}
                            setDownloadStage={setDownloadStage}
                            recordType="Lloyd George"
                        />
                    }
                />
            </Routes>

            <Outlet />
        </>
    );
}

export default LloydGeorgeRecordPage;

//     switch (stage) {
//         case LG_RECORD_STAGE.RECORD:
//             return (
//                 <LloydGeorgeViewRecordStage
//                     numberOfFiles={numberOfFiles}
//                     totalFileSizeInByte={totalFileSizeInByte}
//                     lastUpdated={lastUpdated}
//                     lloydGeorgeUrl={lloydGeorgeUrl}
//                     downloadStage={downloadStage}
//                     setStage={setStage}
//                     stage={stage}
//                 />
//             );
//         case LG_RECORD_STAGE.REMOVE:
//             return <RemoveRecordStage setStage={setStage} recordType="Lloyd George" />;

//         case LG_RECORD_STAGE.DOWNLOAD_ALL:
//             return isBSOL ? (
//                 <LloydGeorgeSelectDownloadStage
//                     setStage={setStage}
//                     deleteAfterDownload={deleteAfterDownload}
//                     setDownloadStage={setDownloadStage}
//                 />
//             ) : (
//                 <LloydGeorgeDownloadStage
//                     numberOfFiles={numberOfFiles}
//                     setStage={setStage}
//                     deleteAfterDownload={deleteAfterDownload}
//                     setDownloadStage={setDownloadStage}
//                 />
//             );
//         case LG_RECORD_STAGE.DELETE_ALL:
//             return (
//                 <DeleteSubmitStage
//                     docType={DOCUMENT_TYPE.LLOYD_GEORGE}
//                     numberOfFiles={numberOfFiles}
//                     recordType="Lloyd George"
//                     setStage={setStage}
//                     setDownloadStage={setDownloadStage}
// >>>>>>> main