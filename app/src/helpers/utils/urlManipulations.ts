export const getLastURLPath = (url: string): string | undefined => {
    return url.split('/').at(-1);
};
