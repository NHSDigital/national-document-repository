import { BackLink } from 'nhsuk-react-components';
import React from 'react';
import type { MouseEvent } from 'react';
import { useNavigate } from 'react-router-dom';

const BackButton = () => {
    const navigate = useNavigate();

    const onBack = (e: MouseEvent<HTMLAnchorElement>) => {
        e.preventDefault();
        navigate(-1);
    };

    return (
        <BackLink onClick={onBack} href="#">
            Go back
        </BackLink>
    );
};

export default BackButton;
