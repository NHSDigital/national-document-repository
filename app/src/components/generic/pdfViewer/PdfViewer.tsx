type Props = {
    fileUrl: string;
    customClasses?: string[];
    customStyleSheet?: string;
};

const PdfViewer = ({ fileUrl, customClasses, customStyleSheet }: Props) => {
    return (
        <pdfjs-viewer-element
            id="pdf-viewer"
            data-testid="pdf-viewer"
            src={fileUrl}
            title="Embedded PDF Viewer"
            viewer-path="/pdfjs"
            viewer-extra-styles={customStyleSheet}
            viewer-extra-styles-urls="['/pdf-viewer.css']"
            className={customClasses?.join(' ')}
        ></pdfjs-viewer-element>
    );
};

export default PdfViewer;
