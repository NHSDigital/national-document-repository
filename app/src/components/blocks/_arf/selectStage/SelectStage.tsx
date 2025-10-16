import React, { useRef } from 'react';
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
import DocumentInputForm from '../documentInputForm/DocumentInputForm';
import { ARFFormConfig } from '../../../../helpers/utils/formConfig';
import { v4 as uuidv4 } from 'uuid';
import BackButton from '../../../generic/backButton/BackButton';
import PatientSummary from '../../../generic/patientSummary/PatientSummary';

interface Props {
    setDocuments: SetUploadDocuments;
    documents: Array<UploadDocument>;
    startUpload: () => Promise<void>;
}

const SelectStage = ({
    setDocuments,
    documents,
    startUpload,
}: Readonly<Props>): React.JSX.Element => {
    const arfInputRef = useRef<HTMLInputElement | null>(null);

    const hasFileInput = documents.length > 0;

    const { handleSubmit, control, formState, setError } = useForm();
    const arfController = useController(ARFFormConfig(control));

    const submitDocuments = async () => {
        if (!hasFileInput) {
            setError('arf-documents', { type: 'custom', message: 'Select a file to upload' });
            return;
        }

        await startUpload();
    };

    const onInput = (e: FileInputEvent, docType: DOCUMENT_TYPE) => {
        const fileArray = Array.from(e.target.files ?? new FileList());
        const newlyAddedDocuments: Array<UploadDocument> = fileArray.map((file) => ({
            id: uuidv4(),
            file,
            state: DOCUMENT_UPLOAD_STATE.SELECTED,
            progress: 0,
            docType: docType,
            attempts: 0,
        }));
        const updatedDocList = [...newlyAddedDocuments, ...documents];
        arfController.field.onChange(updatedDocList);
        setDocuments(updatedDocList);
    };

    const onRemove = (index: number, _docType: DOCUMENT_TYPE) => {
        const updatedDocList: UploadDocument[] = [
            ...documents.slice(0, index),
            ...documents.slice(index + 1),
        ];

        if (arfInputRef.current) {
            arfInputRef.current.files = toFileList(updatedDocList);
            arfController.field.onChange(updatedDocList);
        }

        setDocuments(updatedDocList);
    };

    return (
        <>
            <BackButton />
            <form
                onSubmit={handleSubmit(submitDocuments)}
                noValidate
                data-testid="upload-document-form"
            >
                <Fieldset.Legend
                    headingLevel="h1"
                    isPageHeading
                    data-testid="arf-upload-select-stage-header"
                >
                    Upload documents
                </Fieldset.Legend>
                <PatientSummary showDeceasedTag />

                <Fieldset>
                    <h2>Electronic health records</h2>
                    <DocumentInputForm
                        showHelp
                        documents={documents}
                        onDocumentRemove={onRemove}
                        onDocumentInput={onInput}
                        formController={arfController}
                        inputRef={arfInputRef}
                        formType={DOCUMENT_TYPE.ARF}
                    />
                </Fieldset>
                <Button
                    type="submit"
                    id="upload-button"
                    data-testid="arf-upload-submit-btn"
                    disabled={formState.isSubmitting}
                >
                    Upload
                </Button>
            </form>
        </>
    );
};

export default SelectStage;
