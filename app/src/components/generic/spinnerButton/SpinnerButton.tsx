import React from 'react';
import { Button } from 'nhsuk-react-components';

export type Props = {
    id: string;
    status: string;
    disabled?: boolean;
};

const SpinnerButton = ({ id, status, disabled }: Props) => {
    return (
        <Button
            id={id}
            aria-label={status}
            className="spinner_button"
            // role="SpinnerButton"
            disabled={disabled}
        >
            <div className="spinner_button-spinner"></div>
            <div role="status">{status}</div>
        </Button>
    );
};

export default SpinnerButton;
