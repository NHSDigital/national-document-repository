import { Dispatch, HTMLAttributes, SetStateAction } from 'react';
import { LGRecordActionLink, RECORD_ACTION } from '../../../types/blocks/lloydGeorgeActions';
import { Link, useNavigate } from 'react-router-dom';
import { LG_RECORD_STAGE } from '../../../types/blocks/lloydGeorgeStages';

export type Props = HTMLAttributes<HTMLDivElement> & {
    recordLinks: Array<LGRecordActionLink>;
    setStage: Dispatch<SetStateAction<LG_RECORD_STAGE>>;
    showMenu: boolean;
    className?: string;
};

type SubSectionProps = {
    actionLinks: Array<LGRecordActionLink>;
    heading: string;
    setStage: Dispatch<SetStateAction<LG_RECORD_STAGE>>;
};

const RecordMenuCard = ({
    recordLinks,
    setStage,
    showMenu,
    className = 'lloydgeorge_record-stage_links',
}: Props): React.JSX.Element => {
    const updateActions = recordLinks.filter((link) => link.type === RECORD_ACTION.UPDATE);
    const downloadActions = recordLinks.filter((link) => link.type === RECORD_ACTION.DOWNLOAD);

    if (recordLinks.length === 0) {
        return <></>;
    }

    if (!showMenu) {
        return <></>;
    }
    return (
        <div className={className} data-testid="record-menu-card">
            {downloadActions.length > 0 && (
                <div>
                    <LinkSection
                        actionLinks={downloadActions}
                        heading="Download record"
                        setStage={setStage}
                    />
                </div>
            )}
            {updateActions.length > 0 && (
                <div>
                    <LinkSection
                        actionLinks={updateActions}
                        heading="Update record"
                        setStage={setStage}
                    />
                </div>
            )}
        </div>
    );
};

const LinkSection = ({ actionLinks, setStage }: SubSectionProps): React.JSX.Element => {
    return (
        <>
            {actionLinks.map((link) => (
                <LinkItem key={link.key} link={link} setStage={setStage} onClick={link.onClick} />
            ))}
        </>
    );
};

type LinkItemProps = {
    link: LGRecordActionLink;
    setStage: Dispatch<SetStateAction<LG_RECORD_STAGE>>;
    onClick: (() => void) | undefined;
};

const LinkItem = ({ link, setStage, onClick }: LinkItemProps): React.JSX.Element => {
    const navigate = useNavigate();

    if (link.href || link.stage) {
        return (
            <Link
                to="#placeholder"
                onClick={(e): void => {
                    e.preventDefault();
                    if (onClick) {
                        onClick();
                    }
                    if (link.href) navigate(link.href);
                    else if (link.stage) setStage(link.stage);
                }}
                data-testid={link.key}
            >
                {link.label}
            </Link>
        );
    } else {
        return (
            <button className="link-button" onClick={link.onClick} data-testid={link.key}>
                {link.label}
            </button>
        );
    }
};

export default RecordMenuCard;
