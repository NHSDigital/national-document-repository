import {
    DOCUMENT_TYPE,
    SetUploadDocuments,
    UploadDocument,
} from '../../../../types/pages/UploadDocumentsPage/types';
import { useNavigate } from 'react-router-dom';
import { routes } from '../../../../types/generic/routes';
import { Button } from 'nhsuk-react-components';
import useTitle from '../../../../helpers/hooks/useTitle';
import LinkButton from '../../../generic/linkButton/LinkButton';

type Props = {
    documents: UploadDocument[];
    setDocuments: SetUploadDocuments;
    documentType: DOCUMENT_TYPE;
};

const DocumentUploadRemoveFilesStage = ({
    documents,
    setDocuments,
    documentType,
}: Props): React.JSX.Element => {
    const navigate = useNavigate();

    const pageTitle = 'Are you sure you want to remove all selected files?';
    useTitle({ pageTitle });

    return (
        <>
            <h1>{pageTitle}</h1>
            <Button
                warning
                type="button"
                id="remove-files-button"
                data-testid="remove-files-button"
                onClick={(): void => {
                    setDocuments(documents.filter((doc) => doc.docType !== documentType));
                    navigate(routes.DOCUMENT_UPLOAD);
                }}
            >
                Yes, remove all files
            </Button>

            <LinkButton
                onClick={(): void => {
                    navigate(-1);
                }}
            >
                Cancel
            </LinkButton>
        </>
    );
};

export default DocumentUploadRemoveFilesStage;
