import { Button, Checkboxes, Textarea } from 'nhsuk-react-components';
import usePatient from '../../../../helpers/hooks/usePatient';
import useTitle from '../../../../helpers/hooks/useTitle';
import { FieldValues, SubmitHandler, useForm } from 'react-hook-form';
import { useRef, useState } from 'react';
import { routes } from '../../../../types/generic/routes';
import { Link, useNavigate } from 'react-router-dom';
import BackButton from '../../../generic/backButton/BackButton';
import {
    AccessAuditData,
    AccessAuditType,
    DeceasedAccessAuditReasons,
    PatientAccessAudit,
} from '../../../../types/generic/accessAudit';
import useBaseAPIUrl from '../../../../helpers/hooks/useBaseAPIUrl';
import useBaseAPIHeaders from '../../../../helpers/hooks/useBaseAPIHeaders';
import { AxiosError } from 'axios';
import { isMock } from '../../../../helpers/utils/isLocal';
import { errorToParams } from '../../../../helpers/utils/errorToParams';
import ErrorBox from '../../../layout/errorBox/ErrorBox';
import { InputRef } from '../../../../types/generic/inputRef';
import { TextAreaRef } from '../../../../types/generic/textareaRef';
import { usePatientAccessAuditContext } from '../../../../providers/patientAccessAuditProvider/PatientAccessAuditProvider';
import SpinnerButton from '../../../generic/spinnerButton/SpinnerButton';
import postPatientAccessAudit from '../../../../helpers/requests/postPatientAccessAudit';
import PatientSummary, { PatientInfo } from '../../../generic/patientSummary/PatientSummary';

enum FORM_FIELDS {
    Reasons = 'reasons',
    OtherReasonText = 'otherReasonText',
}
type FormData = {
    [FORM_FIELDS.Reasons]: string[];
    [FORM_FIELDS.OtherReasonText]: string;
};

const DeceasedPatientAccessAudit = (): React.JSX.Element => {
    /* HOOKS */
    const pageTitle = 'Deceased patient record';
    useTitle({ pageTitle });

    const baseUrl = useBaseAPIUrl();
    const baseHeaders = useBaseAPIHeaders();

    const navigate = useNavigate();

    const [patientAccessAudit, setPatientAccessAudit] = usePatientAccessAuditContext();

    const patientDetails = usePatient();
    const deceasedPatientAccessAudit = patientAccessAudit?.find(
        (audit) =>
            audit.accessAuditType === AccessAuditType.deceasedPatient &&
            audit.nhsNumber === patientDetails?.nhsNumber,
    );

    const {
        register,
        handleSubmit,
        getValues,
        formState: { errors },
    } = useForm<FormData>({
        reValidateMode: 'onSubmit',
        shouldFocusError: true,
        defaultValues: {
            reasons: deceasedPatientAccessAudit?.accessAuditData.Reasons ?? [],
            otherReasonText: deceasedPatientAccessAudit?.accessAuditData.OtherReasonText ?? '',
        },
    });

    const [inputErrors, setInputErrors] = useState<undefined | { message: string; id: string }[]>(
        undefined,
    );
    const [anotherReasonSelected, setAnotherReasonSelected] = useState<boolean>(
        deceasedPatientAccessAudit?.accessAuditData.Reasons.includes(
            DeceasedAccessAuditReasons.anotherReason,
        ) ?? false,
    );
    const [submitting, setSubmitting] = useState<boolean>(false);
    const scrollToErrorRef = useRef<HTMLDivElement>(null);
    /* HOOKS */

    if (!patientDetails) {
        navigate(routes.SEARCH_PATIENT);
        return <></>;
    }

    const { ref: checkboxInputRef, ...checkboxProps } = register(FORM_FIELDS.Reasons, {
        required: 'Select a reason why you need to access this record',
        validate: () => {
            const selectedReasons = getValues()[FORM_FIELDS.Reasons];

            if (selectedReasons.length === 0) {
                return false;
            }

            setAnotherReasonSelected(
                selectedReasons.includes(DeceasedAccessAuditReasons.anotherReason),
            );

            return true;
        },
        onChange: () => {
            const selectedReasons = getValues()[FORM_FIELDS.Reasons] ?? [];
            setAnotherReasonSelected(
                selectedReasons.includes(DeceasedAccessAuditReasons.anotherReason),
            );
        },
    });

    const { ref: textareaInputRef, ...textareaProps } = register(FORM_FIELDS.OtherReasonText, {
        validate: (value) => {
            if (!anotherReasonSelected) {
                return true;
            }

            if (value?.length > 10000) {
                return 'Enter your response in 10000 characters or less';
            }

            return value?.length > 0 ? true : 'Enter a reason why you need to access this record';
        },
    });

    const submitForm: SubmitHandler<FormData> = async (formData) => {
        const accessAuditData: AccessAuditData = {
            Reasons: formData.reasons,
        };

        if (formData.reasons.includes(DeceasedAccessAuditReasons.anotherReason)) {
            accessAuditData.OtherReasonText = formData.otherReasonText;
        }

        if (
            JSON.stringify(accessAuditData) ===
            JSON.stringify(deceasedPatientAccessAudit?.accessAuditData)
        ) {
            handleSuccess(accessAuditData);
            return;
        }

        try {
            setSubmitting(true);

            await postPatientAccessAudit({
                accessAuditData,
                accessAuditType: AccessAuditType.deceasedPatient,
                baseUrl,
                baseHeaders,
                nhsNumber: patientDetails!.nhsNumber,
            });

            setSubmitting(false);

            handleSuccess(accessAuditData);
        } catch (e) {
            const error = e as AxiosError;

            if (isMock(error)) {
                handleSuccess(accessAuditData);
            } else if (error.code === '403') {
                navigate(routes.SESSION_EXPIRED);
            } else {
                navigate(routes.SERVER_ERROR + errorToParams(error));
            }
        }
    };

    const handleSuccess = (accessAuditData: AccessAuditData): void => {
        const newPatientAccessAudit = patientAccessAudit?.map((audit): PatientAccessAudit => {
            if (
                audit.accessAuditType === AccessAuditType.deceasedPatient &&
                audit.nhsNumber === patientDetails?.nhsNumber
            ) {
                return {
                    ...audit,
                    accessAuditData,
                    nhsNumber: patientDetails?.nhsNumber,
                } as PatientAccessAudit;
            }

            return audit;
        }) ?? [
            {
                accessAuditType: AccessAuditType.deceasedPatient,
                accessAuditData,
                nhsNumber: patientDetails?.nhsNumber,
            } as PatientAccessAudit,
        ];

        setPatientAccessAudit(newPatientAccessAudit);
        navigate(routes.LLOYD_GEORGE);
    };

    const handleError = (fields: FieldValues): void => {
        const errorMessages = Object.entries(fields).map(
            ([k, v]: [string, { message: string; ref: Element }]) => {
                return {
                    message: v.message,
                    id: v.ref.id,
                };
            },
        );
        setInputErrors(errorMessages);

        scrollToErrorRef.current?.scrollIntoView();
    };

    const ReasonCheckbox = (
        reason: DeceasedAccessAuditReasons,
        label: string,
    ): React.JSX.Element => {
        const key = `reason-checkbox-${reason}`;

        return (
            <Checkboxes.Box
                key={key}
                data-testid={key}
                value={reason}
                inputRef={checkboxInputRef as InputRef}
                {...checkboxProps}
            >
                {label}
            </Checkboxes.Box>
        );
    };

    return (
        <div className="deceased-patient-access-page">
            <BackButton toLocation={routes.VERIFY_PATIENT} />

            {inputErrors && inputErrors.length > 0 && (
                <ErrorBox
                    dataTestId="access-reason-error-box"
                    errorBoxSummaryId="access-reason"
                    messageTitle="There is a problem"
                    errorInputLink={`#${inputErrors[0].id}`}
                    messageLinkBody={inputErrors[0].message}
                    scrollToRef={scrollToErrorRef}
                />
            )}

            <h1 data-testid="title">{pageTitle}</h1>

            <PatientSummary>
                <PatientSummary.Child item={PatientInfo.FULL_NAME} />
                <PatientSummary.Child item={PatientInfo.NHS_NUMBER} />
                <PatientSummary.Child item={PatientInfo.BIRTH_DATE} />
            </PatientSummary>

            <h2>Why do you need to access this record?</h2>
            <p>Select all options that are relevant.</p>
            <form onSubmit={handleSubmit(submitForm, handleError)}>
                <Checkboxes name="access-reason" id="access-reason" error={errors.reasons?.message}>
                    {ReasonCheckbox(
                        DeceasedAccessAuditReasons.medicalRequest,
                        'to respond to a request from a coroner or medical examiner',
                    )}
                    {ReasonCheckbox(
                        DeceasedAccessAuditReasons.legalRequest,
                        'to respond to a legal or insurance request',
                    )}
                    {ReasonCheckbox(
                        DeceasedAccessAuditReasons.familyRequest,
                        'to respond to a request from a family member or personal representative of the patient',
                    )}
                    {ReasonCheckbox(
                        DeceasedAccessAuditReasons.internalNhsRequest,
                        'to respond to an internal NHS request',
                    )}
                    {ReasonCheckbox(
                        DeceasedAccessAuditReasons.removeRecord,
                        'to remove this record at the end of its retention period',
                    )}
                    <Checkboxes.Divider />
                    {ReasonCheckbox(DeceasedAccessAuditReasons.anotherReason, 'another reason')}
                    {anotherReasonSelected && (
                        <Textarea
                            data-testid={FORM_FIELDS.OtherReasonText}
                            className="other-reason-text"
                            label="Enter a reason."
                            hint="Do not include information that could be used to identify any individual."
                            rows={4}
                            error={errors.otherReasonText?.message}
                            textareaRef={textareaInputRef as TextAreaRef}
                            {...textareaProps}
                        />
                    )}
                </Checkboxes>
                <div className="button-container">
                    {submitting ? (
                        <SpinnerButton
                            id="submitting-spinner"
                            status="Loading record"
                            disabled={true}
                        />
                    ) : (
                        <>
                            <Button type="submit" id="form-submit" data-testid="form-submit-button">
                                Continue to the record
                            </Button>
                            <Link
                                className="ml-6"
                                to={routes.SEARCH_PATIENT}
                                data-testid="back-to-search-button"
                            >
                                Go back to Search for a patient
                            </Link>
                        </>
                    )}
                </div>
            </form>
        </div>
    );
};

export default DeceasedPatientAccessAudit;
