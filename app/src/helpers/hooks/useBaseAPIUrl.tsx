const useBaseAPIUrl = (): string => {
    const apiEndpoint: string | undefined = import.meta.env.VITE_DOC_STORE_API_ENDPOINT;

    if (!apiEndpoint) {
        throw Error(`Document Store endpoint has not been set!`);
    }

    return apiEndpoint;
};

export default useBaseAPIUrl;
