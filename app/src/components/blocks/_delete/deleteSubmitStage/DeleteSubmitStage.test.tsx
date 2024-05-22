import { render, screen, waitFor } from '@testing-library/react';
import { buildLgSearchResult, buildPatientDetails } from '../../../../helpers/test/testBuilders';
import DeleteSubmitStage, { Props } from './DeleteSubmitStage';
import { getFormattedDate } from '../../../../helpers/utils/formatDate';
import { act } from 'react-dom/test-utils';
import userEvent from '@testing-library/user-event';
import { DOCUMENT_TYPE } from '../../../../types/pages/UploadDocumentsPage/types';
import axios from 'axios/index';
import useRole from '../../../../helpers/hooks/useRole';
import { REPOSITORY_ROLE, authorisedRoles } from '../../../../types/generic/authRole';
import { routes, routeChildren } from '../../../../types/generic/routes';
import { LG_RECORD_STAGE } from '../../../../types/blocks/lloydGeorgeStages';
import usePatient from '../../../../helpers/hooks/usePatient';
import { runAxeTest } from '../../../../helpers/test/axeTestHelper';
import { MemoryHistory, createMemoryHistory } from 'history';
import * as ReactRouter from 'react-router';

jest.mock('../../../../helpers/hooks/useConfig');
jest.mock('../deleteResultStage/DeleteResultStage', () => () => <div>Deletion complete</div>);
jest.mock('../../../../helpers/hooks/useBaseAPIHeaders');
jest.mock('../../../../helpers/hooks/useRole');
jest.mock('../../../../helpers/hooks/usePatient');
jest.mock('axios');

const mockedUseNavigate = jest.fn();

jest.mock('react-router', () => ({
    ...jest.requireActual('react-router'),
    useNavigate: () => mockedUseNavigate,
}));
jest.mock('moment', () => {
    return () => jest.requireActual('moment')('2020-01-01T00:00:00.000Z');
});

let history: MemoryHistory = createMemoryHistory({
    initialEntries: ['/'],
    initialIndex: 0,
});

const mockedUseRole = useRole as jest.Mock;
const mockedAxios = axios as jest.Mocked<typeof axios>;
const mockedUsePatient = usePatient as jest.Mock;

const mockPatientDetails = buildPatientDetails();
const mockLgSearchResult = buildLgSearchResult();

const mockSetStage = jest.fn();
const mockSetIsDeletingDocuments = jest.fn();
const mockSetDownloadStage = jest.fn();

describe('DeleteSubmitStage', () => {
    beforeEach(() => {
        history = createMemoryHistory({
            initialEntries: ['/'],
            initialIndex: 0,
        });

        process.env.REACT_APP_ENVIRONMENT = 'jest';
        mockedUsePatient.mockReturnValue(mockPatientDetails);
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    describe('Render', () => {
        it.each(authorisedRoles)(
            "renders the page with patient details when user role is '%s'",
            async (role) => {
                const patientName = `${mockPatientDetails.givenName} ${mockPatientDetails.familyName}`;
                const dob = getFormattedDate(new Date(mockPatientDetails.birthDate));
                mockedUseRole.mockReturnValue(role);

                renderComponent(DOCUMENT_TYPE.LLOYD_GEORGE, history);

                await waitFor(async () => {
                    expect(
                        screen.getByText(
                            'Are you sure you want to permanently remove this record?',
                        ),
                    ).toBeInTheDocument();
                });

                expect(screen.getByText(patientName)).toBeInTheDocument();
                expect(screen.getByText(`Date of birth: ${dob}`)).toBeInTheDocument();
                expect(screen.getByText(/NHS number/)).toBeInTheDocument();
                const yesButton = screen.getByRole('radio', { name: 'Yes' });
                expect(yesButton).toBeInTheDocument();
                expect(yesButton).not.toBeChecked();
                const noButton = screen.getByRole('radio', { name: 'No' });
                expect(noButton).toBeInTheDocument();
                expect(noButton).not.toBeChecked();
                expect(screen.getByRole('button', { name: 'Continue' })).toBeInTheDocument();
                expect(
                    screen.queryByText(
                        'Select whether you want to permanently delete these patient files',
                    ),
                ).not.toBeInTheDocument();
            },
        );

        it('renders DocumentSearchResults when No is selected and Continue clicked, when user role is GP Admin', async () => {
            mockedUseRole.mockReturnValue(REPOSITORY_ROLE.GP_ADMIN);

            renderComponent(DOCUMENT_TYPE.LLOYD_GEORGE, history);
            const noButton = screen.getByRole('radio', { name: 'No' });

            expect(noButton).not.toBeChecked();

            act(() => {
                userEvent.click(noButton);
                expect(noButton).toBeChecked();
                userEvent.click(screen.getByRole('button', { name: 'Continue' }));
            });
            expect(screen.queryByTestId('delete-error-box')).not.toBeInTheDocument();

            await waitFor(() => {
                expect(mockedUseNavigate).toHaveBeenCalledWith(routes.LLOYD_GEORGE);
            });
        });

        it('renders DocumentSearchResults when No is selected and Continue clicked, when user role is PCSE', async () => {
            mockedUseRole.mockReturnValue(REPOSITORY_ROLE.PCSE);

            renderComponent(DOCUMENT_TYPE.ALL, history);

            act(() => {
                userEvent.click(screen.getByRole('radio', { name: 'No' }));
                userEvent.click(screen.getByRole('button', { name: 'Continue' }));
            });

            await waitFor(() => {
                expect(mockedUseNavigate).toHaveBeenCalledWith(routes.ARF_OVERVIEW);
            });
        });

        it('does not render a view DocumentSearchResults when No is selected and Continue clicked, when user role is GP Clinical', async () => {
            mockedUseRole.mockReturnValue(REPOSITORY_ROLE.GP_ADMIN);

            renderComponent(DOCUMENT_TYPE.LLOYD_GEORGE, history);

            act(() => {
                userEvent.click(screen.getByRole('radio', { name: 'No' }));
                userEvent.click(screen.getByRole('button', { name: 'Continue' }));
            });

            await waitFor(() => {
                expect(mockSetStage).toHaveBeenCalledTimes(0);
            });
        });

        it('renders DeletionConfirmationStage when the Yes is selected and Continue clicked, when user role is GP_ADMIN', async () => {
            mockedUseRole.mockReturnValue(REPOSITORY_ROLE.GP_ADMIN);

            mockedAxios.delete.mockReturnValue(Promise.resolve({ status: 200, data: 'Success' }));

            renderComponent(DOCUMENT_TYPE.LLOYD_GEORGE, history);

            expect(screen.getByRole('radio', { name: 'Yes' })).toBeInTheDocument();
            expect(screen.getByRole('button', { name: 'Continue' })).toBeInTheDocument();

            act(() => {
                userEvent.click(screen.getByRole('radio', { name: 'Yes' }));
                userEvent.click(screen.getByRole('button', { name: 'Continue' }));
            });

            await waitFor(() => {
                expect(mockedUseNavigate).toHaveBeenCalledWith(
                    routeChildren.LLOYD_GEORGE_DELETE_COMPLETE,
                );
            });
        });

        it('renders DeletionConfirmationStage when the Yes is selected and Continue clicked, when user role is PCSE', async () => {
            mockedUseRole.mockReturnValue(REPOSITORY_ROLE.PCSE);

            mockedAxios.delete.mockReturnValue(Promise.resolve({ status: 200, data: 'Success' }));

            renderComponent(DOCUMENT_TYPE.LLOYD_GEORGE, history);

            expect(screen.getByRole('radio', { name: 'Yes' })).toBeInTheDocument();
            expect(screen.getByRole('button', { name: 'Continue' })).toBeInTheDocument();

            act(() => {
                userEvent.click(screen.getByRole('radio', { name: 'Yes' }));
                userEvent.click(screen.getByRole('button', { name: 'Continue' }));
            });

            await waitFor(() => {
                expect(mockedUseNavigate).toHaveBeenCalledWith(routeChildren.ARF_DELETE_COMPLETE);
            });
        });

        it('does not render DeleteResultStage when the Yes is selected, Continue clicked, and user role is GP Clinical', async () => {
            mockedAxios.delete.mockReturnValue(Promise.resolve({ status: 200, data: 'Success' }));
            mockedUseRole.mockReturnValue(REPOSITORY_ROLE.GP_CLINICAL);

            renderComponent(DOCUMENT_TYPE.LLOYD_GEORGE, history);

            expect(screen.getByRole('radio', { name: 'Yes' })).toBeInTheDocument();
            expect(screen.getByRole('button', { name: 'Continue' })).toBeInTheDocument();

            act(() => {
                userEvent.click(screen.getByRole('radio', { name: 'Yes' }));
                userEvent.click(screen.getByRole('button', { name: 'Continue' }));
            });

            await waitFor(() => {
                expect(screen.queryByText('Deletion complete')).not.toBeInTheDocument();
            });
        });

        it('renders a service error when service is down', async () => {
            const errorResponse = {
                response: {
                    status: 500,
                    data: { message: 'Client Error', err_code: 'SP_1001' },
                },
            };
            mockedAxios.delete.mockImplementation(() => Promise.reject(errorResponse));
            mockedUseRole.mockReturnValue(REPOSITORY_ROLE.PCSE);
            renderComponent(DOCUMENT_TYPE.ALL, history);

            expect(screen.getByRole('radio', { name: 'Yes' })).toBeInTheDocument();
            expect(screen.getByRole('button', { name: 'Continue' })).toBeInTheDocument();

            act(() => {
                userEvent.click(screen.getByRole('radio', { name: 'Yes' }));
                userEvent.click(screen.getByRole('button', { name: 'Continue' }));
            });

            await waitFor(() => {
                expect(
                    screen.getByText('Sorry, the service is currently unavailable.'),
                ).toBeInTheDocument();
            });

            await waitFor(() => {
                expect(mockedUseNavigate).toHaveBeenCalledWith(
                    routes.SERVER_ERROR + '?encodedError=WyJTUF8xMDAxIiwiMTU3NzgzNjgwMCJd',
                );
            });
        });

        it('renders a error box when none of the options are checked', async () => {
            mockedUseRole.mockReturnValue(REPOSITORY_ROLE.GP_ADMIN);

            renderComponent(DOCUMENT_TYPE.LLOYD_GEORGE, history);
            const noButton = screen.getByRole('radio', { name: 'No' });
            const yesButton = screen.getByRole('radio', { name: 'Yes' });

            expect(noButton).not.toBeChecked();
            expect(yesButton).not.toBeChecked();

            act(() => {
                userEvent.click(screen.getByRole('button', { name: 'Continue' }));
            });
            expect(await screen.findByText('You must select an option')).toBeInTheDocument();
            expect(
                screen.getByText(
                    'Select whether you want to permanently delete these patient files',
                ),
            ).toBeInTheDocument();
        });
    });

    describe('Accessibility', () => {
        it('pass accessibility checks at page entry point', async () => {
            mockedUseRole.mockReturnValue(REPOSITORY_ROLE.GP_ADMIN);
            renderComponent(DOCUMENT_TYPE.LLOYD_GEORGE, history);

            const results = await runAxeTest(document.body);
            expect(results).toHaveNoViolations();
        });

        it('pass accessibility checks when error box appears', async () => {
            mockedUseRole.mockReturnValue(REPOSITORY_ROLE.GP_ADMIN);
            renderComponent(DOCUMENT_TYPE.LLOYD_GEORGE, history);

            const errorResponse = {
                response: {
                    status: 400,
                    message: 'Forbidden',
                },
            };
            mockedAxios.delete.mockRejectedValueOnce(errorResponse);

            act(() => {
                userEvent.click(screen.getByRole('radio', { name: 'Yes' }));
                userEvent.click(screen.getByRole('button', { name: 'Continue' }));
            });

            await screen.findByText('Sorry, the service is currently unavailable.');

            const results = await runAxeTest(document.body);
            expect(results).toHaveNoViolations();
        });
    });
});

describe('Navigation', () => {
    it('navigates to session expire page when API call returns 403', async () => {
        const errorResponse = {
            response: {
                status: 403,
                message: 'Forbidden',
            },
        };
        mockedAxios.delete.mockImplementation(() => Promise.reject(errorResponse));
        mockedUseRole.mockReturnValue(REPOSITORY_ROLE.PCSE);

        renderComponent(DOCUMENT_TYPE.ALL, history);

        expect(screen.getByRole('radio', { name: 'Yes' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Continue' })).toBeInTheDocument();

        act(() => {
            userEvent.click(screen.getByRole('radio', { name: 'Yes' }));
            userEvent.click(screen.getByRole('button', { name: 'Continue' }));
        });

        await waitFor(() => {
            expect(mockedUseNavigate).toHaveBeenCalledWith(routes.SESSION_EXPIRED);
        });
    });
});

const renderComponent = (docType: DOCUMENT_TYPE, history: MemoryHistory) => {
    const props: Omit<Props, 'setStage' | 'setIsDeletingDocuments' | 'setDownloadStage'> = {
        numberOfFiles: mockLgSearchResult.number_of_files,
        docType,
        recordType: docType.toString(),
    };

    return render(
        <ReactRouter.Router navigator={history} location={history.location}>
            <DeleteSubmitStage
                {...props}
                setStage={mockSetStage}
                setIsDeletingDocuments={mockSetIsDeletingDocuments}
                setDownloadStage={mockSetDownloadStage}
            />
            ,
        </ReactRouter.Router>,
    );
};
