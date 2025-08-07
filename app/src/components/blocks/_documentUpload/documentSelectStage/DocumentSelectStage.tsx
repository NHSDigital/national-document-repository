import { useRef, useState } from 'react';
import {
    DOCUMENT_TYPE,
    DOCUMENT_UPLOAD_STATE,
    FileInputEvent,
    SetUploadDocuments,
    UploadDocument,
    UploadFilesError,
} from '../../../../types/pages/UploadDocumentsPage/types';
import { v4 as uuidv4 } from 'uuid';
import BackButton from '../../../generic/backButton/BackButton';
import { useNavigate } from 'react-router-dom';
import { routeChildren, routes } from '../../../../types/generic/routes';
import useTitle from '../../../../helpers/hooks/useTitle';
import { Button, Fieldset, Table, TextInput } from 'nhsuk-react-components';
import formatFileSize from '../../../../helpers/utils/formatFileSize';
import LinkButton from '../../../generic/linkButton/LinkButton';
import { getDocument } from 'pdfjs-dist';
import PatientSummary, { PatientInfo } from '../../../generic/patientSummary/PatientSummary';
import ErrorBox from '../../../layout/errorBox/ErrorBox';
import {
    fileUploadErrorMessages,
    PDF_PARSING_ERROR_TYPE,
    UPLOAD_FILE_ERROR_TYPE,
} from '../../../../helpers/utils/fileUploadErrorMessages';

export type Props = {
    setDocuments: SetUploadDocuments;
    documents: Array<UploadDocument>;
    documentType: DOCUMENT_TYPE;
};

const DocumentSelectStage = ({ documents, setDocuments, documentType }: Props) => {
    const fileInputRef = useRef<HTMLInputElement | null>(null);
    const [noFilesSelected, setNoFilesSelected] = useState<boolean>(false);
    const scrollToRef = useRef<HTMLDivElement>(null);

    const navigate = useNavigate();

    const validateFileType = (file: File): boolean => {
        switch (documentType) {
            case DOCUMENT_TYPE.LLOYD_GEORGE:
                return file.type === 'application/pdf';
        }

        return true;
    };

    const onFileDrop = (e: React.DragEvent<HTMLDivElement>): void => {
        e.preventDefault();
        e.stopPropagation();

        let fileArray: File[] = [];
        if (e.dataTransfer.items?.length > 0) {
            [...e.dataTransfer.items].forEach((item) => {
                const file = item.getAsFile();

                if (item.kind === 'file' && file) {
                    fileArray.push(file);
                }
            });
        } else if (e.dataTransfer.files?.length > 0) {
            fileArray = [...e.dataTransfer.files];
        }

        if (fileArray) {
            void updateFileList(fileArray.filter(validateFileType));
        }
    };

    const onInput = (e: FileInputEvent): void => {
        const fileArray = Array.from(e.target.files ?? new FileList()).filter(validateFileType);

        void updateFileList(fileArray);
    };

    const updateFileList = async (fileArray: File[]): Promise<void> => {
        const documentMap = fileArray
            .filter((f) => !documents.some((d) => d.file.name === f.name))
            .map(async (file) => {
                const document: UploadDocument = {
                    id: uuidv4(),
                    file,
                    state: DOCUMENT_UPLOAD_STATE.SELECTED,
                    progress: 0,
                    docType: documentType,
                    attempts: 0,
                    numPages: 0,
                    validated: false,
                };

                const buffer = await file.arrayBuffer();

                try {
                    const pdf = await getDocument(buffer).promise;
                    await pdf.getPage(1);
                    document.numPages = pdf.numPages;
                    await pdf.destroy();
                } catch (e) {
                    const error = e as Error;
                    document.state = DOCUMENT_UPLOAD_STATE.FAILED;

                    if (error.message === PDF_PARSING_ERROR_TYPE.INVALID_PDF_STRUCTURE) {
                        document.error = UPLOAD_FILE_ERROR_TYPE.invalidPdf;
                    } else if (error.message === PDF_PARSING_ERROR_TYPE.PASSWORD_MISSING) {
                        document.error = UPLOAD_FILE_ERROR_TYPE.passwordProtected;
                    } else if (error.message === PDF_PARSING_ERROR_TYPE.EMPTY_PDF) {
                        document.error = UPLOAD_FILE_ERROR_TYPE.emptyPdf;
                    }
                }

                return document;
            });

        const docs = await Promise.all(documentMap);

        updateDocuments([...docs, ...documents]);
    };

    const onRemove = (index: number): void => {
        let updatedDocList: UploadDocument[] = [...documents];
        updatedDocList.splice(index, 1);

        updateDocuments(updatedDocList);
    };

    const updateDocuments = (docs: UploadDocument[]): void => {
        const sortedDocs = docs
            .sort((a, b) => a.file.lastModified - b.file.lastModified)
            .map((doc, index) => ({
                ...doc,
                position: index + 1,
            }));

        setNoFilesSelected(sortedDocs.length === 0);

        setDocuments(sortedDocs);
    };

    const allowedFileTypes = (): string => {
        switch (documentType) {
            case DOCUMENT_TYPE.LLOYD_GEORGE:
                return '.pdf';
        }

        return '';
    };

    const validateDocuments = (): boolean => {
        setNoFilesSelected(documents.length === 0);

        documents?.forEach((doc) => (doc.validated = true));

        setDocuments([...documents]);

        return (
            documents.length > 0 &&
            documents.every((doc) => doc.state !== DOCUMENT_UPLOAD_STATE.FAILED)
        );
    };

    const continueClicked = (): void => {
        if (!validateDocuments()) {
            scrollToRef.current?.scrollIntoView();
            return;
        }

        navigate(routeChildren.DOCUMENT_UPLOAD_SELECT_ORDER);
    };

    const DocumentRow = (document: UploadDocument, index: number) => {
        return (
            <Table.Row key={document.id} id={document.file.name}>
                <Table.Cell className={document.error ? 'error-cell' : ''}>
                    <strong>{document.file.name}</strong>
                    {document.error && (
                        <>
                            <br />
                            <span className="nhs-warning-color">
                                <strong>{fileUploadErrorMessages[document.error!].inline}</strong>
                            </span>
                        </>
                    )}
                </Table.Cell>
                <Table.Cell>{formatFileSize(document.file.size)}</Table.Cell>
                <Table.Cell>
                    <button
                        type="button"
                        aria-label={`Remove ${document.file.name} from selection`}
                        className="link-button"
                        onClick={() => {
                            onRemove(index);
                        }}
                    >
                        Remove
                    </button>
                </Table.Cell>
            </Table.Row>
        );
    };

    const pageTitle = (): string => {
        let title = 'files';

        switch (documentType) {
            case DOCUMENT_TYPE.LLOYD_GEORGE:
                title = 'Lloyd George files';
                break;
        }

        return `Choose ${title} to upload`;
    };

    useTitle({ pageTitle: pageTitle() });

    const errorDocs = () => {
        return documents.filter((doc) => doc.error && doc.validated);
    };

    const errorMessageList = (): UploadFilesError[] => {
        const errors: UploadFilesError[] = [];

        if (noFilesSelected) {
            errors.push({
                linkId: 'upload-files',
                error: UPLOAD_FILE_ERROR_TYPE.noFiles,
            });
        } else {
            errorDocs().forEach((doc) => {
                errors.push({
                    linkId: doc.file.name,
                    error: doc.error!,
                });
            });
        }

        return errors;
    };

    return (
        <>
            <BackButton toLocation={routes.VERIFY_PATIENT} dataTestid="back-button" />

            {(errorDocs().length > 0 || noFilesSelected) && (
                <ErrorBox
                    dataTestId="error-box"
                    errorBoxSummaryId="failed-document-uploads-summary-title"
                    messageTitle="There is a problem"
                    errorMessageList={errorMessageList()}
                    scrollToRef={scrollToRef}
                ></ErrorBox>
            )}

            <h1>{pageTitle()}</h1>

            <div className="nhsuk-inset-text">
                <p>Make sure that all files uploaded are for this patient only:</p>
                <PatientSummary>
                    <PatientSummary.Child item={PatientInfo.FULL_NAME} />
                    <PatientSummary.Child item={PatientInfo.NHS_NUMBER} />
                    <PatientSummary.Child item={PatientInfo.BIRTH_DATE} />
                </PatientSummary>
            </div>

            <div>
                <h2 className="nhsuk-heading-m">Before you upload</h2>
                <ul>
                    <li>you can only upload PDF files</li>
                    <li>
                        upload all the Lloyd George files you have for this patient now - you won't
                        be able to add more later
                    </li>
                    <li>
                        if there's a problem with your files during upload, you'll need to fix these
                        before continuing
                    </li>
                    <li>remove any passwords from files</li>
                </ul>
                <p>
                    Uploading may take longer if there are many files or if individual files are
                    large.
                </p>
            </div>

            <Fieldset>
                <div className={`${noFilesSelected ? 'nhsuk-form-group--error' : ''}`}>
                    <h3>Choose PDF files to upload</h3>
                    {noFilesSelected && (
                        <p className="nhsuk-error-message">
                            {fileUploadErrorMessages.noFiles.inline}
                        </p>
                    )}

                    <div
                        role="button"
                        id="upload-files"
                        tabIndex={0}
                        data-testid="dropzone"
                        onDragOver={(e) => {
                            e.preventDefault();
                        }}
                        onDrop={onFileDrop}
                        className={'lloydgeorge_drag-and-drop'}
                    >
                        <strong className="lg-input-bold">
                            Drag and drop a file or multiple files here
                        </strong>
                        <div>
                            <TextInput
                                data-testid={`button-input`}
                                type="file"
                                multiple={true}
                                hidden
                                accept={allowedFileTypes()}
                                onChange={(e: FileInputEvent) => {
                                    onInput(e);
                                    e.target.value = '';
                                }}
                                // @ts-ignore  The NHS Component library is outdated and does not allow for any reference other than a blank MutableRefObject
                                inputRef={(e: HTMLInputElement) => {
                                    fileInputRef.current = e;
                                }}
                            />
                            <Button
                                data-testid={`upload-button-input`}
                                type={'button'}
                                className={'nhsuk-button nhsuk-button--secondary bottom-margin'}
                                onClick={() => {
                                    fileInputRef.current?.click();
                                }}
                                aria-labelledby="upload-fieldset-legend"
                            >
                                Choose PDF files
                            </Button>
                        </div>
                    </div>
                </div>
            </Fieldset>
            {documents && documents.length > 0 && (
                <>
                    <Table caption="Chosen files" id="selected-documents-table">
                        <Table.Head>
                            <Table.Row>
                                <Table.Cell className="table-cell-lg-input-cell-border">
                                    <div className="div-lg-input-cell">
                                        <strong>
                                            {`${documents.length}`} file
                                            {`${documents.length === 1 ? '' : 's'}`} chosen
                                        </strong>
                                    </div>
                                </Table.Cell>
                            </Table.Row>
                            <Table.Row>
                                <Table.Cell className="word-break-keep-all">Filename</Table.Cell>
                                <Table.Cell width="20%" className="word-break-keep-all">
                                    File size
                                </Table.Cell>
                                <Table.Cell className="word-break-keep-all">Remove file</Table.Cell>
                            </Table.Row>
                        </Table.Head>

                        <Table.Body>{documents.map(DocumentRow)}</Table.Body>
                    </Table>
                    <LinkButton
                        type="button"
                        className="remove-all-button mb-5"
                        data-testid="remove-all-button"
                        onClick={() => {
                            navigate(routeChildren.DOCUMENT_UPLOAD_REMOVE_ALL);
                        }}
                    >
                        Remove all files
                    </LinkButton>
                </>
            )}
            <div className="lloydgeorge_upload-submission">
                <Button
                    type="button"
                    id="continue-button"
                    data-testid="continue-button"
                    onClick={continueClicked}
                >
                    Continue
                </Button>
            </div>
        </>
    );
};

export default DocumentSelectStage;
