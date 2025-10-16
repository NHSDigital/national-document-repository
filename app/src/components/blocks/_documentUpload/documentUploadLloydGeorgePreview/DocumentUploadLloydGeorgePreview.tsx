import { UploadDocument } from '../../../../types/pages/UploadDocumentsPage/types';
import { JSX, useEffect, useRef, useState } from 'react';
import PdfViewer from '../../../generic/pdfViewer/PdfViewer';
import getMergedPdfBlob from '../../../../helpers/utils/pdfMerger';

type Props = {
    documents: UploadDocument[];
    setMergedPdfBlob: (blob: Blob) => void;
    stitchedBlobLoaded?: (value: boolean) => void;
};

const DocumentUploadLloydGeorgePreview = ({
    documents,
    setMergedPdfBlob,
    stitchedBlobLoaded,
}: Props): JSX.Element => {
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
            if (stitchedBlobLoaded) {
                stitchedBlobLoaded(false);
            }

            const blob = await getMergedPdfBlob(documents.map((doc) => doc.file));
            setMergedPdfBlob(blob);

            const url = URL.createObjectURL(blob);
            runningRef.current = false;
            setMergedPdfUrl(url);

            if (stitchedBlobLoaded) {
                stitchedBlobLoaded(true);
            }
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
