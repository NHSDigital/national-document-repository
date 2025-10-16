import axios from 'axios';
import { endpoints } from '../../types/generic/endpoints';
import { UserAuth } from '../../types/blocks/userAuth';

export type AuthTokenArgs = {
    baseUrl: string;
    code: string;
    state: string;
};

const getAuthToken = async ({ baseUrl, code, state }: AuthTokenArgs): Promise<UserAuth> => {
    try {
        const { data } = await axios.get(`${baseUrl}${endpoints.AUTH}`, {
            params: { code, state },
        });
        const userAuth: UserAuth = data;
        return userAuth;
    } catch (e) {
        throw e;
    }
};

export default getAuthToken;
