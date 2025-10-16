import { FormGroup, Form, Button } from 'nhsuk-react-components';
import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { routes } from '../../types/generic/routes';

type LoginFormData = {
    key: string;
    odsCode: string;
    repositoryRole: string;
};

const MockLoginPage = (): React.JSX.Element => {
    const [key, setKey] = useState('');
    const [odsCode, setOdsCode] = useState('');
    const [repositoryRole, setRepositoryRole] = useState('gp_admin');
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();

    const handleSubmit = (e: React.FormEvent<HTMLFormElement>): void => {
        e.preventDefault();

        const formData: LoginFormData = { key, odsCode, repositoryRole };
        const json = JSON.stringify(formData);

        const encodedData = encodeURIComponent(json);
        const state = searchParams.get('state') as string;

        const queryParams = new URLSearchParams();
        queryParams.append('code', encodedData);
        queryParams.append('state', state);

        navigate(`${routes.AUTH_CALLBACK}?${queryParams.toString()}`);
    };

    return (
        <div className="nhsuk-main-wrapper--s">
            <div className="nhsuk-grid-row">
                <div className="nhsuk-grid-column-two-thirds">
                    <Form onSubmit={handleSubmit}>
                        <FormGroup>
                            <div className="form-label-group">
                                <div className="nhsuk-form-group position-relative">
                                    <label className="nhsuk-label" htmlFor="key">
                                        Key
                                    </label>
                                    <input
                                        className="nhsuk-input"
                                        id="key"
                                        name="key"
                                        type="password"
                                        value={key}
                                        onChange={(e): void => setKey(e.target.value)}
                                        required
                                    />
                                </div>
                            </div>
                        </FormGroup>
                        <FormGroup>
                            <div className="form-label-group">
                                <div className="nhsuk-form-group position-relative">
                                    <label className="nhsuk-label" htmlFor="odsCode">
                                        Ods Code
                                    </label>
                                    <input
                                        className="nhsuk-input"
                                        id="odsCode"
                                        name="odsCode"
                                        type="text"
                                        value={odsCode}
                                        onChange={(e): void => setOdsCode(e.target.value)}
                                        required
                                    />
                                </div>
                            </div>
                        </FormGroup>
                        <FormGroup>
                            <div className="form-label-group">
                                <div className="nhsuk-form-group position-relative">
                                    <label className="nhsuk-label" htmlFor="repositoryRole">
                                        {' '}
                                        Select Repository role
                                    </label>
                                    <select
                                        className="nhsuk-select"
                                        id="repositoryRole"
                                        name="repositoryRole"
                                        value={repositoryRole}
                                        onChange={(e): void => setRepositoryRole(e.target.value)}
                                        required
                                    >
                                        <option value="gp_admin">GP Admin</option>
                                        <option value="gp_clinical">GP Clinical</option>
                                        <option value="pcse">PCSE</option>
                                        <option value="no_role">No Role</option>
                                    </select>
                                </div>
                            </div>
                        </FormGroup>
                        <Button type="submit" id="submit-login-details">
                            Continue
                        </Button>
                    </Form>
                </div>
            </div>
        </div>
    );
};

export default MockLoginPage;
