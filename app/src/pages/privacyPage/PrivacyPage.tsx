import React from 'react';
import useRole from '../../helpers/hooks/useRole';
import { routes } from '../../types/generic/routes';
import { Link, useNavigate } from 'react-router-dom';
import useTitle from '../../helpers/hooks/useTitle';

const PrivacyPage = (): React.JSX.Element => {
    const isLoggedIn = !!useRole();
    const navigate = useNavigate();
    const pageHeader = 'Privacy notice';
    const gdprLink =
        'https://digital.nhs.uk/data-and-information/keeping-data-safe-and-benefitting-the-public/gdpr#:~:text=The%20GDPR%20came%20into%20effect,in%20line%20with%20the%20regulations';
    useTitle({ pageTitle: pageHeader });
    return (
        <>
            <section>
                <h1>{pageHeader}</h1>
                <h2>Our permission to process and store patient data</h2>
                <p>
                    This service has legal permission to process and store patient data through the
                    <strong> National Data Processing Deed</strong>.
                </p>
                <p>The National Data Processing Deed enables NHS England to: </p>
                <ul>
                    <li>act as the data processor for all GP practices in England</li>
                    <li>
                        store the digitised Lloyd George records of patients registered at these GP
                        practices.
                    </li>
                </ul>
                <p>
                    This deed operates under the{' '}
                    <a
                        data-testid="permission-section-gdpr-link"
                        target="_blank"
                        href={gdprLink}
                        rel="noreferrer"
                        aria-label="UK General Data Protection Regulation (GDPR) 2018 - this link will open in a new tab"
                    >
                        UK General Data Protection Regulation (GDPR) 2018
                    </a>{' '}
                    .
                </p>
                <p>
                    GP practices in England are automatically signed up to the National Data
                    Processing Deed, so you don't need to do anything.
                </p>
            </section>

            <section>
                <h2>What happens with my personal information?</h2>
                <p>
                    If you sign in to the 'Access and store digital patient documents' service using
                    your{' '}
                    <a
                        data-testid="cis2-link"
                        target="_blank"
                        href="https://am.nhsidentity.spineservices.nhs.uk/openam/XUI/?realm=/#/"
                        rel="noreferrer"
                        aria-label="NHS Care Identity - this link will open in a new tab"
                    >
                        NHS Care Identity
                    </a>{' '}
                    credentials, your NHS Care Identity credentials are managed by NHS England.
                </p>
                <p>
                    This means NHS England is the data controller for any personal information that
                    you provided to get NHS Care Identity credentials.
                </p>
                <p>NHS England uses this information only to verify your identity.</p>
                <p>
                    When verifying your identity, we act as the data "processor". We must act under
                    instructions provided by NHS England (the "controller").
                </p>
                <p>
                    To find out more about NHS England's Privacy Notice and its Terms and
                    Conditions, view the{' '}
                    <a
                        data-testid="cis2-service-link"
                        target="_blank"
                        href="https://digital.nhs.uk/services/care-identity-service"
                        rel="noreferrer"
                        aria-label="NHS Care Identity Service - this link will open in a new tab"
                    >
                        NHS Care Identity Service
                    </a>{' '}
                    .
                </p>
                <p>This only applies to information you provide through NHS England.</p>
            </section>

            <section>
                <h2>Further information</h2>
                <p>
                    <a
                        data-testid="data-controller-link"
                        target="_blank"
                        href="https://www.england.nhs.uk/contact-us/privacy-notice/nhs-england-as-a-data-controller/"
                        rel="noreferrer"
                        aria-label="NHS England's role as a data controller - this link will open in a new tab"
                    >
                        NHS England's role as a data controller
                    </a>{' '}
                </p>
            </section>

            <section>
                <h2>Feedback form privacy notice</h2>
                <p>
                    When submitting your details using our{' '}
                    {isLoggedIn ? (
                        <Link
                            data-testid="feedback-link"
                            to={'#'}
                            onClick={(e): void => {
                                e.preventDefault();
                                navigate(routes.FEEDBACK);
                            }}
                        >
                            feedback form
                        </Link>
                    ) : (
                        <span data-testid="feedback-link">feedback form</span>
                    )}
                    , any personal information you give to us will be processed in accordance with
                    the{' '}
                    <a
                        data-testid="gdpr-link"
                        target="_blank"
                        href={gdprLink}
                        rel="noreferrer"
                        aria-label="UK General Data Protection Regulation (GDPR) 2018 - this link will open in a new tab"
                    >
                        UK General Data Protection Regulation (GDPR) 2018
                    </a>{' '}
                    .
                </p>
                <p>
                    We use the information you submit to process your feedback and provide you with
                    the relevant information or services you have requested.
                </p>
                <p>This will help support us in developing this service.</p>
            </section>

            <section>
                <h2>Contact us</h2>
                <p>
                    If you have any questions about the National Data Processing Deed, or our
                    privacy policy, you can contact the team on{' '}
                    <a
                        href="mailto:england.prmteam@nhs.net"
                        aria-label="Send an email to england.prmteam@nhs.net"
                    >
                        england.prmteam@nhs.net
                    </a>{' '}
                    .
                </p>
            </section>
        </>
    );
};

export default PrivacyPage;
