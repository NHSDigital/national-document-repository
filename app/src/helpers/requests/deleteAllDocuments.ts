import axios from 'axios';
import { AuthHeaders } from '../../types/blocks/authHeaders';
import { DOCUMENT_TYPE } from '../../types/pages/UploadDocumentsPage/types';

type Args = {
    docType: DOCUMENT_TYPE;
    nhsNumber: string;
    baseUrl: string;
    baseHeaders: AuthHeaders;
};

export type DeleteResponse = {
    data: string;
    status: number;
};
const deleteAllDocuments = async ({
    docType,
    nhsNumber,
    baseUrl,
    baseHeaders,
}: Args): Promise<DeleteResponse> => {
    const gatewayUrl = baseUrl + '/DocumentDelete';

    try {
        const response: DeleteResponse = await axios.delete(gatewayUrl, {
            headers: {
                ...baseHeaders,
            },
            params: {
                patientId: nhsNumber,
                docType,
            },
        });
        return response;
    } catch (e) {
        throw e;
    }
};

export default deleteAllDocuments;
