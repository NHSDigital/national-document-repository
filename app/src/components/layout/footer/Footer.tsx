import { Footer as NHSFooter } from 'nhsuk-react-components';
import { routes } from '../../../types/generic/routes';

const serviceUpdatesLink =
    'https://digital.nhs.uk/services/access-and-store-digital-patient-documents/service-updates';

const helpandGuidanceLink =
    'https://digital.nhs.uk/services/access-and-store-digital-patient-documents/help-and-guidance';

function Footer() {
    return (
        <NHSFooter>
            <NHSFooter.List>
                <NHSFooter.ListItem
                    href={helpandGuidanceLink}
                    data-testid="help-and-guidance-link"
                    rel="noopener"
                    target="_blank"
                    aria-label="Help and guidance - Opens in a new tab"
                >
                    Help and guidance
                </NHSFooter.ListItem>
                <NHSFooter.ListItem
                    href={routes.PRIVACY_POLICY}
                    data-testid="privacy-link"
                    rel="opener"
                    target="_blank"
                    aria-label="Privacy notice - Opens in a new tab"
                >
                    Privacy notice
                </NHSFooter.ListItem>
                <NHSFooter.ListItem
                    href={serviceUpdatesLink}
                    data-testid="service-updates-link"
                    rel="noopener"
                    target="_blank"
                    aria-label="Service updates - Opens in a new tab"
                >
                    Service updates
                </NHSFooter.ListItem>
                <NHSFooter.ListItem href={routes.COOKIES_POLICY} data-testid="cookies-policy-link">
                    Cookies policy
                </NHSFooter.ListItem>
            </NHSFooter.List>
            <NHSFooter.Copyright className="footer-copyright-link">
                &copy; {'NHS England'}
            </NHSFooter.Copyright>
        </NHSFooter>
    );
}

export default Footer;
