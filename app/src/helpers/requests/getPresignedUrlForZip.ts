import axios from 'axios';
import { endpoints } from '../../types/generic/endpoints';
import { AuthHeaders } from '../../types/blocks/authHeaders';
import { DOCUMENT_TYPE } from '../../types/pages/UploadDocumentsPage/types';
import { JOB_STATUS, PollingResponse } from '../../types/generic/downloadManifestJobStatus';
import waitForSeconds from '../utils/waitForSeconds';
import { DownloadManifestError } from '../../types/generic/errors';
import { isRunningInCypress } from '../utils/isLocal';

export const DELAY_BETWEEN_POLLING_IN_SECONDS = isRunningInCypress() ? 0 : 3;

type Args = {
    nhsNumber: string;
    baseUrl: string;
    baseHeaders: AuthHeaders;
    docType?: DOCUMENT_TYPE;
    docReferences?: Array<string>;
};

type GetRequestArgs = {
    jobId: string;
    baseUrl: string;
    baseHeaders: AuthHeaders;
    nhsNumber: string;
};

const ThreePendingErrorMessage = 'Failed to initiate download';
const UnexpectedResponseMessage =
    'Got unexpected response from server when trying to download record';

const getPresignedUrlForZip = async (args: Args): Promise<string> => {
    const { baseUrl, baseHeaders, nhsNumber } = args;

    const jobId = await requestJobId(args);
    let pendingCount = 0;
    while (pendingCount < 10) {
        if (pendingCount > 0) {
            await waitForSeconds(DELAY_BETWEEN_POLLING_IN_SECONDS);
        }
        const pollingResponse = await pollForPresignedUrl({
            baseUrl,
            baseHeaders,
            jobId,
            nhsNumber,
        });

        switch (pollingResponse?.jobStatus) {
            case JOB_STATUS.COMPLETED:
                return pollingResponse.url;
            case JOB_STATUS.PROCESSING:
                continue;
            case JOB_STATUS.PENDING:
                pendingCount += 1;
                continue;
            default:
                throw new DownloadManifestError(UnexpectedResponseMessage);
        }
    }
    throw new DownloadManifestError(ThreePendingErrorMessage);
};

export const requestJobId = async ({
    nhsNumber,
    baseUrl,
    baseHeaders,
    docType = DOCUMENT_TYPE.ALL,
    docReferences,
}: Args): Promise<string> => {
    const gatewayUrl = baseUrl + endpoints.DOCUMENT_PRESIGN;

    const response = await axios.post(gatewayUrl, '', {
        headers: {
            ...baseHeaders,
        },
        params: {
            patientId: nhsNumber,
            docType: docType,
            ...(!!docReferences && { docReferences: docReferences }),
        },
        paramsSerializer: { indexes: null },
    });

    return response.data.jobId;
};

export const pollForPresignedUrl = async ({
    jobId,
    baseUrl,
    baseHeaders,
    nhsNumber,
}: GetRequestArgs): Promise<PollingResponse> => {
    const gatewayUrl = baseUrl + endpoints.DOCUMENT_PRESIGN;

    const { data } = await axios.get(gatewayUrl, {
        headers: {
            ...baseHeaders,
        },
        params: {
            jobId,
            patientId: nhsNumber,
        },
    });

    return data;
};

export default getPresignedUrlForZip;
