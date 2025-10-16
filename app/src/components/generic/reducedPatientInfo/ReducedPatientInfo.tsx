import React from 'react';
import usePatient from '../../../helpers/hooks/usePatient';
import { formatNhsNumber } from '../../../helpers/utils/formatNhsNumber';

interface Props {
    className?: string;
}

const ReducedPatientInfo = ({ className }: Props): React.JSX.Element => {
    const patientDetails = usePatient();
    const nhsNumber: string = patientDetails?.nhsNumber ?? '';
    const formattedNhsNumber = formatNhsNumber(nhsNumber);

    return (
        <>
            <div className={className} data-testid="reduced-patient-info">
                {patientDetails?.givenName?.map((name) => `${name} `)}
                {patientDetails?.familyName}
            </div>

            <div>NHS number: {formattedNhsNumber}</div>
        </>
    );
};

export default ReducedPatientInfo;
