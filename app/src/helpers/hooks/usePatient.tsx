import { usePatientDetailsContext } from '../../providers/patientProvider/PatientProvider';
import { PatientDetails } from '../../types/generic/patientDetails';

const usePatient = (): PatientDetails | null => {
    const [patient] = usePatientDetailsContext();
    return patient;
};

export default usePatient;
