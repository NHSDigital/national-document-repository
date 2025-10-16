const LloydGeorgeSummaryDescription = (): React.JSX.Element => {
    return (
        <>
            <p>This report contains:</p>
            <ul className="ml-3">
                <li>
                    the number of Lloyd George records stored within this service for your
                    organisation
                </li>
                <li>
                    a list of the NHS numbers for each record stored in this service for your
                    organisation
                </li>
            </ul>
        </>
    );
};

export default LloydGeorgeSummaryDescription;
