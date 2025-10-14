import React, { useState } from 'react';
import type { MouseEvent } from 'react';
import { ButtonLink } from 'nhsuk-react-components';
import { useNavigate } from 'react-router-dom';
import Spinner from '../../components/generic/spinner/Spinner';
import { routes } from '../../types/generic/routes';
import { endpoints } from '../../types/generic/endpoints';
import { isLocal } from '../../helpers/utils/isLocal';
import useBaseAPIUrl from '../../helpers/hooks/useBaseAPIUrl';
import TestPanel from '../../components/blocks/testPanel/TestPanel';
import ServiceDeskLink from '../../components/generic/serviceDeskLink/ServiceDeskLink';
import useTitle from '../../helpers/hooks/useTitle';

type Props = {};

function StartPage(props: Props) {
    const navigate = useNavigate();
    const baseAPIUrl = useBaseAPIUrl();
    const [isLoading, setIsLoading] = useState(false);
    const handleLogin = (e: MouseEvent<HTMLAnchorElement>) => {
        setIsLoading(true);
        e.preventDefault();
        if (isLocal) {
            navigate(routes.AUTH_CALLBACK);
        } else {
            window.location.replace(`${baseAPIUrl}${endpoints.LOGIN}`);
        }
    };
    const pageHeader = 'Access and store digital patient documents';
    useTitle({ pageTitle: pageHeader });
    return !isLoading ? (
        <>
            <h1>{pageHeader}</h1>
            <p>
                This service gives you access to digital Lloyd George records. You may have received
                a note within a patient record, stating that the record has been digitised.
            </p>
            <p>If you are part of a GP practice, you can use this service to:</p>
            <ul>
                <li>view a patient record</li>
                <li>download a patient record</li>
                <li>remove a patient record</li>
                <li>download a report on the records held within this service</li>
                <li>upload a patient record</li>
            </ul>
            <p>If you are managing records on behalf of NHS England, you can:</p>
            <ul>
                <li>download a patient record</li>
                <li>download a report on the records held within this service</li>
                <li>upload a patient record</li>
            </ul>
            <p>Not every patient will have a digital record available.</p>
            <p>
                You can upload files for patients who do not currently have a Lloyd George record
                stored in this service.
            </p>
            <h2>Before you start</h2>
            <p>You’ll be asked for:</p>
            <ul>
                <li>your NHS smartcard</li>
                <li>patient details including their name, date of birth and NHS number</li>
            </ul>
            <ButtonLink data-testid="start-btn" onClick={handleLogin} href="#">
                Start now
            </ButtonLink>
            <h3>Get support with the service</h3>
            <p>
                {'Contact the '}
                <ServiceDeskLink />
                {' if there is an issue with this service or call 0300 303 5035.'}
            </p>
            {(import.meta.env.VITE_ENVIRONMENT === 'local' ||
                import.meta.env.VITE_ENVIRONMENT === 'development' ||
                import.meta.env.VITE_ENVIRONMENT === 'test') && <TestPanel />}
        </>
    ) : (
        <Spinner status="Signing in..." />
    );
}

export default StartPage;
