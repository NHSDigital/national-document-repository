import { useNavigate, useSearchParams } from 'react-router-dom';
import { ButtonLink } from 'nhsuk-react-components';
import errorCodes from '../../helpers/utils/errorCodes';
import { unixTimestamp } from '../../helpers/utils/createTimestamp';
import useTitle from '../../helpers/hooks/useTitle';

type ServerError = [errorCode: string | null, interactionId: string | null];

const ServerErrorPage = (): React.JSX.Element => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const encodedError: string | null = searchParams.get('encodedError') ?? null;
    const error: ServerError = encodedError ? JSON.parse(atob(encodedError)) : [null, null];
    const [errorCode, interactionId] = error;

    const defaultMessage = 'There was an unexplained error';

    const errorMessage =
        errorCode && !!errorCodes[errorCode] ? errorCodes[errorCode] : defaultMessage;

    const interactionCode = interactionId ?? unixTimestamp();
    useTitle({ pageTitle: 'Service error' });

    return (
        <>
            <h1>Sorry, there is a problem with the service</h1>
            <p>{errorMessage}</p>
            <p>
                Try again by returning to the previous page. You'll need to enter any information
                you submitted again.
            </p>
            <ButtonLink
                href="#"
                onClick={(e): void => {
                    e.preventDefault();
                    const errorUrl = window.location.href;
                    // Navigate back two paces incase the previous page has an error in the prefetch
                    navigate(-2);

                    // If this code is reached, we can assume that the component
                    // has not destroyed and navigate(-2) has no where to go
                    const urlAfterMinusTwoNavigate = window.location.href;
                    const urlHasNotChanged = errorUrl === urlAfterMinusTwoNavigate;
                    if (urlHasNotChanged) {
                        navigate(-1);
                    }
                }}
            >
                Return to previous page
            </ButtonLink>

            <h2>If this error keeps appearing</h2>
            <p>
                <a
                    href="https://digital.nhs.uk/about-nhs-digital/contact-us#nhs-digital-service-desks"
                    target="_blank"
                    rel="noreferrer"
                    aria-label="Contact the NHS National Service Desk - this link will open in a new tab"
                >
                    Contact the NHS National Service Desk
                </a>{' '}
                or call 0300 303 5035
            </p>

            <p>
                When contacting the service desk, quote this error code as reference:{' '}
                <strong>{interactionCode}</strong>
            </p>
        </>
    );
};
export default ServerErrorPage;
