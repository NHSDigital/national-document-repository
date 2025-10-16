import { Dispatch, MouseEvent, SetStateAction } from 'react';
import { ButtonLink, Card } from 'nhsuk-react-components';
import { routes } from '../../../../types/generic/routes';
import { Link, useNavigate } from 'react-router-dom';
import useRole from '../../../../helpers/hooks/useRole';
import { REPOSITORY_ROLE } from '../../../../types/generic/authRole';
import ReducedPatientInfo from '../../../generic/reducedPatientInfo/ReducedPatientInfo';
import useTitle from '../../../../helpers/hooks/useTitle';
import { DOWNLOAD_STAGE } from '../../../../types/generic/downloadStage';

export type Props = {
    numberOfFiles: number;
    setDownloadStage?: Dispatch<SetStateAction<DOWNLOAD_STAGE>>;
};

const DeleteResultStage = ({ numberOfFiles, setDownloadStage }: Props): React.JSX.Element => {
    const navigate = useNavigate();
    const role = useRole();

    const handleClick = (e: MouseEvent<HTMLAnchorElement>): void => {
        e.preventDefault();
        if (setDownloadStage) {
            setDownloadStage(DOWNLOAD_STAGE.REFRESH);
        }
        navigate(routes.LLOYD_GEORGE);
    };

    const isGP = role === REPOSITORY_ROLE.GP_ADMIN || role === REPOSITORY_ROLE.GP_CLINICAL;
    const pageHeader = 'You have permanently removed the record of:';
    useTitle({ pageTitle: pageHeader });

    return (
        <div className="deletion-complete">
            <Card className="deletion-complete_card">
                <Card.Content className="deletion-complete_card_content">
                    <Card.Heading
                        className="deletion-complete_card_content_header"
                        data-testid="deletion-complete_card_content_header"
                        headingLevel="h1"
                    >
                        {pageHeader}
                    </Card.Heading>
                    <ReducedPatientInfo className={'deletion-complete_card_content_subheader'} />
                </Card.Content>
            </Card>
            <p>You can no longer access this record using our storage.</p>
            <h2 className="nhsuk-heading-l">What happens next</h2>
            <ol>
                <li>
                    Make sure you safely store the paper version of this record, as it may be the
                    only copy
                </li>
                <li>
                    If you removed this record due to its retention period ending, you do not need
                    to store the paper copy
                </li>
                <li>
                    If you think you’ve made a mistake, you will need to upload this record again
                </li>
            </ol>
            <h3 className="nhsuk-heading-m">Your responsibilities after removing this record</h3>
            <p>
                Everyone in a health and care organisation is responsible for managing records
                appropriately. It is important all general practice staff understand their
                responsibilities for creating, and disposing of records appropriately.
            </p>
            <h3 className="nhsuk-heading-m">Follow the Record Management Code of Practice</h3>
            <p>
                The{' '}
                <a
                    href="https://transform.england.nhs.uk/information-governance/guidance/records-management-code"
                    target="_blank"
                    rel="noreferrer"
                    aria-label="Record Management Code of Practice - this link will open in a new tab"
                >
                    Record Management Code of Practice
                </a>{' '}
                provides a framework for consistent and effective records management, based on
                established standards.
            </p>
            <p className="paragraph-top-margin">
                {isGP ? (
                    <ButtonLink onClick={handleClick} data-testid="lg-return-btn" href="#">
                        Return to patient's Lloyd George record page
                    </ButtonLink>
                ) : (
                    <Link
                        id="start-again-link"
                        data-testid="start-again-link"
                        to=""
                        onClick={(e): void => {
                            e.preventDefault();
                            navigate(routes.START);
                        }}
                    >
                        Start Again
                    </Link>
                )}
            </p>
        </div>
    );
};

export default DeleteResultStage;
