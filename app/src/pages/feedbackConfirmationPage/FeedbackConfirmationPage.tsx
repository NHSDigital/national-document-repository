import useTitle from '../../helpers/hooks/useTitle';

const FeedbackConfirmationPage = (): React.JSX.Element => {
    const pageHeader = 'We’ve received your feedback';
    useTitle({ pageTitle: 'Feedback sent' });

    return (
        <>
            <h1>{pageHeader}</h1>
            <p>If you have left your details, our team will contact you soon.</p>
            <p>You can now close this window.</p>
        </>
    );
};

export default FeedbackConfirmationPage;
