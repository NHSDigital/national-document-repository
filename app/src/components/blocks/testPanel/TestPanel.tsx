import 'react-toggle/style.css';
import { isLocal } from '../../../helpers/utils/isLocal';
import { LocalFlags, useConfigContext } from '../../../providers/configProvider/ConfigProvider';
import { REPOSITORY_ROLE } from '../../../types/generic/authRole';
import TestToggle, { ToggleProps } from './TestToggle';

const TestPanel = (): React.JSX.Element => {
    const [config, setConfig] = useConfigContext();
    const { recordUploaded, userRole, patientIsActive, uploading, patientIsDeceased } =
        config.mockLocal;

    const updateLocalFlag = (key: keyof LocalFlags, value: boolean | REPOSITORY_ROLE): void => {
        setConfig({
            mockLocal: {
                ...config.mockLocal,
                [key]: value,
            },
            featureFlags: config.featureFlags,
        });
    };

    const roleToggles = {
        'gp-admin-toggle': {
            label: 'GP Admin',
            checked: userRole === REPOSITORY_ROLE.GP_ADMIN,
            onChange: (): void => {
                updateLocalFlag('userRole', REPOSITORY_ROLE.GP_ADMIN);
            },
        },
        'gp-clinical-toggle': {
            label: 'GP Clinical',
            checked: userRole === REPOSITORY_ROLE.GP_CLINICAL,
            onChange: (): void => {
                updateLocalFlag('userRole', REPOSITORY_ROLE.GP_CLINICAL);
            },
        },
        'pcse-toggle': {
            label: 'PCSE',
            checked: userRole === REPOSITORY_ROLE.PCSE,
            onChange: (): void => {
                updateLocalFlag('userRole', REPOSITORY_ROLE.PCSE);
            },
        },
    };

    const dataToggles = {
        'record-toggle': {
            label: 'Patient has a record',
            checked: !!recordUploaded,
            onChange: (): void => {
                updateLocalFlag('recordUploaded', !recordUploaded);
            },
        },
        'deceased-toggle': {
            label: 'Patient is deceased',
            checked: !!patientIsDeceased,
            onChange: (): void => {
                updateLocalFlag('patientIsDeceased', !patientIsDeceased);
            },
        },
        'uploading-toggle': {
            label: 'Documents upload is in progress by another user',
            checked: !!uploading,
            onChange: (): void => {
                updateLocalFlag('uploading', !uploading);
            },
        },
        'patient-active-toggle': {
            label: 'Patient is active (turn off to visit ARF workflow)',
            checked: !!patientIsActive,
            onChange: (): void => {
                updateLocalFlag('patientIsActive', !patientIsActive);
            },
        },
    };

    return (
        <div>
            <br />
            <br />
            <br />
            <h2>Test Panel</h2>
            <p>
                This section should only be displayed on a test/dev environment and should be used
                for displaying test configurations
            </p>
            <p> API endpoint: {import.meta.env.VITE_DOC_STORE_API_ENDPOINT}</p>
            <p> Image Version: {import.meta.env.VITE_IMAGE_VERSION}</p>

            {isLocal && (
                <div>
                    <h3>Local mock</h3>
                    <p>
                        This section is only available when the environment is set to local, and
                        allows for navigating to areas of the app required for developing
                    </p>
                    <h4>Role</h4>
                    <div className="div-bottom-margin">
                        {Object.entries(roleToggles).map(([id, value]) => {
                            const toggleProps: ToggleProps = {
                                id,
                                ...value,
                            };
                            return <TestToggle key={id} {...toggleProps} />;
                        })}
                    </div>
                    <h4>Data</h4>
                    {Object.entries(dataToggles).map(([id, value]) => {
                        const toggleProps: ToggleProps = {
                            id,
                            ...value,
                        };
                        return <TestToggle key={id} {...toggleProps} />;
                    })}
                </div>
            )}
        </div>
    );
};

export default TestPanel;
