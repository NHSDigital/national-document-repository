import { useEffect } from 'react';

type Props = {
    pageTitle: string;
};

const useTitle = ({ pageTitle }: Props): void => {
    const serviceName = 'Access and store digital patient documents';
    useEffect(() => {
        document.title = pageTitle + ' - ' + serviceName;
    }, [pageTitle]);
};

export default useTitle;
