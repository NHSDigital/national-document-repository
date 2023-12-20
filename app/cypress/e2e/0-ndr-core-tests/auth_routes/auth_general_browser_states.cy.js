import authPayload from '../../../fixtures/requests/auth/GET_TokenRequest_GP_ADMIN.json';
import { Roles } from '../../../support/roles';

describe('Authentication & Authorisation', () => {
    const baseUrl = Cypress.config('baseUrl');

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
                cy.intercept('GET', '/Auth/Logout', {
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

    context('Unauthorised accesses checking when no user is logged in', () => {
        const unauthorisedRoutes = [
            '/search/patient',
            '/search/patient/result',
            '/search/results',
            '/search/patient/lloyd-george-record',
            '/search/upload',
            '/search/upload/result',
            '/upload/submit',
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
    });
});
