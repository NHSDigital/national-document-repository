import PDFMerger from 'pdf-merger-js/browser';

const getMergedPdfBlob = async (pdfFiles: File[]): Promise<Blob> => {
    if (pdfFiles.length < 1) {
        throw Error('Cannot merge empty pdf array');
    }

    const merger = new PDFMerger();

    for (const pdf of pdfFiles) {
        let attempts = 0;

        do {
            try {
                await merger.add(pdf);

                attempts = 3;
            } catch (err) {
                attempts += 1;

                if (attempts === 3) {
                    throw err;
                }
            }
        } while (attempts < 3);
    }

    await merger.setMetadata({
        producer: 'National Document Respository',
    });

    return await merger.saveAsBlob();
};

export default getMergedPdfBlob;
