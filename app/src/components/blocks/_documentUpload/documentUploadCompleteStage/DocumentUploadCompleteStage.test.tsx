import { render, waitFor, screen } from '@testing-library/react';
import DocumentUploadCompleteStage from './DocumentUploadCompleteStage';
import userEvent from '@testing-library/user-event';
import { routes } from '../../../../types/generic/routes';
import { LinkProps, MemoryRouter } from 'react-router-dom';
import { buildLgFile, buildPatientDetails } from '../../../../helpers/test/testBuilders';
import { getFormattedDate } from '../../../../helpers/utils/formatDate';
import { formatNhsNumber } from '../../../../helpers/utils/formatNhsNumber';
import usePatient from '../../../../helpers/hooks/usePatient';
import { getFormattedPatientFullName } from '../../../../helpers/utils/formatPatientFullName';
import {
    DOCUMENT_TYPE,
    DOCUMENT_UPLOAD_STATE,
    UploadDocument,
} from '../../../../types/pages/UploadDocumentsPage/types';

const mockNavigate = vi.fn();
vi.mock('../../../../helpers/hooks/usePatient');
vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return {
        ...actual,
        useNavigate: () => mockNavigate,
        Link: (props: LinkProps) => <a {...props} role="link" />,
    };
});

URL.createObjectURL = vi.fn();

const patientDetails = buildPatientDetails();

describe('DocumentUploadCompleteStage', () => {
    let documents: UploadDocument[] = [];
    beforeEach(() => {
        vi.mocked(usePatient).mockReturnValue(patientDetails);
        import.meta.env.VITE_ENVIRONMENT = 'vitest';

        documents = [
            {
                docType: DOCUMENT_TYPE.LLOYD_GEORGE,
                id: '1',
                file: buildLgFile(1),
                attempts: 0,
                state: DOCUMENT_UPLOAD_STATE.SUCCEEDED,
                numPages: 5,
                position: 1,
            },
        ];
    });
    afterEach(() => {
        vi.clearAllMocks();
    });

    it('renders', async () => {
        renderApp(documents);

        expect(
            screen.getByText('You have successfully uploaded a digital Lloyd George record for:'),
        ).toBeInTheDocument();

        const expectedFullName = getFormattedPatientFullName(patientDetails);
        expect(screen.getByTestId('patient-name').textContent).toEqual(
            'Patient name: ' + expectedFullName,
        );

        const expectedNhsNumber = formatNhsNumber(patientDetails.nhsNumber);
        expect(screen.getByTestId('nhs-number').textContent).toEqual(
            'NHS Number: ' + expectedNhsNumber,
        );

        const expectedDob = getFormattedDate(new Date(patientDetails.birthDate));
        expect(screen.getByTestId('dob').textContent).toEqual('Date of birth: ' + expectedDob);
    });

    it('should navigate to search when clicking the search link', async () => {
        delete (globalThis as any).location;
        globalThis.location = { search: '?journey=update' } as any;

        renderApp(documents);

        await userEvent.click(screen.getByTestId('search-patient-link'));

        await waitFor(async () => {
            expect(mockNavigate).toHaveBeenCalledWith(routes.SEARCH_PATIENT, { replace: true });
        });
    });

    it('should navigate to home when clicking the go to home button', async () => {
        renderApp(documents);

        await userEvent.click(screen.getByTestId('home-btn'));

        await waitFor(async () => {
            expect(mockNavigate).toHaveBeenCalledWith(routes.HOME, { replace: true });
        });
    });

    const renderApp = (documents: UploadDocument[]) => {
        render(
            <MemoryRouter>
                <DocumentUploadCompleteStage documents={documents} />,
            </MemoryRouter>,
        );
    };
});
