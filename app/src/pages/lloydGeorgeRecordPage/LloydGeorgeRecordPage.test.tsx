import { render, screen } from '@testing-library/react';
import LloydGeorgeRecordPage from './LloydGeorgeRecordPage';
import PatientDetailsProvider from '../../providers/patientProvider/PatientProvider';
import { buildPatientDetails } from '../../helpers/test/testBuilders';
import { getFormattedDate } from '../../helpers/utils/formatDate';

jest.mock('react-router');
const mockPatientDetails = buildPatientDetails();

describe('LloydGeorgeRecordPage', () => {
    afterEach(() => {
        jest.clearAllMocks();
    });

    it('renders patient details', () => {
        const patientName = `${mockPatientDetails.givenName} ${mockPatientDetails.familyName}`;
        const dob = getFormattedDate(new Date(mockPatientDetails.birthDate));

        renderPage();

        expect(screen.getByText(patientName)).toBeInTheDocument();
        expect(screen.getByText(`Date of birth: ${dob}`)).toBeInTheDocument();
        expect(screen.getByText(/NHS number/)).toBeInTheDocument();
    });

    it('renders LG card', () => {
        renderPage();

        expect(screen.getByText('Lloyd George record')).toBeInTheDocument();
    });
});

const renderPage = () => {
    render(
        <PatientDetailsProvider patientDetails={mockPatientDetails}>
            <LloydGeorgeRecordPage />
        </PatientDetailsProvider>,
    );
};
