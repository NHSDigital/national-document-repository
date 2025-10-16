export const formatNhsNumber = (nhsNumber: string): string => {
    return nhsNumber.slice(0, 3) + ' ' + nhsNumber.slice(3, 6) + ' ' + nhsNumber.slice(6, 10);
};
