import { Button, Fieldset, Input, Radios, Textarea } from 'nhsuk-react-components';
import { SubmitHandler, useForm, UseFormRegisterReturn } from 'react-hook-form';
import { FORM_FIELDS, FormData, SATISFACTION_CHOICES } from '../../types/pages/feedbackPage/types';
import sendEmail from '../../helpers/requests/sendEmail';

function FeedbackPage() {
    const {
        handleSubmit,
        register,
        formState: { errors },
    } = useForm<FormData>();

    /* eslint-disable no-console */
    // using console.log as placeholder until we got the send email solution in place
    const submit: SubmitHandler<FormData> = async (formData) => {
        sendEmail(formData)
            .then(() => {
                console.log('Successfully sent email');
                console.log('will move to confirmation screen');
            })
            .catch((e) => console.error(`got error: ${e}`));
    };
    /* eslint-enable no-console */

    const feedbackContentProps = renameRefKey(
        register(FORM_FIELDS.feedbackContent, {
            required: 'Please enter your feedback',
        }),
        'textareaRef',
    );
    const howSatisfiedProps = renameRefKey(
        register(FORM_FIELDS.howSatisfied, { required: 'Please select an option' }),
        'inputRef',
    );
    const respondentNameProps = renameRefKey(register(FORM_FIELDS.respondentName), 'inputRef');
    const respondentEmailProps = renameRefKey(register(FORM_FIELDS.respondentEmail), 'inputRef');

    return (
        <div id="feedback-form">
            <h1>Give feedback on accessing Lloyd George digital patient records</h1>

            <form onSubmit={handleSubmit(submit)}>
                <Fieldset>
                    <Fieldset.Legend size="m">What is your feedback?</Fieldset.Legend>
                    <Textarea
                        data-testid={FORM_FIELDS.feedbackContent}
                        label="Tell us how we could improve this service or explain your experience using it. You
                can also give feedback about a specific page or section in the service."
                        rows={7}
                        error={errors.feedbackContent?.message}
                        {...feedbackContentProps}
                    />
                </Fieldset>

                <Fieldset>
                    <Fieldset.Legend size="m">
                        How satisfied were you with your overall experience of using this service?
                    </Fieldset.Legend>
                    <Radios id="select-how-satisfied" error={errors.howSatisfied?.message}>
                        {Object.values(SATISFACTION_CHOICES).map((choice, i) => (
                            <Radios.Radio key={i} value={choice} {...howSatisfiedProps}>
                                {choice}
                            </Radios.Radio>
                        ))}
                    </Radios>
                </Fieldset>

                <Fieldset>
                    <Fieldset.Legend size="m">Leave your details (optional)</Fieldset.Legend>

                    <p>
                        If you’re happy to speak to us about your feedback so we can improve this
                        service, please leave your details below.
                    </p>

                    <Input
                        label="Your name"
                        data-testid={FORM_FIELDS.respondentName}
                        {...respondentNameProps}
                    />

                    <Input
                        label="Your email address"
                        hint="We’ll only use this to speak to you about your feedback"
                        data-testid={FORM_FIELDS.respondentEmail}
                        {...respondentEmailProps}
                    />
                </Fieldset>

                <Button type="submit" id="feedback-submit-btn" data-testid="feedback-submit-btn">
                    Send feedback
                </Button>
            </form>
        </div>
    );
}

const renameRefKey = (
    props: UseFormRegisterReturn,
    newRefKey: string,
): Partial<UseFormRegisterReturn> => {
    const { ref, ...otherProps } = props;
    return {
        [newRefKey]: ref,
        ...otherProps,
    };
};

export default FeedbackPage;
