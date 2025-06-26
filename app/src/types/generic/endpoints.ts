export enum endpoints {
    LOGIN = '/Auth/Login',
    LOGOUT = '/Auth/Logout',
    AUTH = '/Auth/TokenRequest',

    PATIENT_SEARCH = '/SearchPatient',

    DOCUMENT_SEARCH = '/SearchDocumentReferences',
    DOCUMENT_UPLOAD = '/DocumentReference',
    DOCUMENT_PRESIGN = '/DocumentManifest',

    LLOYDGEORGE_STITCH = '/LloydGeorgeStitch',
    FEEDBACK = '/Feedback',

    FEATURE_FLAGS = '/FeatureFlags',
    VIRUS_SCAN = '/VirusScan',
    UPLOAD_CONFIRMATION = '/UploadConfirm',
    UPLOAD_DOCUMENT_STATE = '/UploadState',

    ODS_REPORT = '/OdsReport',
    MOCK_LOGIN = '/login',
}
