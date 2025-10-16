import { AxiosError } from 'axios';

export const isLocal =
    !import.meta.env.VITE_ENVIRONMENT || import.meta.env.VITE_ENVIRONMENT === 'local';

export const isMock = (err: AxiosError): boolean => isLocal && err.code === 'ERR_NETWORK';

export const isRunningInCypress = (): boolean => {
    //@ts-ignore
    return Boolean(window?.Cypress) || typeof vitest !== 'undefined';
};
