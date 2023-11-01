import authPayload from '../../fixtures/requests/auth/GET_TokenRequest_GP_ADMIN.json';

describe('authentication & authorisation', () => {
    const baseUrl = 'http://localhost:3000';

    context('session management', () => {
        it('sets session storage on login and clears session storage on logout', () => {
            cy.login('GP_ADMIN');

            assertSessionStorage({
                auth: authPayload,
                isLoggedIn: true,
            });

            // Logout
            cy.intercept('GET', '/Auth/Logout', {
                statusCode: 200,
            }).as('logout');
            cy.getByTestId('logout-btn').click();
            cy.wait('@logout');

            assertSessionStorage({
                auth: null,
                isLoggedIn: false,
            });
        });

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

    context('route access', () => {
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
            it('redirects logged-out user on unauthorised access to ' + route, () => {
                // Visit the unauthorised route
                cy.visit(baseUrl + route);

                // Assert that the user is redirected
                cy.url().should('equal', baseUrl + '/unauthorised');
            });
        });
    });
});
