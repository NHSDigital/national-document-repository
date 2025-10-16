import { usePatientAccessAuditContext } from '../../providers/patientAccessAuditProvider/PatientAccessAuditProvider';
import { PatientAccessAudit } from '../../types/generic/accessAudit';

const usePatientAccessAudit = (): PatientAccessAudit[] | null => {
    const [patientAccessAudit] = usePatientAccessAuditContext();
    return patientAccessAudit;
};

export default usePatientAccessAudit;
