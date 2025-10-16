import { GlobalConfig, useConfigContext } from '../../providers/configProvider/ConfigProvider';

const useConfig = (): GlobalConfig => {
    const [config] = useConfigContext();
    return config;
};

export default useConfig;
