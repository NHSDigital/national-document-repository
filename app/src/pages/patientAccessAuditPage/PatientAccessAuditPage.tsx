import { routeChildren } from '../../types/generic/routes';
import { Outlet, Route, Routes } from 'react-router-dom';
import { getLastURLPath } from '../../helpers/utils/urlManipulations';
import DeceasedPatientAccessAudit from '../../components/blocks/_patientAccessAudit/deceasedPatientAccessAudit/DeceasedPatientAccessAudit';

const PatientAccessAuditPage = (): React.JSX.Element => {
    return (
        <div>
            <Routes>
                <Route index element={<></>} />
                <Route
                    path={getLastURLPath(routeChildren.PATIENT_ACCESS_AUDIT_DECEASED) + '/*'}
                    element={<DeceasedPatientAccessAudit />}
                />
            </Routes>

            <Outlet />
        </div>
    );
};

export default PatientAccessAuditPage;
