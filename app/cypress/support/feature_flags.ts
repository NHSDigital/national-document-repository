export type FeatureFlags = {
    [key: string]: boolean;
};

export const defaultFeatureFlags: FeatureFlags = {
    uploadLloydGeorgeWorkflowEnabled: true,
    uploadArfWorkflowEnabled: true,
    uploadLambdaEnabled: true,
    addDocumentEnabled: true,
};
