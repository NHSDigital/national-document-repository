export const formatFileSize = (bytes: number): string => {
    if (bytes === 0) {
        return '0 bytes';
    }

    const units = ['bytes', 'KB', 'MB', 'GB'];
    const bytesPerKilobyte = 1024;
    const exponent = Math.floor(Math.log(bytes) / Math.log(bytesPerKilobyte));
    const divisor = Math.pow(bytesPerKilobyte, exponent);

    if (!units[exponent]) {
        throw new Error('Invalid file size');
    }

    return `${Math.round(bytes / divisor)} ${units[exponent]}`;
};

export default formatFileSize;
