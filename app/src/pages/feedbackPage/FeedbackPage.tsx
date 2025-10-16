import { JSX, useEffect, useRef, useState } from 'react';

import { SubmitHandler, useForm, UseFormRegisterReturn } from 'react-hook-form';
import isEmail from 'validator/lib/isEmail';
import {
    Button,
    Fieldset,
    TextInput,
    Radios,
    Textarea,
    InsetText,
    HintText,
} from 'nhsuk-react-components';
import { useNavigate } from 'react-router-dom';
import { AxiosError } from 'axios';
import {
    FORM_FIELDS,
    FormData,
    SATISFACTION_CHOICES,
    SUBMISSION_STAGE,
} from '../../types/pages/feedbackPage/types';
import SpinnerButton from '../../components/generic/spinnerButton/SpinnerButton';
import useTitle from '../../helpers/hooks/useTitle';
import useBaseAPIHeaders from '../../helpers/hooks/useBaseAPIHeaders';
import useBaseAPIUrl from '../../helpers/hooks/useBaseAPIUrl';
import sendEmail from '../../helpers/requests/sendEmail';
import { isMock } from '../../helpers/utils/isLocal';
import { routes } from '../../types/generic/routes';
import { errorToParams } from '../../helpers/utils/errorToParams';
import ErrorBox from '../../components/layout/errorBox/ErrorBox';
import {
    FEEDBACK_ERROR_TYPE,
    groupFeedbackErrorsByType,
} from '../../helpers/utils/feedbackErrorMessages';
import { ErrorMessageListItem } from '../../types/pages/genericPageErrors';

type FeedbackError = ErrorMessageListItem<FEEDBACK_ERROR_TYPE>;

const FeedbackPage = (): JSX.Element => {
    const baseUrl = useBaseAPIUrl();
    const baseHeaders = useBaseAPIHeaders();
    const {
        handleSubmit,
        register,
        formState: { errors },
    } = useForm<FormData>({
        reValidateMode: 'onSubmit',
        shouldFocusError: false,
    });
    const navigate = useNavigate();
    const [stage, setStage] = useState(SUBMISSION_STAGE.NotSubmitted);
    const scrollToRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        scrollToRef.current?.scrollIntoView();
    });

    const submit: SubmitHandler<FormData> = async (formData): Promise<void> => {
        setStage(SUBMISSION_STAGE.Submitting);
        try {
            await sendEmail({ formData, baseUrl, baseHeaders });
            navigate(routes.FEEDBACK_CONFIRMATION);
        } catch (e) {
            const error = e as AxiosError;
            if (isMock(error)) {
                navigate(routes.FEEDBACK_CONFIRMATION);
            } else if (error.response?.status === 403) {
                navigate(routes.SESSION_EXPIRED);
                return;
            } else {
                navigate(routes.SERVER_ERROR + errorToParams(error));
            }
        }
    };

    const renameRefKey = (
        props: UseFormRegisterReturn,
        newRefKey: string,
    ): UseFormRegisterReturn => {
        const { ref, ...otherProps } = props;

        return {
            [newRefKey]: ref,
            ...otherProps,
        } as UseFormRegisterReturn;
    };

    const feedbackContentProps = renameRefKey(
        register(FORM_FIELDS.FeedbackContent, {
            required: 'Enter your feedback',
        }),
        'textareaRef',
    );
    const howSatisfiedProps = renameRefKey(
        register(FORM_FIELDS.HowSatisfied, { required: 'Select an option' }),
        'inputRef',
    );
    const respondentNameProps = renameRefKey(register(FORM_FIELDS.RespondentName), 'inputRef');
    const respondentEmailProps = renameRefKey(
        register(FORM_FIELDS.RespondentEmail, {
            validate: (value) => {
                if (value === '' || isEmail(value)) {
                    return true; // accept either blank or a valid email
                }
                return 'Enter a valid email address';
            },
        }),
        'inputRef',
    );
    useTitle({ pageTitle: 'Give feedback on this service' });

    const errorMessageList = (): FeedbackError[] => {
        const errorConfig: {
            key: keyof typeof errors;
            linkId: string;
            error: FEEDBACK_ERROR_TYPE;
        }[] = [
            {
                key: FORM_FIELDS.HowSatisfied,
                linkId: 'select-how-satisfied',
                error: FEEDBACK_ERROR_TYPE.feedbackSatisfaction,
            },
            {
                key: FORM_FIELDS.FeedbackContent,
                linkId: 'feedback_textbox',
                error: FEEDBACK_ERROR_TYPE.feedbackTextbox,
            },
            {
                key: FORM_FIELDS.RespondentEmail,
                linkId: 'email-text-input',
                error: FEEDBACK_ERROR_TYPE.emailTextInput,
            },
        ];

        return errorConfig
            .filter(({ key }) => errors[key])
            .map(({ key, linkId, error }) => ({
                linkId,
                error,
                details: errors[key]!.message,
            }));
    };

    return (
        <div id="feedback-form">
            <h1 data-testid="feedback-page-header">Give feedback on this service</h1>

            {Object.keys(errors).length > 0 && (
                <ErrorBox
                    dataTestId="feedback-error-box"
                    errorBoxSummaryId="feedback-errors"
                    messageTitle="There is a problem"
                    errorMessageList={errorMessageList()}
                    groupErrorsFn={groupFeedbackErrorsByType}
                    scrollToRef={scrollToRef}
                />
            )}

            <form onSubmit={handleSubmit(submit)}>
                <Fieldset id="select-how-satisfied" data-testid="feedback-radio-section">
                    <Fieldset.Legend>
                        <h2>Overall, how satisfied with the service are you?</h2>
                    </Fieldset.Legend>
                    <Radios error={errors.howSatisfied?.message}>
                        {Object.values(SATISFACTION_CHOICES).map((choice) => (
                            <Radios.Radio key={choice} value={choice} {...howSatisfiedProps}>
                                {choice}
                            </Radios.Radio>
                        ))}
                    </Radios>
                </Fieldset>

                <Fieldset id="feedback_textbox" data-testid="feedback-text-section">
                    <Fieldset.Legend>
                        <h2>Can you tell us why you selected that option?</h2>
                    </Fieldset.Legend>
                    <Textarea
                        data-testid={FORM_FIELDS.FeedbackContent}
                        label="You can give details about specific pages or parts of the service here."
                        rows={7}
                        error={errors.feedbackContent?.message}
                        {...feedbackContentProps}
                    />
                </Fieldset>

                <InsetText className="feedback-page_inset-text">
                    <p>
                        Help us improve this service. Tell us more about your experience with using
                        it by completing a further{' '}
                        <a
                            href="https://feedback.digital.nhs.uk/jfe/form/SV_5vE7S5wJ0yleEUm"
                            target="_blank"
                            rel="noreferrer"
                        >
                            short survey (opens in a new tab)
                        </a>
                    </p>
                </InsetText>

                <Fieldset data-testid="feedback-details-section">
                    <Fieldset.Legend>
                        <h3>Leave your details (optional)</h3>
                    </Fieldset.Legend>

                    <HintText>
                        <p>
                            If you’re happy to speak to us about your feedback, leave your details
                            below:
                        </p>
                    </HintText>

                    <TextInput
                        label="Your name"
                        data-testid={FORM_FIELDS.RespondentName}
                        autoComplete="name"
                        spellCheck={false}
                        {...respondentNameProps}
                    />

                    <TextInput
                        id="email-text-input"
                        label="Your email address"
                        hint="We’ll only use this to reply to your message"
                        data-testid={FORM_FIELDS.RespondentEmail}
                        autoComplete="email"
                        spellCheck={false}
                        error={errors.respondentEmail?.message}
                        {...respondentEmailProps}
                    />
                </Fieldset>
                {stage !== SUBMISSION_STAGE.Submitting ? (
                    <Button
                        type="submit"
                        id="submit-feedback"
                        data-testid="submit-feedback"
                        role="button"
                    >
                        Send feedback
                    </Button>
                ) : (
                    <SpinnerButton
                        id="feedback-submit-spinner"
                        dataTestId="feedback-submit-spinner"
                        status="Submitting..."
                        disabled={true}
                    />
                )}
            </form>
        </div>
    );
};

export default FeedbackPage;
