import { FORM_FIELDS, FormData } from '../../types/pages/feedbackPage/types';
import userEvent from '@testing-library/user-event';
import { screen } from '@testing-library/react';

export const fillInForm = async (data: Partial<FormData>): Promise<void> => {
    for (const [fieldName, value] of Object.entries(data)) {
        if (fieldName === FORM_FIELDS.HowSatisfied) {
            await userEvent.click(screen.getByRole('radio', { name: value }));
        } else {
            await userEvent.click(screen.getByTestId(fieldName));
            await userEvent.type(screen.getByTestId(fieldName), value);
        }
    }
};
