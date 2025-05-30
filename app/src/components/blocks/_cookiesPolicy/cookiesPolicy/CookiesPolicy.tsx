import { Button, Details, Fieldset, Radios, Table } from 'nhsuk-react-components';
import useTitle from '../../../../helpers/hooks/useTitle';
import { SubmitHandler, useForm } from 'react-hook-form';
import { useNavigate } from 'react-router';
import { routeChildren } from '../../../../types/generic/routes';
import { InputRef } from '../../../../types/generic/inputRef';
import { useEffect } from 'react';

enum Fields {
    analyticsConsent = 'analyticsConsent',
}

enum ConsentOptions {
    YES = 'yes',
    NO = 'no',
}

type FormData = {
    [Fields.analyticsConsent]: string;
};

const CookiePolicy = () => {
    const { register, handleSubmit, setValue } = useForm<FormData>();
    const { ref: consentRef, ...radioProps } = register(Fields.analyticsConsent);

    const navigate = useNavigate();

    const updatePreferences: SubmitHandler<FormData> = async (formData) => {
        window.NHSCookieConsent.setStatistics(formData.analyticsConsent === ConsentOptions.YES);

        // this hides the banner so it won't appear on next visit
        window.NHSCookieConsent.setConsented(true);
        navigate(routeChildren.COOKIES_POLICY_UPDATED);
    };

    const pageTitle = 'Cookies policy';
    useTitle({ pageTitle });

    useEffect(() => {
        const consent = window.NHSCookieConsent.getStatistics()
            ? ConsentOptions.YES
            : ConsentOptions.NO;
        setValue(Fields.analyticsConsent, consent);
    });

    return (
        <>
            <h1>{pageTitle}</h1>

            <h3>What are cookies?</h3>
            <p>
                Cookies are files saved on your phone, tablet or computer when you visit a website.
            </p>
            <p>
                They store information about how you use the website, such as the pages you visit.
            </p>
            <p>
                Cookies are not viruses or computer programs. They are very small so do not take up
                much space.
            </p>

            <h3>How we use cookies</h3>
            <p>We only use cookies to:</p>
            <ul>
                <li>make our website work</li>
                <li>
                    measure how you use our website, such as which links you click on &#40;analytics
                    cookies&#41;, if you give us permission
                </li>
            </ul>
            <p>
                We do not use any other cookies, for example, cookies that remember your settings or
                cookies that help with health campaigns.
            </p>
            <p>
                We sometimes use tools on other organisations' websites to collect data or to ask
                for feedback. These tools set their own cookies.
            </p>

            <h3>Cookies that make our website work</h3>
            <p>We use cookies to keep our website secure and fast.</p>
            <Details>
                <Details.Summary>List of cookies that make our website work</Details.Summary>
                <Details.Text>
                    <Table>
                        <Table.Head>
                            <Table.Row>
                                <Table.Cell>Cookie name</Table.Cell>
                                <Table.Cell>Purpose</Table.Cell>
                                <Table.Cell>Expiry</Table.Cell>
                            </Table.Row>
                        </Table.Head>
                        <Table.Body>
                            <Table.Row>
                                <Table.Cell>nhsuk-cookie-consent</Table.Cell>
                                <Table.Cell>
                                    Remembers if you used our cookies consent banner
                                </Table.Cell>
                                <Table.Cell>
                                    When you close the browser &#40;if you do not use the
                                    banner&#41; or 1 year &#40;if you use the banner&#41;
                                </Table.Cell>
                            </Table.Row>
                        </Table.Body>
                    </Table>
                </Details.Text>
            </Details>

            <h3>Cookies that measure website use</h3>
            <p>
                We also like to use analytics cookies. These cookies store anonymous information
                about how you use our website, such as which pages you visit or what you click on.
            </p>
            <Details>
                <Details.Summary>List of cookies that measure website use</Details.Summary>
                <Details.Text>
                    <Table>
                        <Table.Head>
                            <Table.Row>
                                <Table.Cell>Cookie name</Table.Cell>
                                <Table.Cell>Purpose</Table.Cell>
                                <Table.Cell>Expiry</Table.Cell>
                            </Table.Row>
                        </Table.Head>
                        <Table.Body></Table.Body>
                    </Table>
                </Details.Text>
            </Details>
            <p>
                We'll only use these cookies if you say it's OK. We'll use a cookie to save your
                settings.
            </p>

            <h3>Tell us if we can use analytics cookies</h3>
            <form onSubmit={handleSubmit(updatePreferences)}>
                <Fieldset>
                    <Radios>
                        <Radios.Radio
                            value={ConsentOptions.YES}
                            inputRef={consentRef as InputRef}
                            {...radioProps}
                            id="yes-radio-button"
                            data-testid="yes-radio-button"
                        >
                            Use cookies to measure my website use
                        </Radios.Radio>
                        <Radios.Radio
                            value={ConsentOptions.NO}
                            inputRef={consentRef as InputRef}
                            {...radioProps}
                            id="no-radio-button"
                            data-testid="no-radio-button"
                        >
                            Do not use cookies to measure my website use
                        </Radios.Radio>
                    </Radios>
                </Fieldset>
                <Button type="submit">Save my cookie settings</Button>
            </form>
        </>
    );
};

export default CookiePolicy;
