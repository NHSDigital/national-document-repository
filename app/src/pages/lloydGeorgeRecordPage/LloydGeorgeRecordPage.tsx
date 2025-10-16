import React, { useState } from 'react';
import { DOWNLOAD_STAGE } from '../../types/generic/downloadStage';

import LloydGeorgeViewRecordStage from '../../components/blocks/_lloydGeorge/lloydGeorgeViewRecordStage/LloydGeorgeViewRecordStage';
import { LG_RECORD_STAGE } from '../../types/blocks/lloydGeorgeStages';
import useRole from '../../helpers/hooks/useRole';
import { REPOSITORY_ROLE } from '../../types/generic/authRole';
import { routeChildren, routes } from '../../types/generic/routes';
import { Outlet, Route, Routes, useNavigate } from 'react-router-dom';
import { getLastURLPath } from '../../helpers/utils/urlManipulations';
import RemoveRecordStage from '../../components/blocks/_delete/removeRecordStage/RemoveRecordStage';
import LloydGeorgeSelectDownloadStage from '../../components/blocks/_lloydGeorge/lloydGeorgeSelectDownloadStage/LloydGeorgeSelectDownloadStage';
import axios, { AxiosError } from 'axios';
import { ErrorResponse } from '../../types/generic/errorResponse';
import { isMock } from '../../helpers/utils/isLocal';
import useConfig from '../../helpers/hooks/useConfig';
import moment from 'moment';
import { errorToParams } from '../../helpers/utils/errorToParams';
import usePatient from '../../helpers/hooks/usePatient';
import getLloydGeorgeRecord from '../../helpers/requests/getLloydGeorgeRecord';
import useBaseAPIHeaders from '../../helpers/hooks/useBaseAPIHeaders';
import useBaseAPIUrl from '../../helpers/hooks/useBaseAPIUrl';
import { getFormattedDatetime } from '../../helpers/utils/formatDatetime';

const LloydGeorgeRecordPage = (): React.JSX.Element => {
    const [downloadStage, setDownloadStage] = useState(DOWNLOAD_STAGE.INITIAL);
    const [stage, setStage] = useState(LG_RECORD_STAGE.RECORD);
    const role = useRole();
    const config = useConfig();
    const navigate = useNavigate();
    const patientDetails = usePatient();
    const baseUrl = useBaseAPIUrl();
    const baseHeaders = useBaseAPIHeaders();
    const [numberOfFiles, setNumberOfFiles] = useState(0);
    const [lastUpdated, setLastUpdated] = useState('');
    const [pdfObjectUrl, setPdfObjectUrl] = useState('');
    const hasRecordInStorage = downloadStage === DOWNLOAD_STAGE.SUCCEEDED;

    const showMenu = role === REPOSITORY_ROLE.GP_ADMIN && hasRecordInStorage;

    const resetDocState = (): void => {
        setNumberOfFiles(0);
        setLastUpdated('');
        setDownloadStage(DOWNLOAD_STAGE.INITIAL);
    };

    const getPdfObjectUrl = async (cloudFrontUrl: string): Promise<void> => {
        const { data } = await axios.get(cloudFrontUrl, {
            responseType: 'blob',
        });

        const objectUrl = URL.createObjectURL(data);

        setPdfObjectUrl(objectUrl);
        setDownloadStage(DOWNLOAD_STAGE.SUCCEEDED);
    };

    const refreshRecord = async (): Promise<void> => {
        const onSuccess = (filesCount: number, updatedDate: string, presignedUrl: string): void => {
            setNumberOfFiles(filesCount);
            setLastUpdated(getFormattedDatetime(new Date(updatedDate)));
            getPdfObjectUrl(presignedUrl);
        };

        const onError = (e: AxiosError): void => {
            const error = e as AxiosError;
            const errorResponse = (error.response?.data as ErrorResponse) ?? {};

            if (isMock(error)) {
                if (!!config.mockLocal.recordUploaded) {
                    onSuccess(1, moment().format(), '/dev/testFile.pdf');
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
        };

        const nhsNumber: string = patientDetails?.nhsNumber ?? '';
        try {
            const { numberOfFiles, lastUpdated, presignedUrl } = await getLloydGeorgeRecord({
                nhsNumber,
                baseUrl,
                baseHeaders,
            });

            onSuccess(numberOfFiles, lastUpdated, presignedUrl);
        } catch (e) {
            onError(e as AxiosError);
        }
    };

    return (
        <>
            <Routes>
                <Route
                    index
                    element={
                        <LloydGeorgeViewRecordStage
                            downloadStage={downloadStage}
                            setStage={setStage}
                            stage={stage}
                            lastUpdated={lastUpdated}
                            refreshRecord={refreshRecord}
                            pdfObjectUrl={pdfObjectUrl}
                            showMenu={showMenu}
                            resetDocState={resetDocState}
                        />
                    }
                />
                <Route
                    path={getLastURLPath(routeChildren.LLOYD_GEORGE_DOWNLOAD) + '/*'}
                    element={
                        <LloydGeorgeSelectDownloadStage
                            setDownloadStage={setDownloadStage}
                            numberOfFiles={numberOfFiles}
                        />
                    }
                />
                <Route
                    path={getLastURLPath(routeChildren.LLOYD_GEORGE_DELETE) + '/*'}
                    element={
                        <RemoveRecordStage
                            setDownloadStage={setDownloadStage}
                            numberOfFiles={numberOfFiles}
                            recordType="Lloyd George"
                            resetDocState={resetDocState}
                        />
                    }
                />
            </Routes>

            <Outlet />
        </>
    );
};

export default LloydGeorgeRecordPage;
