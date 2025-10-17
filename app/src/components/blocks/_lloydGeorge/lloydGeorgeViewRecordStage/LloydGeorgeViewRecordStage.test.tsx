// Imports
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryHistory } from 'history';
import * as ReactRouter from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi, Mock } from 'vitest';

import LloydGeorgeViewRecordStage, { Props } from './LloydGeorgeViewRecordStage';
import { routeChildren, routes } from '../../../../types/generic/routes';
import { DOWNLOAD_STAGE } from '../../../../types/generic/downloadStage';
import { REPOSITORY_ROLE } from '../../../../types/generic/authRole';
import { LG_RECORD_STAGE } from '../../../../types/blocks/lloydGeorgeStages';
import { getFormattedDate } from '../../../../helpers/utils/formatDate';

import usePatient from '../../../../helpers/hooks/usePatient';
import useRole from '../../../../helpers/hooks/useRole';
import useConfig from '../../../../helpers/hooks/useConfig';

import {
    buildPatientDetails,
    buildLgSearchResult,
    buildConfig,
} from '../../../../helpers/test/testBuilders';
import { runAxeTest } from '../../../../helpers/test/axeTestHelper';
import SessionProvider from '../../../../providers/sessionProvider/SessionProvider';

// Mocks
vi.mock('../../../../helpers/hooks/usePatient');
vi.mock('../../../../helpers/hooks/useRole');
vi.mock('../../../../helpers/hooks/useConfig');
vi.mock('../../../../helpers/hooks/useBaseAPIUrl');
vi.mock('../../../../helpers/hooks/useBaseAPIHeaders');

vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return {
        ...actual,
        Link: (props: ReactRouter.LinkProps) => <a {...props} role="link" />,
        useNavigate: () => mockNavigate,
    };
});

// Constants
const mockNavigate = vi.fn();
const mockedUsePatient = usePatient as Mock;
const mockedUseRole = useRole as Mock;
const mockUseConfig = useConfig as Mock;

const mockPdf = buildLgSearchResult();
const mockPatientDetails = buildPatientDetails();

const EMBEDDED_PDF_VIEWER_TITLE = 'Embedded PDF Viewer';

// Test helpers
const TestApp = (props: Omit<Props, 'setStage' | 'stage'>) => {
    const history = createMemoryHistory();
    return (
        <ReactRouter.Router navigator={history} location={history.location}>
            <LloydGeorgeViewRecordStage
                {...props}
                setStage={vi.fn()}
                stage={LG_RECORD_STAGE.RECORD}
            />
        </ReactRouter.Router>
    );
};

const renderComponent = (propsOverride?: Partial<Props>) => {
    const props: Omit<Props, 'setStage' | 'stage'> = {
        downloadStage: DOWNLOAD_STAGE.SUCCEEDED,
        lastUpdated: mockPdf.lastUpdated,
        refreshRecord: vi.fn(),
        pdfObjectUrl: 'http://test.com',
        showMenu: true,
        resetDocState: vi.fn(),
        ...propsOverride,
    };

    render(
        <SessionProvider sessionOverride={{ isLoggedIn: true }}>
            <TestApp {...props} />
        </SessionProvider>,
    );
};

// Test suite
describe('<LloydGeorgeViewRecordStage />', () => {
    beforeEach(() => {
        import.meta.env.VITE_ENVIRONMENT = 'vitest';
        mockedUsePatient.mockReturnValue(mockPatientDetails);
        mockUseConfig.mockReturnValue(buildConfig());
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    describe('Rendering', () => {
        it('shows LG record content and hides empty state', async () => {
            renderComponent();

            await screen.findByTitle(EMBEDDED_PDF_VIEWER_TITLE);

            expect(screen.getByText('View in full screen')).toBeInTheDocument();
            expect(screen.getByText('Lloyd George record')).toBeInTheDocument();
            expect(screen.getByText(`Last updated: ${mockPdf.lastUpdated}`)).toBeInTheDocument();
            expect(
                screen.queryByText(/This patient does not have a Lloyd George record/i),
            ).not.toBeInTheDocument();
        });

        it.each([DOWNLOAD_STAGE.INITIAL, DOWNLOAD_STAGE.PENDING, DOWNLOAD_STAGE.REFRESH])(
            'shows loading indicator for download stage: %s',
            async (stage) => {
                renderComponent({ downloadStage: stage, pdfObjectUrl: '' });

                expect(screen.getByRole('progressbar', { name: 'Loading...' })).toBeInTheDocument();
            },
        );

        it('renders empty state when there is no LG record', async () => {
            renderComponent({ downloadStage: DOWNLOAD_STAGE.NO_RECORDS });
            expect(
                screen.getByText(
                    'This patient does not have a Lloyd George record stored in this service.',
                ),
            ).toBeInTheDocument();
        });

        it('shows full screen mode with patient info', async () => {
            const patientName = `${mockPatientDetails.familyName}, ${mockPatientDetails.givenName}`;
            const dob = getFormattedDate(new Date(mockPatientDetails.birthDate));

            renderComponent();

            await screen.findByTitle(EMBEDDED_PDF_VIEWER_TITLE);
            await userEvent.click(screen.getByText('View in full screen'));

            await screen.findByText('Exit full screen');

            expect(screen.getByText(patientName)).toBeInTheDocument();
            expect(screen.getByText(dob)).toBeInTheDocument();
            expect(screen.getByText(/NHS number/)).toBeInTheDocument();
        });

        it('shows deceased tag for deceased patients', async () => {
            mockedUsePatient.mockReturnValue(buildPatientDetails({ deceased: true }));
            renderComponent();

            expect(screen.getByTestId('deceased-patient-tag')).toBeInTheDocument();
        });

        it('returns to regular view when exiting full screen', async () => {
            renderComponent();

            await userEvent.click(await screen.findByText('View in full screen'));
            await userEvent.click(await screen.findByText('Exit full screen'));

            expect(screen.getByText('View in full screen')).toBeInTheDocument();
        });

        it.each([[REPOSITORY_ROLE.GP_ADMIN], [REPOSITORY_ROLE.GP_CLINICAL]])(
            'does not show callout/button for role: %s',
            async (role) => {
                mockedUseRole.mockReturnValue(role);
                renderComponent();

                expect(screen.queryByText('Before downloading')).not.toBeInTheDocument();
                expect(
                    screen.queryByRole('button', { name: 'Download and remove files' }),
                ).not.toBeInTheDocument();
            },
        );

        it('renders Add Files button when upload is enabled and patient already has a record', () => {
            mockUseConfig.mockReturnValueOnce(
                buildConfig({}, { uploadLloydGeorgeWorkflowEnabled: true }),
            );

            renderComponent({ downloadStage: DOWNLOAD_STAGE.SUCCEEDED });

            expect(screen.getByTestId('add-files-btn')).toBeInTheDocument();
        });

        it('does not render cannot upload content when upload is disabled and patient already has a record', () => {
            renderComponent({ downloadStage: DOWNLOAD_STAGE.SUCCEEDED });

            expect(screen.queryByText('Uploading files')).not.toBeInTheDocument();
        });

        it('does not render cannot upload content when upload is enabled and patient has no record', () => {
            mockUseConfig.mockReturnValueOnce(
                buildConfig({}, { uploadLloydGeorgeWorkflowEnabled: true }),
            );
            renderComponent({ downloadStage: DOWNLOAD_STAGE.NO_RECORDS });

            expect(screen.queryByText('Uploading files')).not.toBeInTheDocument();
        });
    });

    describe('Accessibility', () => {
        it('has no violations when no record is available', async () => {
            renderComponent({ downloadStage: DOWNLOAD_STAGE.NO_RECORDS });

            await screen.findByText(/This patient does not have a Lloyd George record/i);

            const results = await runAxeTest(document.body);
            expect(results).toHaveNoViolations();
        });

        it('has no violations when record is displayed', async () => {
            renderComponent();

            await screen.findByTitle(EMBEDDED_PDF_VIEWER_TITLE);

            const results = await runAxeTest(document.body);
            expect(results).toHaveNoViolations();
        });

        it('has no violations in full screen mode', async () => {
            renderComponent();

            await userEvent.click(
                await screen.findByRole('button', { name: 'View in full screen' }),
            );

            await screen.findByText('Exit full screen');

            const results = await runAxeTest(document.body);
            expect(results).toHaveNoViolations();
        });
    });

    describe('Navigation', () => {
        it('navigates to deceased audit screen for GP user', async () => {
            mockedUseRole.mockReturnValue(REPOSITORY_ROLE.GP_ADMIN);
            mockedUsePatient.mockReturnValue(buildPatientDetails({ deceased: true }));

            renderComponent();

            await userEvent.click(screen.getByTestId('go-back-button'));

            await waitFor(() => {
                expect(mockNavigate).toHaveBeenCalledWith(
                    routeChildren.PATIENT_ACCESS_AUDIT_DECEASED,
                );
            });
        });

        it('navigates to verify patient screen for PCSE user', async () => {
            mockedUseRole.mockReturnValue(REPOSITORY_ROLE.PCSE);
            mockedUsePatient.mockReturnValue(buildPatientDetails({ deceased: true }));

            renderComponent();

            await userEvent.click(screen.getByTestId('go-back-button'));

            await waitFor(() => {
                expect(mockNavigate).toHaveBeenCalledWith(routes.VERIFY_PATIENT);
            });
        });
    });
});
