describe('PCSE User all Workflows Step 1: Patient search and verify', () => {
    // env vars
    const baseUrl = Cypress.env('CYPRESS_BASE_URL') ?? 'http://localhost:3000/';
    const smokeTest = Cypress.env('CYPRESS_RUN_AS_SMOKETEST') ?? false;

    const roles = Object.freeze({
        GP: 'gp',
        PCSE: 'pcse',
    });

    const noPatientError = 400;
    const testNotFoundPatient = '1000000001';
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
        cy.visit(baseUrl);
    });

    it('(Smoke test) shows patient download screen when patient search is used by PCSE', () => {
        if (!smokeTest) {
            cy.intercept('GET', '/SearchPatient*', {
                statusCode: 200,
                body: patient,
            }).as('search');
        }
        cy.login('pcse');
        cy.get('#nhs-number-input').click();
        cy.get('#nhs-number-input').type(testPatient);

        cy.get('#search-submit').click();
        cy.wait('@search');

        cy.url().should('include', 'result');
        cy.url().should('eq', baseUrl + 'search/patient/result');
        cy.get('#gp-message').should('not.exist');

        cy.get('#verify-submit').click();

        cy.url().should('include', 'results');
        cy.url().should('eq', baseUrl + 'search/results');
    });

    it('shows the download documents page when download patient is verified', () => {
        cy.login('pcse');
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
        cy.url().should('eq', baseUrl + 'search/results');
    });

    it('(Smoke test) searches for a patient when the user enters an nhs number', () => {
        if (!smokeTest) {
            cy.intercept('GET', '/SearchPatient*', {
                statusCode: 200,
                body: patient,
            }).as('search');
        }

        cy.login('pcse');
        cy.get('#nhs-number-input').click();
        cy.get('#nhs-number-input').type(testPatient);

        cy.get('#search-submit').click();
        cy.wait('@search');

        cy.url().should('include', 'result');
        cy.url().should('eq', baseUrl + 'search/patient/result');
    });

    it('(Smoke test) searches for a patient when the user enters an nhs number with spaces', () => {
        if (!smokeTest) {
            cy.intercept('GET', '/SearchPatient*', {
                statusCode: 200,
                body: {
                    data: patient,
                },
            }).as('search');
        }

        cy.login('pcse');
        cy.get('#nhs-number-input').click();
        cy.get('#nhs-number-input').type(testPatient);

        cy.get('#search-submit').click();
        cy.wait('@search');

        cy.url().should('include', 'result');
        cy.url().should('eq', baseUrl + 'search/patient/result');
    });

    it('(Smoke test) searches for a patient when the user enters an nhs number with dashed', () => {
        if (!smokeTest) {
            cy.intercept('GET', '/SearchPatient*', {
                statusCode: 200,
                body: {
                    data: patient,
                },
            }).as('search');
        }

        cy.login('pcse');
        cy.get('#nhs-number-input').click();
        cy.get('#nhs-number-input').type(testPatient);

        cy.get('#search-submit').click();
        cy.wait('@search');

        cy.url().should('include', 'result');
        cy.url().should('eq', baseUrl + 'search/patient/result');
    });
});
