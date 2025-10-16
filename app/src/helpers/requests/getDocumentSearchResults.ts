import { AuthHeaders } from '../../types/blocks/authHeaders';
import { endpoints } from '../../types/generic/endpoints';
import { SearchResult } from '../../types/generic/searchResult';

import axios, { AxiosError } from 'axios';
import { DOCUMENT_TYPE } from '../../types/pages/UploadDocumentsPage/types';

type Args = {
    nhsNumber: string;
    baseUrl: string;
    baseHeaders: AuthHeaders;
    docType?: DOCUMENT_TYPE;
};

export type GetDocumentSearchResultsResponse = {
    data: Array<SearchResult>;
};

const getDocumentSearchResults = async ({
    nhsNumber,
    baseUrl,
    baseHeaders,
    docType = DOCUMENT_TYPE.ALL,
}: Args): Promise<Array<SearchResult>> => {
    const gatewayUrl = baseUrl + endpoints.DOCUMENT_SEARCH;

    try {
        const response: GetDocumentSearchResultsResponse = await axios.get(gatewayUrl, {
            headers: {
                ...baseHeaders,
            },
            params: {
                patientId: nhsNumber,
                docType: docType,
            },
        });
        return response?.data;
    } catch (e) {
        const error = e as AxiosError;
        throw error;
    }
};

export default getDocumentSearchResults;
