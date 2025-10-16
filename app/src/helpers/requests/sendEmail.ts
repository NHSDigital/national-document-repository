import { FormData } from '../../types/pages/feedbackPage/types';
import axios, { AxiosError } from 'axios';
import { AuthHeaders } from '../../types/blocks/authHeaders';
import { endpoints } from '../../types/generic/endpoints';
type Args = {
    formData: FormData;
    baseUrl: string;
    baseHeaders: AuthHeaders;
};
const sendEmail = async ({ formData, baseUrl, baseHeaders }: Args): Promise<any> => {
    const gatewayUrl = baseUrl + endpoints.FEEDBACK;

    try {
        const { data } = await axios.post(gatewayUrl, formData, {
            headers: {
                ...baseHeaders,
            },
        });
        return data;
    } catch (e) {
        const error = e as AxiosError;
        throw error;
    }
};

export default sendEmail;
