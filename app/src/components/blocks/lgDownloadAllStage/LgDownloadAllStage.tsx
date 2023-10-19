import React, { Dispatch, SetStateAction, useEffect, useMemo, useRef, useState } from 'react';
import { Card } from 'nhsuk-react-components';
import { Link } from 'react-router-dom';
import { LG_RECORD_STAGE } from '../../../pages/lloydGeorgeRecordPage/LloydGeorgeRecordPage';
import { PatientDetails } from '../../../types/generic/patientDetails';
import { useBaseAPIUrl } from '../../../providers/configProvider/ConfigProvider';
import useBaseAPIHeaders from '../../../helpers/hooks/useBaseAPIHeaders';
import getPresignedUrlForZip from '../../../helpers/requests/getPresignedUrlForZip';
import { DOCUMENT_TYPE } from '../../../types/pages/UploadDocumentsPage/types';
import LgDownloadComplete from '../lgDownloadComplete/LgDownloadComplete';
const FakeProgress = require('fake-progress');

export type Props = {
    numberOfFiles: number;
    setStage: Dispatch<SetStateAction<LG_RECORD_STAGE>>;
    patientDetails: PatientDetails;
};

type DownloadLinkAttributes = {
    url: string;
    filename: string;
};

function LgDownloadAllStage({ numberOfFiles, setStage, patientDetails }: Props) {
    const timeToComplete = 600;
    const [progress, setProgress] = useState(0);
    const progressTimer = useMemo(() => {
        return new FakeProgress({
            timeConstant: timeToComplete,
            autoStart: true,
        });
    }, []);
    const baseUrl = useBaseAPIUrl();
    const baseHeaders = useBaseAPIHeaders();
    const [linkAttributes, setLinkAttributes] = useState<DownloadLinkAttributes>({
        url: '',
        filename: '',
    });
    const [inProgress, setInProgress] = useState(true);
    const linkRef = useRef<HTMLAnchorElement | null>(null);
    const mounted = useRef(false);

    const { nhsNumber } = patientDetails;

    const intervalTimer = window.setInterval(() => {
        setProgress(parseInt((progressTimer.progress * 100).toFixed(1)));
    }, 100);

    useEffect(() => {
        if (linkRef.current && linkAttributes.url) {
            linkRef?.current?.click();
            setTimeout(() => {
                setInProgress(false);
            }, 600);
        }
    }, [linkAttributes]);

    useEffect(() => {
        const onPageLoad = async () => {
            progressTimer.stop();
            try {
                const preSignedUrl = await getPresignedUrlForZip({
                    baseUrl,
                    baseHeaders,
                    nhsNumber,
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                });

                const filename = `lloyd_george-patient-record-${nhsNumber}`;

                setLinkAttributes({ url: preSignedUrl, filename: filename });
                window.clearInterval(intervalTimer);
            } catch (e) {}
        };

        if (!mounted.current) {
            mounted.current = true;
            const min = timeToComplete - 100;
            const max = timeToComplete + 200;
            const delay = Math.floor(Math.random() * (max - min + 1) + min);
            setTimeout(onPageLoad, timeToComplete + delay);
        }
    }, [baseHeaders, baseUrl, intervalTimer, nhsNumber, progressTimer, timeToComplete]);

    return inProgress ? (
        <>
            <h1>Downloading documents</h1>
            <h2 style={{ margin: 0 }}>
                {patientDetails.givenName + ' ' + patientDetails.familyName}
            </h2>
            <h4 style={{ fontWeight: 'unset', fontStyle: 'unset' }}>
                NHS number: {patientDetails.nhsNumber}
            </h4>
            <div className="nhsuk-heading-xl" />
            <h4 style={{ fontWeight: 'unset', fontStyle: 'unset' }}>
                Preparing download for {numberOfFiles} files
            </h4>

            <Card>
                <Card.Content>
                    <strong>
                        <p>Compressing record into a zip file</p>
                    </strong>

                    <div
                        style={{
                            display: 'flex',
                            flexFlow: 'row nowrap',
                            justifyContent: 'space-between',
                        }}
                    >
                        <div>
                            <span>{`${linkAttributes.url ? 100 : progress}%`} downloaded...</span>
                            <a
                                hidden
                                id="download-link"
                                data-testid={linkAttributes.url}
                                ref={linkRef}
                                href={linkAttributes.url}
                                download={linkAttributes.filename}
                            >
                                Download Lloyd George Documents URL
                            </a>
                        </div>
                        <div>
                            <Link
                                to="#"
                                onClick={(e) => {
                                    e.preventDefault();
                                    const w = global.window;
                                    if (
                                        typeof w !== 'undefined' &&
                                        w.confirm(
                                            'Are you sure you would like to cancel the download?',
                                        )
                                    ) {
                                        setStage(LG_RECORD_STAGE.RECORD);
                                    }
                                }}
                            >
                                Cancel
                            </Link>
                        </div>
                    </div>
                </Card.Content>
            </Card>
        </>
    ) : (
        <LgDownloadComplete patientDetails={patientDetails} setStage={setStage} />
    );
}

export default LgDownloadAllStage;
