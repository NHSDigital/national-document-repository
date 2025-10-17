import { Button, Select, Table } from 'nhsuk-react-components';
import { Dispatch, JSX, SetStateAction, useEffect, useRef } from 'react';
import { FieldErrors, FieldValues, useForm } from 'react-hook-form';
import { Link } from 'react-router-dom';
import useTitle from '../../../../helpers/hooks/useTitle';
import {
    fileUploadErrorMessages,
    groupUploadErrorsByType,
    UPLOAD_FILE_ERROR_TYPE,
} from '../../../../helpers/utils/fileUploadErrorMessages';
import getMergedPdfBlob from '../../../../helpers/utils/pdfMerger';
import { getJourney, useEnhancedNavigate } from '../../../../helpers/utils/urlManipulations';
import { routeChildren, routes } from '../../../../types/generic/routes';
import { SelectRef } from '../../../../types/generic/selectRef';
import { ErrorMessageListItem } from '../../../../types/pages/genericPageErrors';
import {
    DOCUMENT_TYPE,
    SetUploadDocuments,
    UploadDocument,
} from '../../../../types/pages/UploadDocumentsPage/types';
import BackButton from '../../../generic/backButton/BackButton';
import PatientSummary, { PatientInfo } from '../../../generic/patientSummary/PatientSummary';
import ErrorBox from '../../../layout/errorBox/ErrorBox';
import DocumentUploadLloydGeorgePreview from '../documentUploadLloydGeorgePreview/DocumentUploadLloydGeorgePreview';

type Props = {
    documents: UploadDocument[];
    setDocuments: SetUploadDocuments;
    setMergedPdfBlob: Dispatch<SetStateAction<Blob | undefined>>;
    existingDocuments: UploadDocument[] | undefined;
};

type FormData = {
    [key: string]: number | null;
};

type UploadFilesError = ErrorMessageListItem<UPLOAD_FILE_ERROR_TYPE>;

const DocumentSelectOrderStage = ({
    documents,
    setDocuments,
    setMergedPdfBlob,
    existingDocuments,
}: Readonly<Props>): JSX.Element => {
    const navigate = useEnhancedNavigate();
    const journey = getJourney();
    const documentPositionKey = (documentId: string): string => {
        return `${documentId}`;
    };

    const { handleSubmit, getValues, register, unregister, formState, setValue } =
        useForm<FormData>({
            reValidateMode: 'onSubmit',
            shouldFocusError: false,
        });

    const scrollToRef = useRef<HTMLDivElement>(null);

    const pageTitle = 'What order do you want these files in?';
    useTitle({ pageTitle });

    useEffect(() => {
        scrollToRef.current?.scrollIntoView();
    }, [formState.errors]);

    const handleErrors = (_: FieldValues): void => {
        scrollToRef.current?.scrollIntoView();
    };

    useEffect(() => {
        const positionOffset = existingDocuments && existingDocuments.length > 0 ? 1 : 0;
        documents.forEach((doc, index) => {
            const key = documentPositionKey(doc.id);
            const defaultPosition =
                positionOffset > 0 ? index + 1 + positionOffset : doc.position || index + 1;
            setValue(key, defaultPosition);
        });
    }, [documents.length, existingDocuments]);

    const DocumentPositionDropdown = (
        documentId: string,
        currentPosition: number | undefined,
    ): React.JSX.Element => {
        const key = documentPositionKey(documentId);

        const positionOffset = existingDocuments && existingDocuments.length > 0 ? 1 : 0;

        const { ref: dropdownInputRef, ...dropdownProps } = register(key, {
            validate: (value, fieldValues) => {
                if (!value || +value === 0) {
                    return 'Please select a position for every document';
                }

                const otherFieldsWithSameValue = Object.keys(fieldValues).filter(
                    (k) => k !== key && Number(fieldValues[k]) === Number(value),
                );

                if (otherFieldsWithSameValue.length > 0) {
                    return fileUploadErrorMessages.duplicatePositionError.inline;
                }

                return true;
            },
            onChange: updateDocumentPositions,
        });

        const hasErr = !!formState.errors[key];
        const ariaDescribedBy = hasErr ? `${key}-error` : undefined;
        const document = documents.find((doc) => doc.id === documentId)!;

        return (
            <div className={'nhsuk-form-group ' + (hasErr ? ' nhsuk-form-group--error' : '')}>
                <fieldset
                    className="nhsuk-fieldset"
                    aria-describedby={`${document.file.name}`}
                    role="group"
                >
                    <span>
                        {hasErr && (
                            <span className="nhsuk-error-message" id={`${key}-error`}>
                                <span className="nhsuk-u-visually-hidden">Error:</span>
                                {formState.errors[key]?.message}
                            </span>
                        )}
                        <Select
                            aria-describedby={ariaDescribedBy}
                            aria-invalid={hasErr}
                            aria-label="Select document position"
                            className="nhsuk-select"
                            data-testid={key}
                            id={`${key}-select`}
                            selectRef={dropdownInputRef as SelectRef}
                            {...dropdownProps}
                        >
                            {documents.map((_, index) => {
                                const position = index + 1 + positionOffset;
                                return (
                                    <option
                                        key={`${documentId}_position_${position}`}
                                        value={position}
                                    >
                                        {position}
                                    </option>
                                );
                            })}
                        </Select>
                    </span>
                </fieldset>
            </div>
        );
    };

    const onRemove = (index: number): void => {
        let updatedDocList: UploadDocument[] = [...documents];
        const docToRemove = documents[index];
        const key = documentPositionKey(documents[index].id);
        unregister(key);

        updatedDocList.splice(index, 1);

        if (docToRemove.position) {
            updatedDocList = updatedDocList.map((doc) => {
                if (doc.position && +doc.position > +docToRemove.position!) {
                    doc.position = +doc.position - 1;
                }

                return doc;
            });
        }

        setDocuments(updatedDocList);
    };

    const updateDocumentPositions = (): void => {
        const fieldValues = getValues();

        const updatedDocuments = documents.map((doc) => ({
            ...doc,
            position: fieldValues[documentPositionKey(doc.id)]!,
        }));

        setDocuments(updatedDocuments);
    };

    const submitDocuments = (): void => {
        updateDocumentPositions();
        if (documents.length !== 1) {
            navigate.withParams(routeChildren.DOCUMENT_UPLOAD_UPLOADING);
            return;
        }
        navigate.withParams(routeChildren.DOCUMENT_UPLOAD_CONFIRMATION);
    };

    const errorMessageList = (formStateErrors: FieldErrors<FormData>): UploadFilesError[] =>
        Object.entries(formStateErrors)
            .map(([key, error]) => {
                const document = documents.find((doc) => doc.id === key);
                if (!error || !document || !error.message) {
                    return undefined;
                }
                return {
                    linkId: document.file.name,
                    error: UPLOAD_FILE_ERROR_TYPE.duplicatePositionError,
                    details: error.message,
                };
            })
            .filter((item) => item !== undefined);

    const viewPdfFile = async (file: File): Promise<void> => {
        const blob = await getMergedPdfBlob([file]);
        const url = URL.createObjectURL(blob);

        window.open(url);
    };

    type FileRowParams = {
        id: string;
        index: number;
        filename: string;
        position: number;
        ableToReposition: boolean;
        ableToRemove: boolean;
        numberOfPages?: number;
        document?: UploadDocument;
    };

    const renderFileRow = ({
        id,
        index,
        filename,
        position,
        ableToReposition,
        ableToRemove,
        document,
    }: FileRowParams): JSX.Element => {
        return (
            <Table.Row key={id}>
                <Table.Cell scope="row" className="header-cell nhsuk-table__header">
                    {id === 'existing-documents' ? <b>{filename}</b> : filename}
                </Table.Cell>
                <Table.Cell className="position-cell">
                    {ableToReposition && DocumentPositionDropdown(id, position)}
                    {!ableToReposition && position}
                </Table.Cell>
                <Table.Cell className="view-cell">
                    {document && (
                        <Link
                            to=""
                            onClick={(): Promise<void> => viewPdfFile(document.file)}
                            aria-label="Preview - opens in a new tab"
                            data-testid={`document-preview-${document.id}`}
                        >
                            View
                        </Link>
                    )}
                </Table.Cell>
                <Table.Cell className="remove-cell">
                    {ableToRemove && document && (
                        <button
                            type="button"
                            aria-label={`Remove ${document.file.name} from selection`}
                            className="link-button"
                            onClick={(): void => {
                                onRemove(index);
                            }}
                        >
                            Remove
                        </button>
                    )}
                    {!ableToRemove && '-'}
                </Table.Cell>
            </Table.Row>
        );
    };

    const renderDocumentFileRow = (document: UploadDocument, index: number): JSX.Element => {
        const positionOffset = existingDocuments && existingDocuments.length > 0 ? 1 : 0;
        return renderFileRow({
            id: document.id,
            index: index,
            filename: document.file.name,
            position: document.position || index + 1 + positionOffset,
            ableToReposition: true,
            ableToRemove: true,
            document,
        });
    };

    return (
        <>
            <BackButton />

            {Object.keys(formState.errors).length > 0 && (
                <ErrorBox
                    dataTestId="error-box"
                    errorBoxSummaryId="document-positions"
                    messageTitle="There is a problem"
                    errorMessageList={errorMessageList(formState.errors)}
                    groupErrorsFn={groupUploadErrorsByType}
                    scrollToRef={scrollToRef}
                />
            )}

            <h1>{pageTitle}</h1>

            <div className="nhsuk-inset-text">
                <p>Make sure that all files uploaded are for this patient only:</p>
                <PatientSummary>
                    <PatientSummary.Child item={PatientInfo.FULL_NAME} />
                    <PatientSummary.Child item={PatientInfo.NHS_NUMBER} />
                    <PatientSummary.Child item={PatientInfo.BIRTH_DATE} />
                </PatientSummary>
            </div>

            {journey === 'update' && (
                <>
                    <p>
                        When you upload your files, they will be added to the end of the patient's
                        existing Lloyd George record.
                    </p>

                    <p>
                        If you have added more than one file, they may not be in the correct order:
                    </p>
                    <ul>
                        <li>you cannot change the order of the existing files</li>
                        <li>
                            change the order number to put the files you've added in the order you
                            want
                        </li>
                    </ul>
                </>
            )}

            {journey !== 'update' && (
                <>
                    <p>
                        When you upload your files, they will be combined into a single PDF
                        document.
                    </p>

                    <p>If you have more than one file, they may not be in the correct order:</p>
                    <ul>
                        <li>
                            put your files in the order you need them to appear in the final
                            document by changing the position number
                        </li>
                        <li>the file marked '1' will be at the start of the final document</li>
                    </ul>
                </>
            )}

            <form
                onSubmit={handleSubmit(submitDocuments, handleErrors)}
                noValidate
                data-testid="upload-document-form"
            >
                <Table id="selected-documents-table" className="mb-5">
                    <Table.Head>
                        <Table.Row>
                            <Table.Cell className="word-break-keep-all" width="45%">
                                Filename
                            </Table.Cell>
                            <Table.Cell className="word-break-keep-all">Position</Table.Cell>
                            <Table.Cell className="word-break-keep-all">View file</Table.Cell>
                            <Table.Cell className="word-break-keep-all">Remove file</Table.Cell>
                        </Table.Row>
                    </Table.Head>

                    <Table.Body>
                        {journey === 'update' &&
                            existingDocuments &&
                            // Existing Lloyd George Record row
                            renderFileRow({
                                id: 'existing-documents',
                                index: 1,
                                filename: 'Existing Lloyd George record',
                                position: 1,
                                ableToReposition: false,
                                ableToRemove: false,
                                document: existingDocuments[0],
                            })}
                        {documents.length !== 0 && documents.map(renderDocumentFileRow)}
                        {documents.length === 0 && (
                            <Table.Row>
                                <Table.Cell colSpan={5}>
                                    <p>
                                        {journey === 'update'
                                            ? 'You have removed all additional files. Go back to '
                                            : 'You have removed all files. Go back to '}
                                        <button
                                            className="govuk-link"
                                            onClick={(e): void => {
                                                e.preventDefault();
                                                navigate.withParams(routes.DOCUMENT_UPLOAD);
                                            }}
                                        >
                                            choose files
                                        </button>
                                        {journey === 'update' ? ' to add more.' : '.'}
                                    </p>
                                </Table.Cell>
                            </Table.Row>
                        )}
                    </Table.Body>
                </Table>

                <div>
                    <h2>Preview this Lloyd George record</h2>
                    <p>
                        This shows how the final record will look when combined into a single
                        document.{' '}
                        {journey === 'update' &&
                            'Any files added will appear after the existing Lloyd George record.'}
                    </p>
                    <p>
                        Preview may take longer to load if there are many files or if individual
                        files are large.
                    </p>

                    <DocumentUploadLloydGeorgePreview
                        documents={getDocumentsForPreview()}
                        setMergedPdfBlob={setMergedPdfBlob}
                    />
                </div>
                {documents.length > 0 && (
                    <Button
                        type="submit"
                        id="form-submit"
                        data-testid="form-submit-button"
                        className="mt-4"
                        name="continue"
                    >
                        Continue
                    </Button>
                )}
            </form>
        </>
    );

    function getDocumentsForPreview(): UploadDocument[] {
        if (journey !== 'update' || !existingDocuments || existingDocuments.length === 0) {
            return documents
                .filter((doc) => doc.docType === DOCUMENT_TYPE.LLOYD_GEORGE)
                .sort((a, b) => a.position! - b.position!);
        }

        return [...existingDocuments, ...documents]
            .filter((doc) => doc.docType === DOCUMENT_TYPE.LLOYD_GEORGE)
            .sort((a, b) => a.position! - b.position!);
    }
};

export default DocumentSelectOrderStage;
