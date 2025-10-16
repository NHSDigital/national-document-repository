import axios, { AxiosError } from 'axios';
import { AuthHeaders } from '../../types/blocks/authHeaders';
import { endpoints } from '../../types/generic/endpoints';

export type Args = {
    baseUrl: string;
    baseHeaders: AuthHeaders;
};

const logout = async ({ baseUrl, baseHeaders }: Args): Promise<void> => {
    const gatewayUrl = baseUrl + endpoints.LOGOUT;
    try {
        await axios.get(gatewayUrl, {
            headers: {
                ...baseHeaders,
            },
        });
    } catch (e) {
        const error = e as AxiosError;
        throw error;
    }
};

export default logout;
