import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ConfigProvider, { GlobalConfig, useConfigContext } from './ConfigProvider';
import { defaultFeatureFlags } from '../../helpers/requests/getFeatureFlags';
describe('SessionProvider', () => {
    beforeEach(() => {
        process.env.REACT_APP_ENVIRONMENT = 'jest';
    });
    afterEach(() => {
        jest.clearAllMocks();
    });

    it('is able to set and retrieve auth data when user has logged in', async () => {
        renderFeatureFlagsProvider();
        expect(screen.getByText('testFeature - false')).toBeInTheDocument();
        act(() => {
            userEvent.click(screen.getByText('Flag On'));
        });

        expect(screen.getByText('testFeature - true')).toBeInTheDocument();
    });

    it('is able to delete auth data when user has logged out', async () => {
        renderFeatureFlagsProvider();
        expect(screen.getByText('testFeature - true')).toBeInTheDocument();
        act(() => {
            userEvent.click(screen.getByText('Flag Off'));
        });

        expect(screen.getByText('testFeature - false')).toBeInTheDocument();
    });
});

const TestApp = () => {
    const [featureFlags, setConfig] = useConfigContext();
    const flagOn: GlobalConfig = {
        ...featureFlags,
        featureFlags: {
            ...defaultFeatureFlags,
            testFeature1: true,
        },
    };
    const flagOff: GlobalConfig = {
        ...featureFlags,
        featureFlags: {
            ...defaultFeatureFlags,
            testFeature1: false,
        },
    };
    return (
        <>
            <div>
                <h1>Actions</h1>
                <div onClick={() => setConfig(flagOn)}>Flag On</div>
                <div onClick={() => setConfig(flagOff)}>Flag Off</div>
            </div>
            <div>
                <h1>Flags</h1>
                <span>testFeature - {`${!!featureFlags.featureFlags.testFeature1}`}</span>
            </div>
        </>
    );
};

const renderFeatureFlagsProvider = () => {
    render(
        <ConfigProvider>
            <TestApp />
        </ConfigProvider>,
    );
};
