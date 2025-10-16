type Props = { status: string; className?: string };

const ProgressBar = (props: Props): React.JSX.Element => {
    const { status, className, ...elementProps } = props;
    return (
        <div className={className} {...elementProps}>
            <progress className={'continuous-progress-bar'} aria-label={status} />
            <p role="status">{status}</p>
        </div>
    );
};

export default ProgressBar;
