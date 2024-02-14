import React, { useRef, useState } from 'react';
import {
    DOCUMENT_TYPE,
    DOCUMENT_UPLOAD_STATE,
    FileInputEvent,
    SetUploadDocuments,
    UploadDocument,
} from '../../../../types/pages/UploadDocumentsPage/types';
import { Button, Fieldset } from 'nhsuk-react-components';
import { useController, useForm } from 'react-hook-form';
import toFileList from '../../../../helpers/utils/toFileList';
import PatientSummary from '../../../generic/patientSummary/PatientSummary';
import DocumentInputForm from '../documentInputForm/DocumentInputForm';
import { ARFFormConfig, lloydGeorgeFormConfig } from '../../../../helpers/utils/formConfig';

interface Props {
    uploadDocuments: () => void;
    setDocuments: SetUploadDocuments;
}

function SelectStage({ uploadDocuments, setDocuments }: Props) {
    const [arfDocuments, setArfDocuments] = useState<Array<UploadDocument>>([]);
    const [lgDocuments, setLgDocuments] = useState<Array<UploadDocument>>([]);

    let arfInputRef = useRef<HTMLInputElement | null>(null);
    let lgInputRef = useRef<HTMLInputElement | null>(null);

    const mergedDocuments = [...arfDocuments, ...lgDocuments];
    const hasFileInput = mergedDocuments.length;

    const { handleSubmit, control, formState } = useForm();

    const lgController = useController(lloydGeorgeFormConfig(control));
    const arfController = useController(ARFFormConfig(control));

    const onInput = (e: FileInputEvent, docType: DOCUMENT_TYPE) => {
        const fileArray = Array.from(e.target.files ?? new FileList());
        const documentMap: Array<UploadDocument> = fileArray.map((file) => ({
            id: Math.floor(Math.random() * 1000000).toString(),
            file,
            state: DOCUMENT_UPLOAD_STATE.SELECTED,
            progress: 0,
            docType: docType,
        }));
        const isArfDoc = docType === DOCUMENT_TYPE.ARF;
        const mergeList = isArfDoc ? lgDocuments : arfDocuments;
        const docTypeList = isArfDoc ? arfDocuments : lgDocuments;
        const updatedDocList = [...documentMap, ...docTypeList];
        if (isArfDoc) {
            setArfDocuments(updatedDocList);
            arfController.field.onChange(updatedDocList);
        } else {
            setLgDocuments(updatedDocList);
            lgController.field.onChange(updatedDocList);
        }
        const updatedFileList = [...mergeList, ...updatedDocList];
        setDocuments(updatedFileList);
    };

    const onRemove = (index: number, docType: DOCUMENT_TYPE) => {
        const isArfDoc = docType === DOCUMENT_TYPE.ARF;
        const mergeList = isArfDoc ? lgDocuments : arfDocuments;
        const docTypeList = isArfDoc ? arfDocuments : lgDocuments;
        const updatedDocList = [...docTypeList.slice(0, index), ...docTypeList.slice(index + 1)];
        if (isArfDoc) {
            setArfDocuments(updatedDocList);
            if (arfInputRef.current) {
                arfInputRef.current.files = toFileList(updatedDocList);
                arfController.field.onChange(updatedDocList);
            }
        } else {
            setLgDocuments(updatedDocList);
            if (lgInputRef.current) {
                lgInputRef.current.files = toFileList(updatedDocList);
                lgController.field.onChange(updatedDocList);
            }
        }

        const updatedFileList = [...mergeList, ...updatedDocList];
        setDocuments(updatedFileList);
    };

    return (
        <>
            <form
                onSubmit={handleSubmit(uploadDocuments)}
                noValidate
                data-testid="upload-document-form"
            >
                <Fieldset.Legend headingLevel="h1" isPageHeading>
                    Upload documents
                </Fieldset.Legend>
                <PatientSummary />

                <Fieldset>
                    <h2>Electronic health records</h2>
                    <DocumentInputForm
                        showHelp
                        documents={arfDocuments}
                        onDocumentRemove={onRemove}
                        onDocumentInput={onInput}
                        formController={arfController}
                        inputRef={arfInputRef}
                        formType={DOCUMENT_TYPE.ARF}
                    />
                </Fieldset>
                <Fieldset>
                    <h2>Lloyd George records</h2>
                    <DocumentInputForm
                        documents={lgDocuments}
                        onDocumentRemove={onRemove}
                        onDocumentInput={onInput}
                        formController={lgController}
                        inputRef={lgInputRef}
                        formType={DOCUMENT_TYPE.LLOYD_GEORGE}
                    />
                </Fieldset>
                <Button
                    type="submit"
                    id="upload-button"
                    disabled={formState.isSubmitting || !hasFileInput}
                >
                    Upload
                </Button>
            </form>
        </>
    );
}

export default SelectStage;
