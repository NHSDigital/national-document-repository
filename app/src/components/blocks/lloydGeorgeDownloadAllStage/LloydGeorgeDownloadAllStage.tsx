import React, {
    Dispatch,
    SetStateAction,
    useCallback,
    useEffect,
    useMemo,
    useRef,
    useState,
} from 'react';
import { Card } from 'nhsuk-react-components';
import { Link } from 'react-router-dom';
import { PatientDetails } from '../../../types/generic/patientDetails';
import useBaseAPIHeaders from '../../../helpers/hooks/useBaseAPIHeaders';
import getPresignedUrlForZip from '../../../helpers/requests/getPresignedUrlForZip';
import { DOCUMENT_TYPE } from '../../../types/pages/UploadDocumentsPage/types';
import LgDownloadComplete from '../lloydGeorgeDownloadComplete/LloydGeorgeDownloadComplete';
import { LG_RECORD_STAGE } from '../../../types/blocks/lloydGeorgeStages';
import useBaseAPIUrl from '../../../helpers/hooks/useBaseAPIUrl';
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

function LloydGeorgeDownloadAllStage({ numberOfFiles, setStage, patientDetails }: Props) {
    const timeToComplete = 600;
    const [progress, setProgress] = useState(0);
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
                setInProgress(false);
            }, 600);
        }
    }, [linkAttributes]);

    useEffect(() => {
        const onPageLoad = async () => {
            progressTimer.stop();
            window.clearInterval(intervalTimer);
            try {
                const preSignedUrl = await getPresignedUrlForZip({
                    baseUrl,
                    baseHeaders,
                    nhsNumber,
                    docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                });

                const filename = `patient-record-${nhsNumber}`;
                setLinkAttributes({ url: preSignedUrl, filename: filename });
            } catch (e) {}
        };

        if (!mounted.current) {
            mounted.current = true;
            const min = timeToComplete - 100;
            const max = timeToComplete + 200;
            const delay = Math.floor(Math.random() * (max - min + 1) + min);
            const delayTimer = setTimeout(onPageLoad, timeToComplete + delay);
            setDelayTimer(delayTimer);
        }
    }, [baseHeaders, baseUrl, intervalTimer, nhsNumber, progressTimer]);

    return inProgress ? (
        <div className="lloydgeorge_downloadall-stage">
            <div className="lloydgeorge_downloadall-stage_header">
                <h1>Downloading documents</h1>
                <h2>{patientDetails.givenName + ' ' + patientDetails.familyName}</h2>
                <h4>NHS number: {patientDetails.nhsNumber}</h4>
                <div className="nhsuk-heading-xl" />
                <h4>Preparing download for {numberOfFiles} files</h4>
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
                                onClick={(e) => {
                                    e.preventDefault();
                                    handlePageExit();
                                    setStage(LG_RECORD_STAGE.RECORD);
                                }}
                            >
                                Cancel
                            </Link>
                        </div>
                    </div>
                </Card.Content>
            </Card>
        </div>
    ) : (
        <LgDownloadComplete patientDetails={patientDetails} setStage={setStage} />
    );
}

export default LloydGeorgeDownloadAllStage;
