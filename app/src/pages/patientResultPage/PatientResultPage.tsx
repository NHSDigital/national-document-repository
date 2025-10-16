import { useState } from 'react';
import { Button, WarningCallout } from 'nhsuk-react-components';
import { useNavigate } from 'react-router-dom';
import { routeChildren, routes } from '../../types/generic/routes';
import BackButton from '../../components/generic/backButton/BackButton';
import { useForm } from 'react-hook-form';
import ErrorBox from '../../components/layout/errorBox/ErrorBox';
import { REPOSITORY_ROLE } from '../../types/generic/authRole';
import useRole from '../../helpers/hooks/useRole';
import usePatient from '../../helpers/hooks/usePatient';
import useTitle from '../../helpers/hooks/useTitle';
import PatientSummary from '../../components/generic/patientSummary/PatientSummary';

const PatientResultPage = (): React.JSX.Element => {
    const role = useRole();
    const patientDetails = usePatient();
    const userIsPCSE = role === REPOSITORY_ROLE.PCSE;
    const navigate = useNavigate();
    const [inputError, setInputError] = useState('');
    const { handleSubmit } = useForm();

    const submit = (): void => {
        if (userIsPCSE) {
            // Make PDS and Dynamo document store search request to download documents from patient
            navigate(routes.ARF_OVERVIEW);
        } else {
            // Make PDS patient search request to upload documents to patient
            if (typeof patientDetails?.active === 'undefined') {
                setInputError('We cannot determine the active state of this patient');
                return;
            }

            if (patientDetails?.deceased) {
                navigate(routeChildren.PATIENT_ACCESS_AUDIT_DECEASED);
                return;
            }

            if (patientDetails?.active) {
                navigate(routes.LLOYD_GEORGE);
                return;
            }

            navigate(routes.SEARCH_PATIENT);
        }
    };
    const showDeceasedWarning = patientDetails?.deceased && !userIsPCSE;
    const showWarning =
        patientDetails?.superseded || patientDetails?.restricted || showDeceasedWarning;
    const pageHeader = 'Patient details';
    useTitle({ pageTitle: pageHeader });

    return (
        <div className="patient-results-paragraph">
            <BackButton toLocation={routes.SEARCH_PATIENT} />
            {inputError && (
                <ErrorBox
                    messageTitle={'There is a problem'}
                    messageLinkBody={inputError}
                    errorInputLink={'#patient-status'}
                    errorBoxSummaryId={'error-box-summary'}
                />
            )}
            <h1>{pageHeader}</h1>

            {showWarning && (
                <WarningCallout>
                    <WarningCallout.Label headingLevel="h2">
                        {showDeceasedWarning
                            ? 'This record is for a deceased patient'
                            : 'Information'}
                    </WarningCallout.Label>
                    {patientDetails.superseded && (
                        <p>The NHS number for this patient has changed.</p>
                    )}
                    {patientDetails.restricted && (
                        <p>
                            Certain details about this patient cannot be displayed without the
                            necessary access.
                        </p>
                    )}
                    {showDeceasedWarning && (
                        <p>
                            Access to the records of deceased patients is regulated under the Access
                            to Health Records Act. You will need to give a reason why you need to
                            access this record. For more information, read the article{' '}
                            <a
                                href="https://transform.england.nhs.uk/information-governance/guidance/access-to-the-health-and-care-records-of-deceased-people/"
                                target="_blank"
                                rel="noreferrer"
                                aria-label="Access to the health and care records of deceased people - this link will open in a new tab"
                            >
                                Access to the health and care records of deceased people
                            </a>
                            .
                        </p>
                    )}
                </WarningCallout>
            )}

            <PatientSummary showDeceasedTag={userIsPCSE} />

            <form onSubmit={handleSubmit(submit)} className="patient-results-form">
                <p id="gp-message">
                    This page displays the current data recorded in the Personal Demographics
                    Service for this patient.
                </p>
                <Button type="submit" id="verify-submit" className="nhsuk-u-margin-top-6">
                    Confirm patient details and continue
                </Button>
            </form>
        </div>
    );
};

export default PatientResultPage;
