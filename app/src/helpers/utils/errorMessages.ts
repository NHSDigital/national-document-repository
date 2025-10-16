import { ErrorMessageListItem, ErrorMessageMap } from '../../types/pages/genericPageErrors';

export const getMappedErrorMessage = <T extends string>(
    error: ErrorMessageListItem<T>,
    messageMap: ErrorMessageMap<T>,
): string => {
    return messageMap[error.error].errorBox;
};

export const groupErrorsByType = <T extends string>(
    errors: ErrorMessageListItem<T>[],
    getMessage: (error: ErrorMessageListItem<T>) => string,
): Partial<Record<T, { linkIds: string[]; errorMessage: string }>> => {
    const result: Partial<Record<T, { linkIds: string[]; errorMessage: string }>> = {};

    errors.forEach((errorItem) => {
        const { error, linkId = '' } = errorItem;
        const errorMessage = getMessage(errorItem);

        if (!result[error]) {
            result[error] = { linkIds: [linkId], errorMessage };
        } else {
            result[error]!.linkIds.push(linkId);
        }
    });

    return result;
};
