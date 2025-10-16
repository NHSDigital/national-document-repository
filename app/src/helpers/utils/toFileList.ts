import { UploadDocument } from '../../types/pages/UploadDocumentsPage/types';

export const toFileList = (uploadDocs: Array<UploadDocument>): FileList => {
    const updatedFileList = new DataTransfer();

    uploadDocs.forEach((doc) => {
        updatedFileList.items.add(doc.file);
    });

    return updatedFileList.files;
};

export default toFileList;
