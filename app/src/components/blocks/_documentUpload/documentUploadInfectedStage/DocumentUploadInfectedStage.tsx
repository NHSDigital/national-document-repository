import useTitle from '../../../../helpers/hooks/useTitle';
import { useNavigate } from 'react-router-dom';
import { routes } from '../../../../types/generic/routes';

const DocumentUploadInfectedStage = (): React.JSX.Element => {
    const navigate = useNavigate();
    const pageHeader = 'Warning: we found a virus in your files';
    useTitle({ pageTitle: pageHeader });

    return (
        <>
            <h1>{pageHeader}</h1>

            <p>One or more of your files has a virus.</p>

            <p>
                To keep patient information safe and our systems secure, we've stopped the upload.
            </p>

            <p>
                Contact your local IT support desk for help immediately. Do not attempt to upload
                the files again until they have been made safe.
            </p>

            <p>
                <button
                    className="govuk-link"
                    onClick={(e): void => {
                        e.preventDefault();
                        navigate(routes.HOME, { replace: true });
                    }}
                >
                    Go to home
                </button>
            </p>
        </>
    );
};

export default DocumentUploadInfectedStage;
