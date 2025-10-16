import { Card } from 'nhsuk-react-components';
import { Dispatch, ReactNode, SetStateAction } from 'react';
import PdfViewer from '../pdfViewer/PdfViewer';
import { LGRecordActionLink } from '../../../types/blocks/lloydGeorgeActions';
import { LG_RECORD_STAGE } from '../../../types/blocks/lloydGeorgeStages';
import RecordMenuCard from '../recordMenuCard/RecordMenuCard';

export type Props = {
    heading: string;
    fullScreenHandler: (clicked: true) => void;
    detailsElement: ReactNode;
    isFullScreen: boolean;
    pdfObjectUrl: string;
    recordLinks?: Array<LGRecordActionLink>;
    setStage?: Dispatch<SetStateAction<LG_RECORD_STAGE>>;
    showMenu?: boolean;
};

const RecordCard = ({
    heading,
    fullScreenHandler,
    detailsElement,
    isFullScreen,
    pdfObjectUrl,
    recordLinks = [],
    setStage = (): void => {},
    showMenu = false,
}: Props): React.JSX.Element => {
    const Record = (): React.JSX.Element => {
        return pdfObjectUrl ? <PdfViewer fileUrl={pdfObjectUrl} /> : <></>;
    };

    const RecordLayout = ({ children }: { children: ReactNode }): React.JSX.Element => {
        if (isFullScreen) {
            return (
                <>
                    {detailsElement}
                    {children}
                </>
            );
        } else {
            return (
                <Card className="lloydgeorge_record-stage_pdf">
                    <Card.Content
                        data-testid="pdf-card"
                        className="lloydgeorge_record-stage_pdf-content"
                    >
                        <Card.Heading
                            className="lloydgeorge_record-stage_pdf-content-label"
                            headingLevel="h2"
                            tabIndex={0}
                        >
                            {heading}
                        </Card.Heading>
                        {pdfObjectUrl && (
                            <button
                                className="lloydgeorge_record-stage_pdf-content-button link-button clickable full-screen"
                                data-testid="full-screen-btn"
                                onClick={(): void => {
                                    fullScreenHandler(true);
                                }}
                            >
                                View in full screen
                            </button>
                        )}

                        {detailsElement}

                        <RecordMenuCard
                            recordLinks={recordLinks}
                            setStage={setStage}
                            showMenu={showMenu}
                        />
                    </Card.Content>
                    <div>{children}</div>
                </Card>
            );
        }
    };
    return (
        <RecordLayout>
            <Record />
        </RecordLayout>
    );
};

export default RecordCard;
