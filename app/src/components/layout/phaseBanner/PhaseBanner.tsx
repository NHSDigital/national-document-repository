import { routes } from '../../../types/generic/routes';
import { useSessionContext } from '../../../providers/sessionProvider/SessionProvider';
import { Link } from 'react-router-dom';
import { Tag } from 'nhsuk-react-components';

const PhaseBanner = (): React.JSX.Element => {
    const [session] = useSessionContext();
    const { isLoggedIn } = session;
    const linkToFeedbackPage = isLoggedIn ? (
        <Link
            to={routes.FEEDBACK}
            target="_blank"
            rel="opener"
            aria-label="feedback - this link will open in a new tab"
        >
            feedback
        </Link>
    ) : (
        'feedback'
    );

    return (
        <div className="nhsuk-phase-banner">
            <div className="nhsuk-width-container">
                <div className="nhsuk-phase-banner__content">
                    <Tag className="nhsuk-phase-banner__content__tag ">New service</Tag>
                    <p className="nhsuk-phase-banner__text">
                        Your {linkToFeedbackPage} will help us to improve this service.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default PhaseBanner;
