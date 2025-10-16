export type Props = {
    lastUpdated: string;
};

const LloydGeorgeRecordDetails = ({ lastUpdated }: Props): React.JSX.Element => {
    return (
        <div className="lloydgeorge_record-details">
            <div className="lloydgeorge_record-details_details">
                <div className="lloydgeorge_record-details_details--last-updated">
                    Last updated: {lastUpdated}
                </div>
            </div>
        </div>
    );
};

export default LloydGeorgeRecordDetails;
