import React, { useRef, useState } from 'react';
import BackButton from '../../components/generic/backButton/BackButton';
import { formatNhsNumber } from '../../helpers/utils/formatNhsNumber';
import { getFormattedDate } from '../../helpers/utils/formatDate';
import { buildPatientDetails } from '../../helpers/test/testBuilders';
import { Input, Button, Fieldset, InsetText, Table } from 'nhsuk-react-components';
import { ReactComponent as FileSVG } from '../../styles/file-input.svg';
import {
    DOCUMENT_TYPE,
    DOCUMENT_UPLOAD_STATE,
    FileInputEvent,
    UploadDocument,
} from '../../types/pages/UploadDocumentsPage/types';
import { useController, useForm } from 'react-hook-form';
import formatFileSize from '../../helpers/utils/formatFileSize';
import { lloydGeorgeFormConfig } from '../../helpers/utils/formConfig';
import uploadDocument from '../../helpers/requests/uploadDocument';
import useBaseAPIUrl from '../../helpers/hooks/useBaseAPIUrl';
import useBaseAPIHeaders from '../../helpers/hooks/useBaseAPIHeaders';

function UploadLloydGeorgeRecordPage() {
    const patientDetails = buildPatientDetails();
    const nhsNumber: string = patientDetails?.nhsNumber || '';
    const formattedNhsNumber = formatNhsNumber(nhsNumber);
    const dob: String = patientDetails?.birthDate
        ? getFormattedDate(new Date(patientDetails.birthDate))
        : '';
    let fileInputRef = useRef<HTMLInputElement | null>(null);
    const [lgDocuments, setLgDocuments] = useState<Array<UploadDocument>>([]);

    const { handleSubmit, control, formState } = useForm();
    const lgController = useController(lloydGeorgeFormConfig(control));

    const hasFileInput = lgDocuments.length;
    const baseUrl = useBaseAPIUrl();
    const baseHeaders = useBaseAPIHeaders();

    const uploadDocuments = async () => {
        if (patientDetails) {
            await uploadDocument({
                nhsNumber: patientDetails.nhsNumber,
                setDocuments: setLgDocuments,
                documents: lgDocuments,
                baseUrl,
                baseHeaders,
            });
        }
    };
    const updateFileList = (fileArray: File[]) => {
        const documentMap: Array<UploadDocument> = fileArray.map((file) => ({
            id: Math.floor(Math.random() * 1000000).toString(),
            file,
            state: DOCUMENT_UPLOAD_STATE.SELECTED,
            progress: 0,
            docType: DOCUMENT_TYPE.LLOYD_GEORGE,
        }));
        const updatedDocList = [...documentMap, ...lgDocuments];
        setLgDocuments(updatedDocList);
        lgController.field.onChange(updatedDocList);
    };
    const onFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        let fileArray: File[] = [];
        if (e.dataTransfer.items) {
            [...e.dataTransfer.items].forEach((item) => {
                const file = item.getAsFile();

                if (item.kind === 'file' && file) {
                    fileArray.push(file);
                }
            });
        } else if (e.dataTransfer.files) {
            fileArray = [...e.dataTransfer.files];
        }
        if (fileArray) {
            updateFileList(fileArray);
        }
    };
    const onInput = (e: FileInputEvent) => {
        const fileArray = Array.from(e.target.files ?? new FileList());
        updateFileList(fileArray);
    };
    const onRemove = (index: number) => {
        let updatedDocList: UploadDocument[] = [];
        if (index >= 0) {
            updatedDocList = [...lgDocuments.slice(0, index), ...lgDocuments.slice(index + 1)];
        }
        setLgDocuments(updatedDocList);
        lgController.field.onChange(updatedDocList);
    };

    return (
        <div>
            <form
                onSubmit={handleSubmit(uploadDocuments)}
                noValidate
                data-testid="upload-document-form"
            >
                <BackButton />
                <h1>Upload a Lloyd George record</h1>
                <div id="patient-info" className="lloydgeorge_record-stage_patient-info">
                    <p data-testid="patient-name">
                        {`${patientDetails?.givenName} ${patientDetails?.familyName}`}
                    </p>
                    <p data-testid="patient-nhs-number">NHS number: {formattedNhsNumber}</p>
                    <p data-testid="patient-dob">Date of birth: {dob}</p>
                </div>
                <div>
                    <h3>Before you upload a Lloyd George patient record:</h3>
                    <ul>
                        <li>The patient details must match the record you are uploading</li>
                        <li>The patient record must be in a PDF file or multiple PDFs</li>
                        <li>Your PDF file(s) should be named in this format:</li>
                        <p style={{ fontWeight: 600, margin: 20, marginRight: 0 }}>
                            [PDFnumber]_Lloyd_George_Record_[Patient Name]_[NHS Number]_[D.O.B].PDF
                        </p>
                    </ul>
                    <InsetText style={{ maxWidth: 'unset' }}>
                        <p>For example:</p>
                        <p>1of2_Lloyd_George_Record_[Joe Bloggs]_[1234567890]_[25-12-2019].PDF</p>
                        <p>2of2_Lloyd_George_Record_[Joe Bloggs]_[1234567890]_[25-12-2019].PDF</p>
                    </InsetText>
                    <p></p>
                    <p>
                        It's recommended to upload the entire record in one go, as each file will be
                        combined together based on the file names.
                    </p>
                    <p>You will not be able to view a partially uploaded record.</p>
                </div>
                <Fieldset.Legend size="m">Select the files you wish to upload</Fieldset.Legend>
                <Fieldset>
                    <div
                        data-testid="dropzone"
                        onDragOver={(e) => {
                            e.preventDefault();
                        }}
                        onDrop={onFileDrop}
                        className={'lloydgeorge_drag-and-drop'}
                    >
                        <strong style={{ fontSize: '19px' }}>
                            Drag and drop a file or multiple files here
                        </strong>
                        <div style={{ margin: '0 2rem' }}>
                            <FileSVG />
                        </div>
                        <div>
                            <Input
                                data-testid={`button-input`}
                                type="file"
                                multiple={true}
                                hidden
                                name={lgController.field.name}
                                error={lgController.fieldState.error?.message}
                                onChange={(e: FileInputEvent) => {
                                    onInput(e);
                                    e.target.value = '';
                                }}
                                onBlur={lgController.field.onBlur}
                                // @ts-ignore  The NHS Component library is outdated and does not allow for any reference other than a blank MutableRefObject
                                inputRef={(e: HTMLInputElement) => {
                                    lgController.field.ref(e);
                                    fileInputRef.current = e;
                                }}
                            />
                            <Button
                                type={'button'}
                                style={{ background: '#4C6272', marginBottom: 0, color: 'white' }}
                                onClick={() => {
                                    fileInputRef.current?.click();
                                }}
                            >
                                Select files
                            </Button>
                        </div>
                    </div>
                </Fieldset>
                {lgDocuments && lgDocuments.length > 0 && (
                    <Table caption="Chosen files" id="selected-documents-table">
                        <Table.Head>
                            <Table.Row>
                                <Table.Cell>Filename</Table.Cell>
                                <Table.Cell>Size</Table.Cell>
                                <Table.Cell>Remove</Table.Cell>
                            </Table.Row>
                        </Table.Head>

                        <Table.Body>
                            {lgDocuments.map((document: UploadDocument, index: number) => (
                                <Table.Row key={document.id}>
                                    <Table.Cell>{document.file.name}</Table.Cell>
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
                            ))}
                        </Table.Body>
                    </Table>
                )}
                <div style={{ display: 'flex', alignItems: 'baseline' }}>
                    <Button
                        type="submit"
                        id="upload-button"
                        disabled={formState.isSubmitting || !hasFileInput}
                        onSubmit={handleSubmit(uploadDocuments)}
                    >
                        Upload
                    </Button>
                    <button
                        className={'lloydgeorge_link'}
                        type="button"
                        onClick={() => {
                            onRemove(-1);
                        }}
                        style={{}}
                    >
                        Remove all
                    </button>
                </div>
            </form>
        </div>
    );
}

export default UploadLloydGeorgeRecordPage;
