import React from 'react';
import { Button } from 'nhsuk-react-components';

export type Props = {
    id: string;
    status: string;
    disabled?: boolean;
    dataTestId?: string;
    className?: string;
};

const SpinnerButton = ({ id, status, disabled, dataTestId, className }: Props) => {
    return (
        <Button
            id={id}
            data-testid={dataTestId}
            aria-label={status}
            className={`spinner_button ${className}`}
            disabled={disabled}
        >
            <div className="spinner_button-spinner"></div>
            <output>{status}</output>
        </Button>
    );
};

export default SpinnerButton;
