const testPatient = '9000000009';
const patient = {
    birthDate: '1970-01-01',
    familyName: 'Default Surname',
    givenName: ['Default Given Name'],
    nhsNumber: testPatient,
    postalCode: 'AA1 1AA',
    superseded: false,
    restricted: false,
    active: true,
};

const smokeTest = Cypress.env('CYPRESS_RUN_AS_SMOKETEST') ?? false;
const baseUrl = Cypress.env('CYPRESS_BASE_URL') ?? 'http://localhost:3000/';

const forbiddenRoutes = ['search/patient', 'search/patient/result', 'search/results'];

describe('assert GP_ADMIN user has access to the GP_ADMIM workflow path', () => {
    context('session management', () => {
        it('sets session storage on login and checks starting url route', () => {
            if (!smokeTest) {
                cy.intercept('GET', '/SearchPatient*', {
                    statusCode: 200,
                    body: patient,
                }).as('search');
            }

            cy.login('GP_ADMIN');
            cy.url().should('eq', baseUrl + 'search/upload');

            cy.get('#nhs-number-input').click();
            cy.get('#nhs-number-input').type(testPatient);
            cy.get('#search-submit').click();
            cy.wait('@search');

            cy.url().should('include', 'upload');
            cy.url().should('eq', baseUrl + 'search/upload/result');

            cy.get('#verify-submit').click();

            cy.url().should('include', 'lloyd-george-record');
            cy.url().should('eq', baseUrl + 'search/patient/lloyd-george-record');
        });
    });
});

describe('assert GP ADMIM role cannot access expected forbidden routes', () => {
    context('forbidden routes', () => {
        forbiddenRoutes.forEach((forbiddenRoute) => {
            it('assert GP Admin cannot access route ' + forbiddenRoute, () => {
                cy.login('GP_ADMIN');
                cy.visit(baseUrl + forbiddenRoute);
                cy.url().should('include', 'unauthorised');
            });
        });
    });
});
