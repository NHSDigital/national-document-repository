import { JSX, useState } from 'react';
import { routes } from '../../types/generic/routes';
import { FieldValues, useForm } from 'react-hook-form';
import ErrorBox from '../../components/layout/errorBox/ErrorBox';
import { BackLink, Button, TextInput } from 'nhsuk-react-components';
import SpinnerButton from '../../components/generic/spinnerButton/SpinnerButton';
import { InputRef } from '../../types/generic/inputRef';
import { useNavigate } from 'react-router-dom';
import ServiceError from '../../components/layout/serviceErrorBox/ServiceErrorBox';
import { usePatientDetailsContext } from '../../providers/patientProvider/PatientProvider';
import getPatientDetails from '../../helpers/requests/getPatientDetails';
import { SEARCH_STATES } from '../../types/pages/patientSearchPage';
import { AxiosError } from 'axios';
import { PatientDetails } from '../../types/generic/patientDetails';
import { buildPatientDetails } from '../../helpers/test/testBuilders';
import { isMock } from '../../helpers/utils/isLocal';
import useBaseAPIHeaders from '../../helpers/hooks/useBaseAPIHeaders';
import useBaseAPIUrl from '../../helpers/hooks/useBaseAPIUrl';
import { errorToParams } from '../../helpers/utils/errorToParams';
import useTitle from '../../helpers/hooks/useTitle';
import useConfig from '../../helpers/hooks/useConfig';
import { ErrorResponse } from '../../types/generic/errorResponse';
import errorCodes from '../../helpers/utils/errorCodes';
import useRole from '../../helpers/hooks/useRole';
import { REPOSITORY_ROLE } from '../../types/generic/authRole';

export const incorrectFormatMessage = "Enter patient's 10 digit NHS number";

const PatientSearchPage = (): JSX.Element => {
    const [, setPatientDetails] = usePatientDetailsContext();
    const [submissionState, setSubmissionState] = useState<SEARCH_STATES>(SEARCH_STATES.IDLE);
    const [statusCode, setStatusCode] = useState<null | number>(null);
    const [inputError, setInputError] = useState<null | string>(null);
    const { mockLocal, featureFlags } = useConfig();
    const role = useRole();
    const userIsGPAdmin = role === REPOSITORY_ROLE.GP_ADMIN;
    const userIsGPClinical = role === REPOSITORY_ROLE.GP_CLINICAL;
    const { register, handleSubmit } = useForm({
        reValidateMode: 'onSubmit',
    });
    const { ref: nhsNumberRef, ...searchProps } = register('nhsNumber', {
        required: incorrectFormatMessage,
        pattern: {
            value: /^\s*([0-9]{10}|[0-9]{3}\s[0-9]{3}\s[0-9]{4}|[0-9]{3}-[0-9]{3}-[0-9]{4})\s*$/,
            message: incorrectFormatMessage,
        },
    });
    const navigate = useNavigate();
    const isError = (statusCode && statusCode >= 500) || !inputError;
    const baseUrl = useBaseAPIUrl();
    const baseHeaders = useBaseAPIHeaders();
    const handleSuccess = (patientDetails: PatientDetails): void => {
        setPatientDetails(patientDetails);
        setSubmissionState(SEARCH_STATES.SUCCEEDED);
        navigate(routes.VERIFY_PATIENT);
    };
    const uploadEnabled =
        featureFlags.uploadLambdaEnabled && featureFlags.uploadLloydGeorgeWorkflowEnabled;
    const pageTitle = 'Search for a patient';
    useTitle({ pageTitle: pageTitle });

    const setFailedSubmitState = (statusCode: number | null): void => {
        setStatusCode(statusCode);
        setSubmissionState(SEARCH_STATES.FAILED);
    };

    const handleSearch = async (data: FieldValues): Promise<void> => {
        setSubmissionState(SEARCH_STATES.SEARCHING);
        setInputError(null);
        setStatusCode(null);
        const nhsNumber = data.nhsNumber.replace(/[-\s]/gi, '');
        try {
            const patientDetails = await getPatientDetails({
                nhsNumber,
                baseUrl,
                baseHeaders,
            });

            if (!patientDetails.active && !patientDetails.deceased) {
                if (
                    userIsGPClinical ||
                    (userIsGPAdmin &&
                        (!featureFlags.uploadArfWorkflowEnabled ||
                            !featureFlags.uploadLambdaEnabled))
                ) {
                    setInputError(errorCodes['SP_4003']);
                    setFailedSubmitState(404);
                    return;
                }
            }

            handleSuccess(patientDetails);
        } catch (e) {
            const error = e as AxiosError;
            const errorData = error.response?.data as ErrorResponse;
            /* istanbul ignore if */
            if (isMock(error)) {
                handleSuccess(
                    buildPatientDetails({
                        nhsNumber,
                        active: mockLocal.patientIsActive,
                        deceased: mockLocal.patientIsDeceased,
                    }),
                );
                return;
            }
            if (error.response?.status === 400) {
                setInputError('Enter a valid patient NHS number.');
            } else if (error.response?.status === 403) {
                navigate(routes.SESSION_EXPIRED);
            } else if (error.response?.status === 404) {
                setInputError(errorCodes[errorData?.err_code!] ?? 'Sorry, patient data not found.');
            } else {
                navigate(routes.SERVER_ERROR + errorToParams(error));
            }

            setFailedSubmitState(error.response?.status ?? null);
        }
    };
    const handleError = (fields: FieldValues): void => {
        const errorMessages = Object.entries(fields).map(
            ([k, v]: [string, { message: string }]) => v.message,
        );
        setInputError(errorMessages[0]);
    };
    return (
        <>
            <BackLink asElement="a" href={routes.HOME}>
                Go to home
            </BackLink>
            {(submissionState === SEARCH_STATES.FAILED ||
                inputError === incorrectFormatMessage) && (
                <>
                    {isError ? (
                        <ServiceError />
                    ) : (
                        <ErrorBox
                            messageTitle={'There is a problem'}
                            messageLinkBody={inputError}
                            errorInputLink={'#nhs-number-input'}
                            errorBoxSummaryId={'error-box-summary'}
                        />
                    )}
                </>
            )}

            <h1>{pageTitle}</h1>
            <form onSubmit={handleSubmit(handleSearch, handleError)}>
                <TextInput
                    id="nhs-number-input"
                    data-testid="nhs-number-input"
                    className="nhsuk-input--width-10"
                    label={
                        uploadEnabled
                            ? 'Enter an NHS number to view or upload a record'
                            : 'Enter NHS number'
                    }
                    hint="A 10-digit number, for example, 485 777 3456"
                    type="text"
                    {...searchProps}
                    error={
                        submissionState !== SEARCH_STATES.SEARCHING && inputError
                            ? inputError
                            : false
                    }
                    name="nhsNumber"
                    inputRef={nhsNumberRef as InputRef}
                    readOnly={
                        submissionState === SEARCH_STATES.SUCCEEDED ||
                        submissionState === SEARCH_STATES.SEARCHING
                    }
                    autoComplete="off"
                />

                {submissionState === SEARCH_STATES.SEARCHING ? (
                    <SpinnerButton
                        id="patient-search-spinner"
                        status="Searching..."
                        disabled={true}
                    />
                ) : (
                    <Button type="submit" id="search-submit" data-testid="search-submit-btn">
                        Search
                    </Button>
                )}
            </form>
        </>
    );
};

export default PatientSearchPage;
