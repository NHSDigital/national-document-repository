import React, { useEffect, useState } from 'react';
import { Button, Fieldset, Radios } from 'nhsuk-react-components';
import { FieldValues, useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { routes } from '../../types/generic/routes';
import ErrorBox from '../../components/layout/errorBox/ErrorBox';
import { useSessionContext } from '../../providers/sessionProvider/SessionProvider';

function RoleSelectPage() {
    /**
     * [DEPRECATED] Removed from routing
     */
    const navigate = useNavigate();
    const [inputError, setInputError] = useState('');
    const [session, setSession] = useSessionContext();
    const { register, handleSubmit, formState, getFieldState } = useForm();
    const { ref: organisationRef, ...radioProps } = register('organisation');
    const { isDirty: isOrganisationDirty } = getFieldState('organisation', formState);

    useEffect(() => {
        if (!session.auth?.authorisation_token) {
            navigate(routes.UNAUTHORISED);
        }
    }, [session, navigate]);

    const submit = (fieldValues: FieldValues) => {
        if (!isOrganisationDirty) {
            setInputError('Select one organisation you would like to view');
            return;
        }
        setSession({
            ...session,
            isLoggedIn: true,
        });
        navigate(routes.SEARCH_PATIENT);
    };

    return (
        <div className="role-select-page-div">
            {inputError && (
                <ErrorBox
                    messageTitle={'There is a problem'}
                    messageLinkBody={inputError}
                    errorInputLink={'#select-org-input'}
                    errorBoxSummaryId={'error-box-summary'}
                />
            )}
            <form onSubmit={handleSubmit(submit)}>
                <Fieldset>
                    <Fieldset.Legend headingLevel="h1" isPageHeading>
                        Select an organisation
                    </Fieldset.Legend>
                    <Radios
                        id="select-org-input"
                        error={inputError}
                        hint="You are associated to more than one organisation, select an organisation you would like to view."
                    >
                        <Radios.Radio
                            value={'GP'}
                            inputRef={organisationRef}
                            {...radioProps}
                            id="gp-radio-button"
                        >
                            <p className="role-select-page-paragraph">GP Role</p>
                            <p>{'[A9A5A] GP Practice'}</p>
                        </Radios.Radio>
                        <Radios.Radio
                            value={'PCSE'}
                            inputRef={organisationRef}
                            {...radioProps}
                            id="pcse-radio-button"
                        >
                            <p className="role-select-page-paragraph">PCSE Role</p>
                            <p>{'[B9A5A] Primary Care Support England'}</p>
                        </Radios.Radio>
                    </Radios>
                </Fieldset>
                <Button type="submit" id="role-submit-button">
                    Continue
                </Button>
            </form>
        </div>
    );
}

export default RoleSelectPage;
