import { createContext, useContext, useState } from 'react';
import type { ReactNode, Dispatch, SetStateAction } from 'react';
import { PatientAccessAudit } from '../../types/generic/accessAudit';

type Props = {
    patientAccessAudit?: PatientAccessAudit[] | null;
    children: ReactNode;
};

export type PatientAccessAuditContext = [
    PatientAccessAudit[] | null,
    Dispatch<SetStateAction<PatientAccessAudit[] | null>>,
];

const Context = createContext<PatientAccessAuditContext | null>(null);

const PatientAccessAuditProvider = ({ children, patientAccessAudit }: Props): React.JSX.Element => {
    const patientAccessAuditState: PatientAccessAuditContext = useState(patientAccessAudit ?? null);

    return <Context.Provider value={patientAccessAuditState}>{children}</Context.Provider>;
};

export default PatientAccessAuditProvider;
export const usePatientAccessAuditContext = (): PatientAccessAuditContext =>
    useContext(Context) as PatientAccessAuditContext;
