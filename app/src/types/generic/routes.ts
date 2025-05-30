import { REPOSITORY_ROLE } from './authRole';

export enum routes {
    START = '/',
    HOME = '/home',
    AUTH_CALLBACK = '/auth-callback',
    NOT_FOUND = '/*',
    UNAUTHORISED = '/unauthorised',
    AUTH_ERROR = '/auth-error',
    UNAUTHORISED_LOGIN = '/unauthorised-login',
    SERVER_ERROR = '/server-error',
    SESSION_EXPIRED = '/session-expired',
    PRIVACY_POLICY = '/privacy-policy',
    LOGOUT = '/logout',
    FEEDBACK = '/feedback',
    SEARCH_PATIENT = '/patient/search',
    VERIFY_PATIENT = '/patient/verify',
    LLOYD_GEORGE = '/patient/lloyd-george-record',
    LLOYD_GEORGE_WILDCARD = '/patient/lloyd-george-record/*',
    ARF_OVERVIEW = '/patient/arf',
    ARF_OVERVIEW_WILDCARD = '/patient/arf/*',
    FEEDBACK_CONFIRMATION = '/feedback/confirmation',
    REPORT_DOWNLOAD = '/create-report',
    REPORT_DOWNLOAD_WILDCARD = '/create-report/*',
    PATIENT_ACCESS_AUDIT = '/patient/access-audit',
    PATIENT_ACCESS_AUDIT_WILDCARD = '/patient/access-audit/*',
    DOCUMENT_UPLOAD = '/patient/document-upload',
    DOCUMENT_UPLOAD_WILDCARD = '/patient/document-upload/*',
    MOCK_LOGIN = 'Auth/MockLogin',
    COOKIES_POLICY = '/cookies-policy',
    COOKIES_POLICY_WILDCARD = '/cookies-policy/*',
}

export enum routeChildren {
    LLOYD_GEORGE_DOWNLOAD = '/patient/lloyd-george-record/download',
    LLOYD_GEORGE_DOWNLOAD_SELECT = '/patient/lloyd-george-record/download/select',
    LLOYD_GEORGE_DOWNLOAD_IN_PROGRESS = '/patient/lloyd-george-record/download/in-progress',
    LLOYD_GEORGE_DOWNLOAD_COMPLETE = '/patient/lloyd-george-record/download/complete',
    LLOYD_GEORGE_DELETE = '/patient/lloyd-george-record/delete',
    LLOYD_GEORGE_DELETE_CONFIRMATION = '/patient/lloyd-george-record/delete/confirmation',
    LLOYD_GEORGE_DELETE_COMPLETE = '/patient/lloyd-george-record/delete/complete',
    ARF_DELETE = '/patient/arf/delete',
    ARF_DELETE_CONFIRMATION = '/patient/arf/delete/confirmation',
    ARF_DELETE_COMPLETE = '/patient/arf/delete/complete',
    REPORT_DOWNLOAD_COMPLETE = '/create-report/complete',
    PATIENT_ACCESS_AUDIT_DECEASED = '/patient/access-audit/deceased',
    DOCUMENT_UPLOAD_SELECT_ORDER = '/patient/document-upload/select-order',
    DOCUMENT_UPLOAD_REMOVE_ALL = '/patient/document-upload/remove-all',
    DOCUMENT_UPLOAD_CONFIRMATION = '/patient/document-upload/confirmation',
    DOCUMENT_UPLOAD_UPLOADING = '/patient/document-upload/in-progress',
    DOCUMENT_UPLOAD_COMPLETED = '/patient/document-upload/completed',
    DOCUMENT_UPLOAD_INFECTED = '/patient/document-upload/infected',
    COOKIES_POLICY_UPDATED = '/cookies-policy/confirmation',
}

export enum ROUTE_TYPE {
    // No guard
    PUBLIC = 0,
    // Auth route guard
    PRIVATE = 1,
    // All route guards
    PATIENT = 2,
}

export type route = {
    page: React.JSX.Element;
    type: ROUTE_TYPE;
    unauthorized?: Array<REPOSITORY_ROLE>;
    children?: React.ReactNode;
};
