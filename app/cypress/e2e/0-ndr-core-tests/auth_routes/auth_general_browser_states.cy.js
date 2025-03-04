import authPayload from '../../../fixtures/requests/auth/GET_TokenRequest_GP_ADMIN.json';
import { Roles } from '../../../support/roles';
import { routes } from '../../../support/routes';
import dbItem from '../../../fixtures/dynamo-db-items/active-patient.json';
import searchPatientPayload from '../../../fixtures/requests/GET_SearchPatientLGUpload.json';

describe('Authentication & Authorisation', () => {
    const baseUrl = Cypress.config('baseUrl');
    const logoutPath = '/Auth/Logout';

    context('Session management is handled correctly', () => {
        it.skip(
            'sets session storage on login and clears session storage on logout',
            { tags: 'regression' },
            () => {
                cy.login(Roles.GP_ADMIN);

                assertSessionStorage({
                    auth: authPayload,
                    isLoggedIn: true,
                });

                // Logout
                cy.intercept('GET', logoutPath, {
                    statusCode: 200,
                }).as('logout');
                cy.getByTestId('logout-btn').click();
                cy.wait('@logout').then(() => {
                    assertSessionStorage({
                        auth: null,
                        isLoggedIn: false,
                    });
                });
            },
        );

        const assertSessionStorage = (storage) => {
            cy.getAllSessionStorage().then((result) => {
                expect(result).to.deep.equal({
                    [baseUrl]: {
                        UserSession: JSON.stringify(storage),
                    },
                });
            });
        };
    });

    context('Unauthorised access redirection', () => {
        const unauthorisedRoutes = [
            routes.home,
            routes.patientSearch,
            '/patient/verify',
            '/patient/arf',
            '/patient/lloyd-george-record',
            '/patient/lloyd-george-record/upload',
            routes.createReport,
            routes.createReportComplete,
        ];

        unauthorisedRoutes.forEach((route) => {
            it(
                'redirects logged-out user on unauthorised access to ' + route,
                { tags: 'regression' },
                () => {
                    // Visit the unauthorised route
                    cy.visit(route);

                    // Assert that the user is redirected
                    cy.url().should('equal', baseUrl + '/unauthorised');
                },
            );
        });

        it(
            'unauthorised account access is redirected to error page',
            { tags: 'regression' },
            () => {
                const authCallback = '/auth-callback';

                cy.intercept('GET', '/Auth/TokenRequest*', {
                    statusCode: 401,
                }).as('auth');
                cy.visit(authCallback);
                cy.wait('@auth');

                cy.contains('Your account cannot access this service').should('be.visible');
                cy.url().should('include', 'unauthorised-login');
                cy.title().should(
                    'eq',
                    'Unauthorised account - Access and store digital patient documents',
                );
            },
        );
    });

    context('Page refresh redirection ', () => {
        const workspace = Cypress.env('WORKSPACE');
        dbItem.FileLocation = dbItem.FileLocation.replace('{env}', workspace);

        const lloydGeorgeRecordUrl = '/patient/lloyd-george-record';
        const verifyUrl = '/patient/verify';

        it(
            'Refreshing the browser after searching for a patient will return the user to the patient search page',
            { tags: 'regression ', defaultCommandTimeout: 20000 },
            () => {
                cy.login(Roles.GP_ADMIN);
                cy.visit(routes.patientSearch);

                cy.intercept('GET', '/SearchPatient*', {
                    statusCode: 200,
                    body: searchPatientPayload,
                }).as('search');
                cy.intercept('POST', '/LloydGeorgeStitch*', {
                    statusCode: 404,
                }).as('stitch');

                cy.getByTestId('nhs-number-input').type(searchPatientPayload.nhsNumber);
                cy.getByTestId('search-submit-btn').click();

                cy.url().should('contain', verifyUrl);
                cy.get('#verify-submit').click();

                cy.url().should('contain', lloydGeorgeRecordUrl);

                cy.reload();

                cy.url().should('contain', routes.patientSearch);
            },
        );
    });
});
