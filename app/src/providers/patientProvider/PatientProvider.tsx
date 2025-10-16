import { createContext, useContext, useState } from 'react';
import type { ReactNode, Dispatch, SetStateAction } from 'react';
import { PatientDetails } from '../../types/generic/patientDetails';

type Props = {
    patientDetails?: PatientDetails | null;
    children: ReactNode;
};

export type PatientContext = [
    PatientDetails | null,
    Dispatch<SetStateAction<PatientDetails | null>>,
];

const PatientDetailsContext = createContext<PatientContext | null>(null);

const PatientDetailsProvider = ({ children, patientDetails }: Props): React.JSX.Element => {
    const patientState: PatientContext = useState(patientDetails ?? null);

    return (
        <PatientDetailsContext.Provider value={patientState}>
            {children}
        </PatientDetailsContext.Provider>
    );
};

export default PatientDetailsProvider;
export const usePatientDetailsContext = (): PatientContext =>
    useContext(PatientDetailsContext) as PatientContext;
