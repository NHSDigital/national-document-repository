import React from 'react';
import { Button } from 'nhsuk-react-components';
import { useNavigate } from 'react-router-dom';
import { UploadDocument } from '../../../../types/pages/UploadDocumentsPage/types';
import UploadSummary from '../uploadSummary/UploadSummary';
interface Props {
    documents: Array<UploadDocument>;
}

const CompleteStage = ({ documents }: Props): React.JSX.Element => {
    const navigate = useNavigate();

    return (
        <>
            <UploadSummary documents={documents} />
            <p className="complete-stage-paragraph">
                If you want to upload another patient&apos;s health record
            </p>
            <Button
                id="start-again-button"
                onClick={() => {
                    navigate('/');
                }}
            >
                Start Again
            </Button>
        </>
    );
};

export default CompleteStage;
