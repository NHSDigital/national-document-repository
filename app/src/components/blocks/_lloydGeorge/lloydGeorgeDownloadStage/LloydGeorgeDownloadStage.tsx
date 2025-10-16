import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Card } from 'nhsuk-react-components';
import useBaseAPIHeaders from '../../../../helpers/hooks/useBaseAPIHeaders';
import getPresignedUrlForZip from '../../../../helpers/requests/getPresignedUrlForZip';
import { DOCUMENT_TYPE } from '../../../../types/pages/UploadDocumentsPage/types';
import useBaseAPIUrl from '../../../../helpers/hooks/useBaseAPIUrl';
import usePatient from '../../../../helpers/hooks/usePatient';
import { routeChildren, routes } from '../../../../types/generic/routes';
import { useNavigate, Link } from 'react-router-dom';
import { errorToParams } from '../../../../helpers/utils/errorToParams';
import { AxiosError } from 'axios/index';
import { isMock } from '../../../../helpers/utils/isLocal';
import useConfig from '../../../../helpers/hooks/useConfig';
import useTitle from '../../../../helpers/hooks/useTitle';

const FakeProgress = require('fake-progress');

export type Props = {
    selectedDocuments?: Array<string>;
    numberOfFiles: number;
};

type DownloadLinkAttributes = {
    url: string;
    filename: string;
};

const LloydGeorgeDownloadStage = ({
    selectedDocuments,
    numberOfFiles,
}: Props): React.JSX.Element => {
    const timeToComplete = 600;
    const [progress, setProgress] = useState(0);
    const baseUrl = useBaseAPIUrl();
    const baseHeaders = useBaseAPIHeaders();
    const [linkAttributes, setLinkAttributes] = useState<DownloadLinkAttributes>({
        url: '',
        filename: '',
    });
    const linkRef = useRef<HTMLAnchorElement | null>(null);
    const pageDownloadCountId = 'download-file-header-' + numberOfFiles + '-files';
    const mounted = useRef(false);
    const navigate = useNavigate();
    const { mockLocal } = useConfig();
    const patientDetails = usePatient();
    const nhsNumber = patientDetails?.nhsNumber ?? '';
    const [delayTimer, setDelayTimer] = useState<NodeJS.Timeout>();

    const progressTimer = useMemo(() => {
        return new FakeProgress({
            timeConstant: timeToComplete,
            autoStart: true,
        });
    }, []);

    const intervalTimer = window.setInterval(() => {
        setProgress(parseInt((progressTimer.progress * 100).toFixed(1)));
    }, 100);

    const handlePageExit = useCallback(() => {
        window.clearInterval(intervalTimer);
        if (delayTimer) {
            window.clearTimeout(delayTimer);
        }
    }, [delayTimer, intervalTimer]);

    useEffect(() => {
        if (linkRef.current && linkAttributes.url) {
            linkRef?.current?.click();
            setTimeout(() => {
                navigate(routeChildren.LLOYD_GEORGE_DOWNLOAD_COMPLETE);
            }, 600);
        }
    }, [linkAttributes, navigate]);

    useEffect(() => {
        const onFail = (error: AxiosError): void => {
            if (isMock(error) && !!mockLocal.recordUploaded) {
                if (typeof window !== 'undefined') {
                    const { protocol, host } = window.location;
                    setLinkAttributes({
                        url: protocol + '//' + host + '/dev/testFile.pdf',
                        filename: 'testFile.pdf',
                    });
                }
            } else if (error.response?.status === 403) {
                navigate(routes.SESSION_EXPIRED);
            } else {
                navigate(routes.SERVER_ERROR + errorToParams(error));
            }
        };
        const onPageLoad = async (): Promise<void> => {
            progressTimer.stop();
            window.clearInterval(intervalTimer);
            if (!nhsNumber) {
                navigate(routes.SEARCH_PATIENT);
                return;
            }
            try {
                const preSignedUrl = await getPresignedUrlForZip({
                    baseUrl,
                    baseHeaders,
                    nhsNumber,
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                    docReferences: selectedDocuments,
                });

                const filename = `patient-record-${nhsNumber}`;
                setLinkAttributes({ url: preSignedUrl, filename: filename });
            } catch (e) {
                const error = e as AxiosError;
                onFail(error);
            }
        };

        if (!mounted.current) {
            mounted.current = true;
            const min = timeToComplete - 100;
            const max = timeToComplete + 200;
            const delay = Math.floor(Math.random() * (max - min + 1) + min);
            const delayTimer = setTimeout(onPageLoad, timeToComplete + delay);
            setDelayTimer(delayTimer);
        }
    }, [
        baseHeaders,
        baseUrl,
        intervalTimer,
        nhsNumber,
        progressTimer,
        navigate,
        mockLocal,
        selectedDocuments,
    ]);

    const pageHeader = 'Downloading documents';
    useTitle({ pageTitle: pageHeader });

    return (
        <div className="lloydgeorge_downloadall-stage" data-testid="lloydgeorge_downloadall-stage">
            <div className="lloydgeorge_downloadall-stage_header">
                <h1 data-testid="lloyd-george-download-header">{pageHeader}</h1>
                <h2>{patientDetails?.givenName + ' ' + patientDetails?.familyName}</h2>
                <h3 className="nhsuk-heading-s">NHS number: {patientDetails?.nhsNumber}</h3>
                <h4 data-testid={pageDownloadCountId}>
                    Preparing download for {numberOfFiles} files
                </h4>
            </div>

            <Card className="lloydgeorge_downloadall-stage_details">
                <Card.Content>
                    <strong>
                        <p>Compressing record into a zip file</p>
                    </strong>

                    <div className="lloydgeorge_downloadall-stage_details-content">
                        <div>
                            <span>{`${linkAttributes.url ? 100 : progress}%`} downloaded...</span>
                            <a
                                hidden
                                id="download-link"
                                data-testid={linkAttributes.url}
                                ref={linkRef}
                                href={linkAttributes.url}
                                download
                            >
                                Download Lloyd George Documents URL
                            </a>
                        </div>
                        <div>
                            <Link
                                to="#"
                                data-testid="cancel-download-link"
                                onClick={(e): void => {
                                    e.preventDefault();
                                    handlePageExit();
                                    navigate(routes.LLOYD_GEORGE);
                                }}
                            >
                                Cancel and return to patient record
                            </Link>
                        </div>
                    </div>
                </Card.Content>
            </Card>
        </div>
    );
};

export default LloydGeorgeDownloadStage;
