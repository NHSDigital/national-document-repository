import useTitle from '../../../../helpers/hooks/useTitle';
import { useNavigate } from 'react-router-dom';
import { routes } from '../../../../types/generic/routes';

const DocumentUploadInfectedStage = (): React.JSX.Element => {
    const navigate = useNavigate();
    const pageHeader = "We couldn't upload your files because we found a virus";
    useTitle({ pageTitle: pageHeader });

    return (
        <>
            <h1>{pageHeader}</h1>

            <p>One or more of your files has a virus.</p>

            <p>
                To keep patient information safe and our systems secure, we've stopped the upload.
            </p>

            <p>Contact your local IT support desk for help.</p>

            <p>
                <button
                    className="govuk-link"
                    data-testid="go-to-home-button"
                    onClick={(e) => {
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
