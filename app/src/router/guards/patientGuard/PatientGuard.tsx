import { useEffect, type ReactNode } from 'react';
import { routes } from '../../../types/generic/routes';
import { useNavigate } from 'react-router-dom';
import usePatient from '../../../helpers/hooks/usePatient';

type Props = {
    children: ReactNode;
};

const PatientGuard = ({ children }: Props): React.JSX.Element => {
    const patient = usePatient();
    const navigate = useNavigate();
    useEffect(() => {
        if (!patient) {
            navigate(routes.SEARCH_PATIENT);
        }
    }, [patient, navigate]);
    return <>{children}</>;
};

export default PatientGuard;
