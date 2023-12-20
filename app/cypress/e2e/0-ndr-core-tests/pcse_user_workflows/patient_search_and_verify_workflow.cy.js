const { Roles } = require('../../../support/roles');

describe('PCSE Workflow: patient search and verify', () => {
    // env vars
    const baseUrl = Cypress.config('baseUrl');
    const homeUrl = '/';
    const testPatient = '9000000009';
    const patient = {
        birthDate: '1970-01-01',
        familyName: 'Default Surname',
        givenName: ['Default Given Name'],
        nhsNumber: testPatient,
        postalCode: 'AA1 1AA',
        superseded: false,
        restricted: false,
    };

    beforeEach(() => {
        cy.visit(homeUrl);
    });

    it(
        'It redirects to the patient download screen when patient search successfully by a PCSE user',
        { tags: 'regression' },
        () => {
            cy.intercept('GET', '/SearchPatient*', {
                statusCode: 200,
                body: patient,
            }).as('search');

            cy.login(Roles.PCSE);
            cy.get('#nhs-number-input').click();
            cy.get('#nhs-number-input').type(testPatient);

            cy.get('#search-submit').click();
            cy.wait('@search');

            cy.url().should('include', 'result');
            cy.url().should('eq', baseUrl + '/search/patient/result');
            cy.get('#gp-message').should('not.exist');

            cy.get('#verify-submit').click();

            cy.url().should('include', 'results');
            cy.url().should('eq', baseUrl + '/search/results');
        },
    );

    it(
        'It shows the download documents page when download patient is verified by a PCSE user',
        { tags: 'regression' },
        () => {
            cy.login(Roles.PCSE);
            cy.intercept('GET', '/SearchPatient*', {
                statusCode: 200,
                body: patient,
            }).as('search');
            cy.get('#nhs-number-input').click();
            cy.get('#nhs-number-input').type(testPatient);
            cy.get('#search-submit').click();
            cy.wait('@search');
            cy.get('#verify-submit').click();

            cy.url().should('include', 'results');
            cy.url().should('eq', baseUrl + '/search/results');
        },
    );

    it(
        'It searches for a valid patient successfully when the user enters a known nhs number by a PCSE user',
        { tags: 'regression' },
        () => {
            cy.intercept('GET', '/SearchPatient*', {
                statusCode: 200,
                body: patient,
            }).as('search');

            cy.login(Roles.PCSE);
            cy.get('#nhs-number-input').click();
            cy.get('#nhs-number-input').type(testPatient);

            cy.get('#search-submit').click();
            cy.wait('@search');

            cy.url().should('include', 'result');
            cy.url().should('eq', baseUrl + '/search/patient/result');
        },
    );

    it(
        'It searches for a valid patient successfully when the user enters a known nhs number with spaces by a PCSE user',
        { tags: 'regression' },
        () => {
            cy.intercept('GET', '/SearchPatient*', {
                statusCode: 200,
                body: {
                    data: patient,
                },
            }).as('search');

            cy.login(Roles.PCSE);
            cy.get('#nhs-number-input').click();
            cy.get('#nhs-number-input').type(testPatient);

            cy.get('#search-submit').click();
            cy.wait('@search');

            cy.url().should('include', 'result');
            cy.url().should('eq', baseUrl + '/search/patient/result');
        },
    );

    it(
        'It searches for a valid patient successfully when the user enters a known nhs number with dashes by a PCSE user',
        { tags: 'regression' },
        () => {
            cy.intercept('GET', '/SearchPatient*', {
                statusCode: 200,
                body: {
                    data: patient,
                },
            }).as('search');

            cy.login(Roles.PCSE);
            cy.get('#nhs-number-input').click();
            cy.get('#nhs-number-input').type(testPatient);

            cy.get('#search-submit').click();
            cy.wait('@search');

            cy.url().should('include', 'result');
            cy.url().should('eq', baseUrl + '/search/patient/result');
        },
    );
});
