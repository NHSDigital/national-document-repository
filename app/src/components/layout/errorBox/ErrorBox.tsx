import { ErrorSummary } from 'nhsuk-react-components';
import { Ref, MouseEvent, JSX } from 'react';
import { ErrorMessageListItem, GroupErrors } from '../../../types/pages/genericPageErrors';

type ErrorBoxProps<T extends string> = {
    errorBoxSummaryId: string;
    messageTitle: string;
    messageBody?: string;
    messageLinkBody?: string;
    errorInputLink?: string;
    errorBody?: string;
    dataTestId?: string;
    errorOnClick?: () => void;
    errorMessageList?: ErrorMessageListItem<T>[];
    scrollToRef?: Ref<HTMLDivElement>;
    groupErrorsFn?: GroupErrors<T>;
};

type ErrorMessagesProps<T extends string> = {
    errorMessageList: ErrorMessageListItem<T>[];
    groupErrorsFn?: GroupErrors<T>;
};

const ErrorMessages = <T extends string>({
    errorMessageList,
    groupErrorsFn,
}: Readonly<ErrorMessagesProps<T>>): JSX.Element => {
    if (!groupErrorsFn) return <></>;

    const groupedErrors = groupErrorsFn(errorMessageList);

    return (
        <>
            {Object.entries(groupedErrors).map(([errorType, value]) => {
                const { linkIds, errorMessage } = value as {
                    linkIds: string[];
                    errorMessage: string;
                };

                const firstFile = linkIds[0];

                return (
                    <div key={errorType}>
                        <ErrorSummary.List>
                            <ErrorSummary.Item href={'#' + firstFile} key={errorType + firstFile}>
                                {errorMessage}
                            </ErrorSummary.Item>
                        </ErrorSummary.List>
                    </div>
                );
            })}
        </>
    );
};

const ErrorBox = <T extends string>({
    errorBoxSummaryId,
    messageTitle,
    messageBody,
    messageLinkBody,
    errorInputLink,
    errorBody,
    dataTestId,
    errorOnClick,
    errorMessageList,
    scrollToRef,
    groupErrorsFn,
}: ErrorBoxProps<T>): JSX.Element => {
    const hasInputLink = errorInputLink && messageLinkBody;
    const hasOnClick = errorOnClick && messageLinkBody;

    return (
        <div id="error-box" data-testid={dataTestId} ref={scrollToRef}>
            <ErrorSummary aria-labelledby={errorBoxSummaryId} role="alert" tabIndex={-1}>
                <ErrorSummary.Title id={errorBoxSummaryId}>{messageTitle}</ErrorSummary.Title>
                <ErrorSummary.Body>
                    <ErrorSummary.List>
                        {errorBody && (
                            <ErrorSummary.Item
                                href="#"
                                onClick={(e: MouseEvent<HTMLAnchorElement>): void => {
                                    e.preventDefault();
                                }}
                            >
                                {errorBody}
                            </ErrorSummary.Item>
                        )}

                        {messageBody && <p>{messageBody}</p>}
                        {hasInputLink && (
                            <ErrorSummary.Item href={errorInputLink}>
                                <p>{messageLinkBody}</p>
                            </ErrorSummary.Item>
                        )}
                        {hasOnClick && (
                            <ErrorSummary.Item
                                data-testid="error-box-link"
                                href={'#'}
                                onClick={(e): void => {
                                    e.preventDefault();
                                    errorOnClick();
                                }}
                            >
                                <p>{messageLinkBody}</p>
                            </ErrorSummary.Item>
                        )}
                    </ErrorSummary.List>

                    {errorMessageList && (
                        <ErrorMessages<T>
                            errorMessageList={errorMessageList}
                            groupErrorsFn={groupErrorsFn}
                        />
                    )}
                </ErrorSummary.Body>
            </ErrorSummary>
        </div>
    );
};

export default ErrorBox;
