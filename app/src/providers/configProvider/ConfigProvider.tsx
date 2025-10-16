import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { Dispatch, ReactNode, SetStateAction } from 'react';
import { REPOSITORY_ROLE } from '../../types/generic/authRole';
import { FeatureFlags, defaultFeatureFlags } from '../../types/generic/featureFlags';
import { isLocal } from '../../helpers/utils/isLocal';

type SetConfigOverride = (config: GlobalConfig) => void;

type Props = {
    children: ReactNode;
    configOverride?: Partial<GlobalConfig>;
    setConfigOverride?: SetConfigOverride;
};

export type LocalFlags = {
    recordUploaded?: boolean;
    userRole?: REPOSITORY_ROLE;
    patientIsActive?: boolean;
    patientIsDeceased?: boolean;
    uploading?: boolean;
};

export type GlobalConfig = {
    featureFlags: FeatureFlags;
    mockLocal: LocalFlags;
};

export type TConfigContext = [
    GlobalConfig,
    Dispatch<SetStateAction<GlobalConfig>> | SetConfigOverride,
];

const ConfigContext = createContext<TConfigContext | null>(null);
const ConfigProvider = ({
    children,
    configOverride,
    setConfigOverride,
}: Props): React.JSX.Element => {
    const emptyConfig = useMemo(
        () => ({
            featureFlags: { ...defaultFeatureFlags, ...configOverride?.featureFlags },
            mockLocal: {
                ...configOverride?.mockLocal,
            },
        }),
        [configOverride],
    );
    const defaultMockLocals = isLocal
        ? {
              recordUploaded: true,
              patientIsActive: true,
              patientIsDeceased: false,
              userRole: REPOSITORY_ROLE.GP_ADMIN,
          }
        : null;
    const storedConfig = sessionStorage.getItem('AppConfig');
    const currentConfig: GlobalConfig = storedConfig ? JSON.parse(storedConfig) : emptyConfig;
    const [config, setConfig] = useState<GlobalConfig>({
        mockLocal: {
            ...defaultMockLocals,
            ...currentConfig.mockLocal,
            ...configOverride?.mockLocal,
        },
        featureFlags: {
            ...defaultFeatureFlags,
            ...currentConfig.featureFlags,
            ...configOverride?.featureFlags,
        },
    });

    useEffect(() => {
        sessionStorage.setItem('AppConfig', JSON.stringify(config) ?? emptyConfig);
    }, [config, emptyConfig]);

    return (
        <ConfigContext.Provider value={[config, setConfigOverride ?? setConfig]}>
            {children}
        </ConfigContext.Provider>
    );
};

export default ConfigProvider;
export const useConfigContext = (): TConfigContext => useContext(ConfigContext) as TConfigContext;
