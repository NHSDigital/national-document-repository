import { Card } from 'nhsuk-react-components';
import { routes } from '../../types/generic/routes';
import useTitle from '../../helpers/hooks/useTitle';
import { REPORT_TYPE } from '../../types/generic/reports';
import { ReactComponent as RightCircleIcon } from '../../styles/right-chevron-circle.svg';
import useConfig from '../../helpers/hooks/useConfig';

const HomePage = (): React.JSX.Element => {
    useTitle({ pageTitle: 'Access and store digital patient documents' });
    const config = useConfig();
    const uploadEnabled =
        config.featureFlags.uploadLambdaEnabled &&
        config.featureFlags.uploadLloydGeorgeWorkflowEnabled;

    return (
        <>
            <h1 className="smaller-title">Access and store digital patient documents</h1>
            <h3>Select an action</h3>
            <Card.Group>
                <Card.GroupItem width="one-half">
                    <Card clickable cardType="primary">
                        <Card.Content className="home-action-card-content">
                            {uploadEnabled ? (
                                <>
                                    <Card.Heading className="nhsuk-heading-m">
                                        <Card.Link
                                            data-testid="search-patient-btn"
                                            href={routes.SEARCH_PATIENT}
                                        >
                                            View or upload a patient record
                                        </Card.Link>
                                    </Card.Heading>
                                    <Card.Description>
                                        View or upload a Lloyd George record for a patient using
                                        their NHS number.
                                    </Card.Description>
                                </>
                            ) : (
                                <>
                                    <Card.Heading className="nhsuk-heading-m">
                                        <Card.Link
                                            data-testid="search-patient-btn"
                                            href={routes.SEARCH_PATIENT}
                                        >
                                            Search for a patient
                                        </Card.Link>
                                    </Card.Heading>
                                    <Card.Description>
                                        Find a Lloyd George record for a patient using their NHS
                                        number.
                                    </Card.Description>
                                </>
                            )}
                            <RightCircleIcon />
                        </Card.Content>
                    </Card>
                </Card.GroupItem>
                <Card.GroupItem width="one-half">
                    <Card clickable cardType="primary">
                        <Card.Content>
                            <Card.Heading className="nhsuk-heading-m">
                                <Card.Link
                                    data-testid="download-report-btn"
                                    href={`${routes.REPORT_DOWNLOAD}?reportType=${REPORT_TYPE.ODS_PATIENT_SUMMARY}`}
                                >
                                    Download a report
                                </Card.Link>
                            </Card.Heading>
                            <Card.Description>
                                This report shows the list of Lloyd George records stored for your
                                organisation.
                            </Card.Description>
                            <RightCircleIcon />
                        </Card.Content>
                    </Card>
                </Card.GroupItem>
            </Card.Group>
        </>
    );
};

export default HomePage;
