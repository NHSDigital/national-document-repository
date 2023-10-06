describe('GP Upload Workflow Step 1: Patient search and verify', () => {
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

    const navigateToSearch = (role) => {
        cy.visit(baseUrl + 'auth-callback');
        cy.intercept('GET', '/Auth/TokenRequest*', {
            statusCode: 200,
            body: {
                organisations: [
                    {
                        org_name: 'PORTWAY LIFESTYLE CENTRE',
                        ods_code: 'A470',
                        role: 'DEV',
                    },
                ],
                authorisation_token: '111xxx222',
            },
        }).as('auth');
        cy.wait('@auth');
        cy.get(`#${role}-radio-button`).click();
        cy.get('#role-submit-button').click();
    };

    const navigateToVerify = (role) => {
        cy.visit(baseUrl + 'auth-callback');
        cy.intercept('GET', '/Auth/TokenRequest*', {
            statusCode: 200,
            body: {
                organisations: [
                    {
                        org_name: 'PORTWAY LIFESTYLE CENTRE',
                        ods_code: 'A470',
                        role: 'DEV',
                    },
                ],
                authorisation_token: '111xxx222',
            },
        }).as('auth');
        cy.intercept('GET', '/SearchPatient*', {
            statusCode: 200,
            body: patient,
        }).as('search');
        cy.wait('@auth');
        cy.get(`#${role}-radio-button`).click();
        cy.get('#role-submit-button').click();
        cy.get('#nhs-number-input').click();
        cy.get('#nhs-number-input').type(testPatient);
        cy.get('#search-submit').click();
        cy.wait('@search');
    };

    it('(Smoke test) shows patient upload screen when patient search is used by a GP  and Inactive patient radio button is selected', () => {
        navigateToSearch(roles.GP);

        if (!smokeTest) {
            cy.intercept('GET', '/SearchPatient*', {
                statusCode: 200,
                body: patient,
            }).as('search');
        }

        cy.get('#nhs-number-input').click();
        cy.get('#nhs-number-input').type(testPatient);

        cy.get('#search-submit').click();
        cy.wait('@search');

        cy.url().should('include', 'upload');
        cy.url().should('eq', baseUrl + 'search/upload/result');
        cy.get('#gp-message').should('be.visible');
        cy.get('#gp-message').should(
            'have.text',
            'Ensure these patient details match the records and attachments that you upload',
        );
        cy.get('#inactive-radio-button').click();
        cy.get('#verify-submit').click();

        cy.url().should('include', 'submit');
        cy.url().should('eq', baseUrl + 'upload/submit');
    });

    it('(Smoke test) does not show verify patient when the search finds no patient', () => {
        if (!smokeTest) {
            cy.intercept('GET', '/SearchPatient*', {
                statusCode: noPatientError,
            }).as('search');
        }

        navigateToSearch(roles.GP);
        cy.get('#nhs-number-input').click();
        cy.get('#nhs-number-input').type(testNotFoundPatient);

        cy.get('#search-submit').click();
        cy.wait('@search');

        cy.get('#nhs-number-input--error-message').should('be.visible');
        cy.get('#nhs-number-input--error-message').should(
            'have.text',
            'Error: Enter a valid patient NHS number.',
        );
        cy.get('#error-box-summary').should('be.visible');
        cy.get('#error-box-summary').should('have.text', 'There is a problem');
    });

    it('shows the upload documents page when upload patient is verified and Inactive patient radio button selected', () => {
        navigateToVerify(roles.GP);
        cy.get('#inactive-radio-button').click();
        cy.get('#verify-submit').click();

        cy.url().should('include', 'submit');
        cy.url().should('eq', baseUrl + 'upload/submit');
    });

    it("fails to search for a patient when the user doesn't enter an nhs number", () => {
        navigateToSearch(roles.GP);
        cy.get('#search-submit').click();
        cy.get('#nhs-number-input--error-message').should('be.visible');
        cy.get('#nhs-number-input--error-message').should(
            'have.text',
            "Error: Enter patient's 10 digit NHS number",
        );
    });

    it('fails to search for a patient when the user enters an invalid nhs number', () => {
        navigateToSearch(roles.GP);
        cy.get('#nhs-number-input').click();
        cy.get('#nhs-number-input').type('900');
        cy.get('#search-submit').click();
        cy.get('#nhs-number-input--error-message').should('be.visible');
        cy.get('#nhs-number-input--error-message').should(
            'have.text',
            "Error: Enter patient's 10 digit NHS number",
        );
    });
});
