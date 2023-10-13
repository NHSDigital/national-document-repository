import viewLloydGeorgePayload from '../../fixtures/requests/GET_LloydGeorgeStitch.json';
import searchPatientPayload from '../../fixtures/requests/GET_SearchPatient.json';

const baseUrl = Cypress.env('CYPRESS_BASE_URL') ?? 'http://localhost:3000/';

describe('GP View Lloyd George Workflow', () => {
    beforeEach(() => {
        // Arrange
        navigateToLgPage();
    });

    it('allows a GP user to view the Lloyd George document of an active patient', () => {
        // Act
        cy.intercept('GET', '/LloydGeorgeStitch*', {
            statusCode: 200,
            body: viewLloydGeorgePayload,
        });
        cy.get('#verify-submit').click();

        // Assert
        assertPatientInfo();
        cy.getCy('pdf-card-heading').should('have.text', 'Lloyd George record');
        cy.getCy('pdf-card-description')
            .should('include.text', 'Last updated: 09 October 2023 at 15:41:38')
            .should('include.text', '12 files | File size: 502 KB | File format: PDF');
        cy.getCy('pdf-viewer').should('be.visible');

        // Act - open full screen view
        cy.getCy('full-screen-btn').click();

        // Assert
        assertPatientInfo();
        cy.getCy('pdf-card-description').should('not.exist');
        cy.getCy('pdf-viewer').should('be.visible');

        //  Act - close full screen view
        cy.getCy('back-link').click();

        // Assert
        cy.getCy('pdf-card-description').should('be.visible');
        cy.getCy('pdf-viewer').should('be.visible');
    });

    it('displays an empty Lloyd George card when no Lloyd George record exists for the patient', () => {
        // Act
        cy.intercept('GET', '/LloydGeorgeStitch*', {
            statusCode: 404,
        });
        cy.get('#verify-submit').click();

        // Assert
        assertPatientInfo();
        assertEmptyLloydGeorgeCard();
    });

    it('displays an empty Lloyd George card when the backend API call fails', () => {
        // Act
        cy.intercept('GET', '/LloydGeorgeStitch*', {
            statusCode: 500,
        });
        cy.get('#verify-submit').click();

        //Assert
        assertPatientInfo();
        assertEmptyLloydGeorgeCard();
    });

    const navigateToLgPage = () => {
        // login and navigate to search
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
        cy.visit(baseUrl + 'auth-callback');
        cy.wait('@auth');

        cy.get(`#gp-radio-button`).click();
        cy.get('#role-submit-button').click();

        // search patient
        cy.intercept('GET', '/SearchPatient*', {
            statusCode: 200,
            body: searchPatientPayload,
        }).as('search');
        cy.get('#nhs-number-input').type(searchPatientPayload.nhsNumber);
        cy.get('#search-submit').click();
        cy.wait('@search');

        // verify patient is active
        cy.get('#active-radio-button').click();
    };

    const assertPatientInfo = () => {
        cy.getCy('patient-name').should(
            'have.text',
            `${searchPatientPayload.givenName} ${searchPatientPayload.familyName}`,
        );
        cy.getCy('patient-nhs-number').should('have.text', `NHS number: 900 000 0009`);
        cy.getCy('patient-dob').should('have.text', `Date of birth: 01 January 1970`);
    };

    const assertEmptyLloydGeorgeCard = () => {
        cy.getCy('pdf-card-heading').should('have.text', 'Lloyd George record');
        cy.getCy('pdf-card-description').should('have.text', 'No documents are available');
    };
});
