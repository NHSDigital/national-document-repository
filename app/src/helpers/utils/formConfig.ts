import { UploadDocument } from '../../types/pages/UploadDocumentsPage/types';
import { Control, FieldValues } from 'react-hook-form';

export const ARFFormConfig = (control: Control<FieldValues>) => {
    const FIVEGB = 5 * Math.pow(1024, 3);
    return {
        name: 'arf-documents',
        control,
        rules: {
            validate: {
                perFileValidation: (value?: Array<UploadDocument>) => {
                    if (Array.isArray(value)) {
                        for (let i = 0; i < value.length; i++) {
                            const currentFile = value[i].file;
                            if (currentFile.size > FIVEGB) {
                                return 'Please ensure that all files are less than 5GB in size';
                            }
                        }
                    }
                },
            },
        },
    };
};
