import { REPOSITORY_ROLE } from './authRole';

export enum routes {
    HOME = '/',
    AUTH_CALLBACK = '/auth-callback',
    NOT_FOUND = '/*',
    UNAUTHORISED = '/unauthorised',
    AUTH_ERROR = '/auth-error',

    LOGOUT = '/logout',

    DOWNLOAD_SEARCH = '/search/patient',
    DOWNLOAD_VERIFY = '/search/patient/result',
    DOWNLOAD_DOCUMENTS = '/search/results',

    LLOYD_GEORGE = '/search/patient/lloyd-george-record',

    UPLOAD_SEARCH = '/search/upload',
    UPLOAD_VERIFY = '/search/upload/result',
    UPLOAD_DOCUMENTS = '/upload/submit',
}

export enum ROUTE_TYPE {
    // No guard
    PUBLIC = 0,
    // Auth route guard
    PRIVATE = 1,
    // All route guards
    APP = 2,
}

export type route = {
    page: JSX.Element;
    type: ROUTE_TYPE;
    unauthorized?: Array<REPOSITORY_ROLE>;
};
