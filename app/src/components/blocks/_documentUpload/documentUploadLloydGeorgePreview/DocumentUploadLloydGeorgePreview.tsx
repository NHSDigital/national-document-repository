import { UploadDocument } from '../../../../types/pages/UploadDocumentsPage/types';
import { Dispatch, JSX, SetStateAction, useEffect, useRef, useState } from 'react';
import PdfViewer from '../../../generic/pdfViewer/PdfViewer';
import getMergedPdfBlob from '../../../../helpers/utils/pdfMerger';

type Props = {
    documents: UploadDocument[];
    setMergedPdfBlob: Dispatch<SetStateAction<Blob | undefined>>;
};

const DocumentUploadLloydGeorgePreview = ({ documents, setMergedPdfBlob }: Props): JSX.Element => {
    const [mergedPdfUrl, setMergedPdfUrl] = useState('');

    const runningRef = useRef(false);
    useEffect(() => {
        // If no docs or effect already running, ensure state cleared and exit
        if (!documents || documents.length === 0) {
            if (mergedPdfUrl) {
                setMergedPdfUrl('');
            }
            return;
        }
        if (runningRef.current) return;

        runningRef.current = true;

        const render = async (): Promise<void> => {
            const blob = await getMergedPdfBlob(documents.map((doc) => doc.file));
            setMergedPdfBlob(blob);
            const url = URL.createObjectURL(blob);
            runningRef.current = false;
            setMergedPdfUrl(url);
        };

        render().catch((err) => {
            runningRef.current = false;
            throw err;
        });
    }, [JSON.stringify(documents)]);

    return (
        <>
            {documents && mergedPdfUrl && (
                <PdfViewer customClasses={['upload-preview']} fileUrl={mergedPdfUrl} />
            )}
        </>
    );
};

export default DocumentUploadLloydGeorgePreview;
