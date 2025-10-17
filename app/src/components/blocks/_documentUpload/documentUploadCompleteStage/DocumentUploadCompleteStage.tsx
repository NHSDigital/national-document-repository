import { Button } from 'nhsuk-react-components';
import { routes } from '../../../../types/generic/routes';
import { Link, useNavigate } from 'react-router-dom';
import useTitle from '../../../../helpers/hooks/useTitle';
import usePatient from '../../../../helpers/hooks/usePatient';
import { formatNhsNumber } from '../../../../helpers/utils/formatNhsNumber';
import { getFormattedDateFromString } from '../../../../helpers/utils/formatDate';
import { getFormattedPatientFullName } from '../../../../helpers/utils/formatPatientFullName';
import {
    DOCUMENT_UPLOAD_STATE,
    UploadDocument,
} from '../../../../types/pages/UploadDocumentsPage/types';
import { useEffect } from 'react';
import { allDocsHaveState } from '../../../../helpers/utils/uploadDocumentHelpers';
import { getJourney } from '../../../../helpers/utils/urlManipulations';

type Props = {
    documents: UploadDocument[];
};

const DocumentUploadCompleteStage = ({ documents }: Props): React.JSX.Element => {
    const navigate = useNavigate();
    const patientDetails = usePatient();
    const nhsNumber: string = patientDetails?.nhsNumber ?? '';
    const formattedNhsNumber = formatNhsNumber(nhsNumber);
    const dob: string = getFormattedDateFromString(patientDetails?.birthDate);
    const patientName = getFormattedPatientFullName(patientDetails);
    const journey = getJourney();

    useTitle({ pageTitle: 'Record upload complete' });

    useEffect(() => {
        if (!allDocsHaveState(documents, DOCUMENT_UPLOAD_STATE.SUCCEEDED)) {
            navigate(routes.HOME);
        }
    }, [navigate]);

    if (!allDocsHaveState(documents, DOCUMENT_UPLOAD_STATE.SUCCEEDED)) {
        return <></>;
    }

    return (
        <div className="lloydgeorge_upload-complete" data-testid="upload-complete-page">
            <div className="nhsuk-panel" data-testid="upload-complete-card">
                <h1 className="nhsuk-panel__title">Upload complete</h1>
                <div className="nhsuk-panel__body">
                    {journey === 'update' && (
                        <p>
                            You have successfully added additional files to the digital Lloyd George
                            record for:
                        </p>
                    )}
                    {journey === 'new' && (
                        <p>You have successfully uploaded a digital Lloyd George record for:</p>
                    )}
                </div>
                <br />
                <div className="nhsuk-panel__body">
                    <strong data-testid="patient-name">Patient name: {patientName}</strong>
                    <br />
                    <span data-testid="nhs-number">NHS Number: {formattedNhsNumber}</span>
                    <br />
                    <span data-testid="dob">Date of birth: {dob}</span>
                </div>
            </div>

            <h2>What happens next</h2>

            {journey === 'update' && (
                <>
                    <p>
                        You can now view the updated Lloyd George record for this patient in this
                        service by{' '}
                        <Link
                            to=""
                            onClick={(e): void => {
                                e.preventDefault();
                                navigate(routes.SEARCH_PATIENT, { replace: true });
                            }}
                            data-testid="search-patient-link"
                        >
                            searching using their NHS number
                        </Link>
                        {'.'}
                    </p>
                    <p>
                        If you think you've made a mistake, contact the Patient Record Management
                        team at england.prmteam@nhs.net.
                    </p>
                    <p>
                        You can add a note to the patient's electronic health record to say their
                        Lloyd George record is stored in this service. Use SNOMED code 'Lloyd George
                        record folder' 16521000000101.
                    </p>
                </>
            )}

            {journey === 'new' && (
                <p>
                    You can now view this patient's record within this service by{' '}
                    <Link
                        to=""
                        onClick={(e): void => {
                            e.preventDefault();
                            navigate(routes.SEARCH_PATIENT, { replace: true });
                        }}
                        data-testid="search-patient-link"
                    >
                        searching using their NHS number
                    </Link>
                    {'.'}
                </p>
            )}

            <p>
                If you think you've made a mistake, contact the Patient Record Management team at{' '}
                <a href="mailto:england.prmteam@nhs.net">england.prmteam@nhs.net</a>.
            </p>

            <p>
                You can add a note to the patient's electronic health record to say their Lloyd
                George record is stored in this service. Use SNOMED code 'Lloyd George record
                folder' 16521000000101.
            </p>

            <p>
                For information on destroying your paper records and removing the digital files from
                your system, read the article{' '}
                <Link
                    to="https://future.nhs.uk/DigitalPC/view?objectId=185217477"
                    data-testid="digitisation-link"
                >
                    Digitisation of Lloyd George records
                </Link>
                {'.'}
            </p>

            <Button
                data-testid="home-btn"
                type="button"
                onClick={(): void => {
                    navigate(routes.HOME, { replace: true });
                }}
            >
                Go to home
            </Button>
        </div>
    );
};

export default DocumentUploadCompleteStage;
