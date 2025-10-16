import moment from 'moment';

export const unixTimestamp = (): number => {
    return moment().unix();
};
