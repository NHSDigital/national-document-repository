import { Dispatch, SetStateAction, useEffect, useRef } from 'react';
import { Button, ChevronLeftIcon } from 'nhsuk-react-components';
import { DOWNLOAD_STAGE } from '../../../../types/generic/downloadStage';
import LloydGeorgeRecordDetails from '../lloydGeorgeRecordDetails/LloydGeorgeRecordDetails';
import { LG_RECORD_STAGE } from '../../../../types/blocks/lloydGeorgeStages';
import LloydGeorgeRecordError from '../lloydGeorgeRecordError/LloydGeorgeRecordError';
import useRole from '../../../../helpers/hooks/useRole';
import BackButton from '../../../generic/backButton/BackButton';
import { getUserRecordActionLinks } from '../../../../types/blocks/lloydGeorgeActions';
import RecordCard from '../../../generic/recordCard/RecordCard';
import useTitle from '../../../../helpers/hooks/useTitle';
import { routes, routeChildren } from '../../../../types/generic/routes';
import ProgressBar from '../../../generic/progressBar/ProgressBar';
import usePatient from '../../../../helpers/hooks/usePatient';
import { useSessionContext } from '../../../../providers/sessionProvider/SessionProvider';
import RecordMenuCard from '../../../generic/recordMenuCard/RecordMenuCard';
import { REPOSITORY_ROLE } from '../../../../types/generic/authRole';
import PatientSummary, { PatientInfo } from '../../../generic/patientSummary/PatientSummary';
import { Link } from 'react-router-dom';
import useConfig from '../../../../helpers/hooks/useConfig';

export type Props = {
    downloadStage: DOWNLOAD_STAGE;
    lastUpdated: string;
    setStage: Dispatch<SetStateAction<LG_RECORD_STAGE>>;
    stage: LG_RECORD_STAGE;
    refreshRecord: () => void;
    pdfObjectUrl: string;
    showMenu: boolean;
    resetDocState: () => void;
};

const LloydGeorgeViewRecordStage = ({
    downloadStage,
    lastUpdated,
    setStage,
    refreshRecord,
    pdfObjectUrl,
    showMenu,
    resetDocState,
}: Props): React.JSX.Element => {
    const patientDetails = usePatient();
    const [session, setUserSession] = useSessionContext();
    const config = useConfig();

    const role = useRole();

    const hasRecordInStorage = downloadStage === DOWNLOAD_STAGE.SUCCEEDED;

    const setFullScreen = (isFullscreen: boolean): void => {
        if (isFullscreen) {
            if (document.fullscreenEnabled) {
                document.documentElement.requestFullscreen?.();
            }
        } else if (document.fullscreenElement !== null) {
            document.exitFullscreen?.();
        }

        setUserSession({ ...session, isFullscreen });
    };

    let recordLinksToShow = getUserRecordActionLinks({ role, hasRecordInStorage }).map((link) => {
        link.onClick = (): void => {
            setFullScreen(false);
        };

        return link;
    });

    const recordDetailsProps: RecordDetailsProps = {
        downloadStage,
        lastUpdated,
    };

    const pageHeader = 'Available records';
    useTitle({ pageTitle: pageHeader });

    const mounted = useRef(false);

    useEffect(() => {
        const onPageLoad = async (): Promise<void> => {
            resetDocState();
            refreshRecord();
        };
        if (!mounted.current) {
            onPageLoad();
            mounted.current = true;
        }
    }, [refreshRecord, resetDocState]);

    const menuClass = showMenu ? '--menu' : '--upload';

    return (
        <div className="lloydgeorge_record-stage">
            {session.isFullscreen && (
                <div className="header">
                    <div className="header-items">
                        <Button
                            reverse
                            data-testid="back-link"
                            className="exit-fullscreen-button"
                            onClick={(): void => {
                                setFullScreen(false);
                            }}
                        >
                            <ChevronLeftIcon className="mr-2" />
                            Exit full screen
                        </Button>
                        <h1 className="title">Lloyd George record</h1>
                        <a
                            className="sign-out-link"
                            href={routes.LOGOUT}
                            onClick={(): void => {
                                setFullScreen(false);
                            }}
                        >
                            Sign out
                        </a>
                    </div>
                </div>
            )}

            <div className="main-content">
                <div className="top-info">
                    {!session.isFullscreen && (
                        <>
                            <BackButton
                                dataTestid="go-back-button"
                                toLocation={
                                    patientDetails?.deceased && role !== REPOSITORY_ROLE.PCSE
                                        ? routeChildren.PATIENT_ACCESS_AUDIT_DECEASED
                                        : routes.VERIFY_PATIENT
                                }
                                backLinkText="Go back"
                            />
                            <h1>{pageHeader}</h1>
                        </>
                    )}

                    <PatientSummary showDeceasedTag>
                        <PatientSummary.Child item={PatientInfo.FULL_NAME} />
                        <PatientSummary.Child item={PatientInfo.NHS_NUMBER} />
                        <PatientSummary.Child item={PatientInfo.BIRTH_DATE} />
                    </PatientSummary>

                    {session.isFullscreen && (
                        <RecordMenuCard
                            recordLinks={recordLinksToShow}
                            setStage={setStage}
                            showMenu={showMenu}
                        />
                    )}

                    {hasRecordInStorage && config.featureFlags.uploadLloydGeorgeWorkflowEnabled && (
                        <>
                            <h2>Uploading files</h2>
                            <p>
                                You cannot currently add more files to this patient's record. This
                                feature is coming soon. If you have more files for this patient,
                                store them following the{' '}
                                <Link to="https://transform.england.nhs.uk/information-governance/guidance/records-management-code/records-management-code-of-practice/">
                                    Records Management Code of Practice
                                </Link>
                                {'.'}
                            </p>
                        </>
                    )}
                </div>

                {!session.isFullscreen ? (
                    <div className="lloydgeorge_record-stage_flex">
                        <div
                            className={`lloydgeorge_record-stage_flex-row lloydgeorge_record-stage_flex-row${menuClass}`}
                        >
                            <RecordCard
                                heading="Lloyd George record"
                                fullScreenHandler={setFullScreen}
                                detailsElement={<RecordDetails {...recordDetailsProps} />}
                                isFullScreen={session.isFullscreen!}
                                pdfObjectUrl={hasRecordInStorage ? pdfObjectUrl : ''}
                                recordLinks={recordLinksToShow}
                                setStage={setStage}
                                showMenu={showMenu}
                            />
                        </div>
                    </div>
                ) : (
                    <RecordCard
                        heading="Lloyd George record"
                        fullScreenHandler={setFullScreen}
                        detailsElement={<RecordDetails {...recordDetailsProps} />}
                        isFullScreen={session.isFullscreen!}
                        pdfObjectUrl={hasRecordInStorage ? pdfObjectUrl : ''}
                    />
                )}
            </div>
        </div>
    );
};

type RecordDetailsProps = Pick<Props, 'downloadStage' | 'lastUpdated'>;

const RecordDetails = ({ downloadStage, lastUpdated }: RecordDetailsProps): React.JSX.Element => {
    const [{ isFullscreen }] = useSessionContext();

    switch (downloadStage) {
        case DOWNLOAD_STAGE.INITIAL:
        case DOWNLOAD_STAGE.PENDING:
        case DOWNLOAD_STAGE.REFRESH:
            return <ProgressBar status="Loading..." className="loading-bar" />;

        case DOWNLOAD_STAGE.SUCCEEDED: {
            if (isFullscreen) {
                return <></>;
            }

            const detailsProps = {
                lastUpdated,
            };
            return <LloydGeorgeRecordDetails {...detailsProps} />;
        }

        default:
            return <LloydGeorgeRecordError downloadStage={downloadStage} />;
    }
};

export default LloydGeorgeViewRecordStage;
