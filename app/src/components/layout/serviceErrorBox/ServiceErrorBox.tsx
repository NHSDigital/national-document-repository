import { ErrorSummary } from 'nhsuk-react-components';
import ServiceDeskLink from '../../generic/serviceDeskLink/ServiceDeskLink';

type Props = {
    message?: string;
};

const ServiceError = ({ message }: Props): React.JSX.Element => {
    const serviceErrorSummaryId = 'service-error-summary';
    const defaultMessage = 'Please try again later.';

    return (
        <ErrorSummary
            aria-labelledby={serviceErrorSummaryId}
            role="alert"
            tabIndex={-1}
            id="service-error"
            data-testid="service-error"
        >
            <ErrorSummary.Title id={serviceErrorSummaryId}>
                Sorry, the service is currently unavailable.
            </ErrorSummary.Title>
            <ErrorSummary.Body>
                <p data-testid="error-summary_message">{message || defaultMessage}</p>
                <p>
                    Please check your internet connection. If the issue persists please contact the{' '}
                    <ServiceDeskLink />.
                </p>
            </ErrorSummary.Body>
        </ErrorSummary>
    );
};

export default ServiceError;
