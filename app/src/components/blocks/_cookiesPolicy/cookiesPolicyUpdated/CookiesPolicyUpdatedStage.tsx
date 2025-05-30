import useTitle from '../../../../helpers/hooks/useTitle';
import { routes } from '../../../../types/generic/routes';

const CookiesPolicyUpdatedStage = () => {
    const pageTitle = 'Your cookie settings have been saved';
    useTitle({ pageTitle });

    return (
        <>
            <h1>{pageTitle}</h1>

            <p>We'll save your settings for a year.</p>
            <p>We'll ask you if you're still OK with us using cookies when either:</p>
            <ul>
                <li>
                    it's been a year since you last saved your settings we add any new cookies or
                    change the cookies we use
                </li>
            </ul>
            <p>
                You can also change your settings at any time using our{' '}
                <a className="govuk-link" href={routes.COOKIES_POLICY}>
                    cookies page
                </a>
                .
            </p>
        </>
    );
};

export default CookiesPolicyUpdatedStage;
