import React, { Dispatch, SetStateAction, useState } from 'react';
import { BackLink, Card, Details } from 'nhsuk-react-components';
import { getFormattedDate } from '../../../helpers/utils/formatDate';
import { DOWNLOAD_STAGE } from '../../../types/generic/downloadStage';
import PdfViewer from '../../generic/pdfViewer/PdfViewer';
import LloydGeorgeRecordDetails from '../lloydGeorgeRecordDetails/LloydGeorgeRecordDetails';
import { formatNhsNumber } from '../../../helpers/utils/formatNhsNumber';
import { LG_RECORD_STAGE } from '../../../types/blocks/lloydGeorgeStages';
import usePatient from '../../../helpers/hooks/usePatient';

export type Props = {
    downloadStage: DOWNLOAD_STAGE;
    lloydGeorgeUrl: string;
    lastUpdated: string;
    numberOfFiles: number;
    totalFileSizeInByte: number;
    setStage: Dispatch<SetStateAction<LG_RECORD_STAGE>>;
    stage: LG_RECORD_STAGE;
};

function LloydGeorgeRecordStage({
    downloadStage,
    lloydGeorgeUrl,
    lastUpdated,
    numberOfFiles,
    totalFileSizeInByte,
    setStage,
    stage,
}: Props) {
    const [fullScreen, setFullScreen] = useState(false);
    const patientDetails = usePatient();
    const dob: String = patientDetails?.birthDate
        ? getFormattedDate(new Date(patientDetails.birthDate))
        : '';

    const nhsNumber: string = patientDetails?.nhsNumber || '';
    const formattedNhsNumber = formatNhsNumber(nhsNumber);

    const PdfCardDescription = () => {
        if (downloadStage === DOWNLOAD_STAGE.SUCCEEDED) {
            const detailsProps = {
                lastUpdated,
                numberOfFiles,
                totalFileSizeInByte,
                setStage,
            };

            return <LloydGeorgeRecordDetails {...detailsProps} setStage={setStage} />;
        } else if (downloadStage === DOWNLOAD_STAGE.FAILED) {
            return <span>No documents are available</span>;
        } else {
            return <span> Loading...</span>;
        }
    };

    return (
        <div className="lloydgeorge_record-stage">
            {fullScreen && (
                <BackLink
                    data-testid="back-link"
                    href="#"
                    onClick={() => {
                        setFullScreen(false);
                    }}
                >
                    Go back
                </BackLink>
            )}
            <div id="patient-info" className="lloydgeorge_record-stage_patient-info">
                <p data-testid="patient-name">
                    {`${patientDetails?.givenName} ${patientDetails?.familyName}`}
                </p>
                <p data-testid="patient-nhs-number">NHS number: {formattedNhsNumber}</p>
                <p data-testid="patient-dob">Date of birth: {dob}</p>
            </div>
            {!fullScreen ? (
                <>
                    <Card className="lloydgeorge_record-stage_header">
                        <Card.Content
                            data-testid="pdf-card"
                            className="lloydgeorge_record-stage_header-content"
                        >
                            <Card.Heading className="lloydgeorge_record-stage_header-content-label">
                                Lloyd George record
                            </Card.Heading>
                            <PdfCardDescription />
                        </Card.Content>
                    </Card>
                    {downloadStage === DOWNLOAD_STAGE.SUCCEEDED && (
                        <>
                            <Details expander open className="lloydgeorge_record-stage_expander">
                                <Details.Summary
                                    style={{ display: 'inline-block' }}
                                    data-testid="view-record-bin"
                                >
                                    View record
                                </Details.Summary>
                                <button
                                    className="lloydgeorge_record-stage_expander-button link-button"
                                    data-testid="full-screen-btn"
                                    onClick={() => {
                                        setFullScreen(true);
                                    }}
                                >
                                    View in full screen
                                </button>
                                <PdfViewer fileUrl={lloydGeorgeUrl} />
                            </Details>
                        </>
                    )}
                </>
            ) : (
                <PdfViewer fileUrl={lloydGeorgeUrl} />
            )}
        </div>
    );
}

export default LloydGeorgeRecordStage;
