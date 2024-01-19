import { Roles, roleName } from '../../../support/roles';

describe('GP Workflow: GP Role rejected from accessing a non mating ODS patient on PDS', () => {
    // env vars
    const baseUrl = Cypress.config('baseUrl');
    const gpRoles = [Roles.GP_ADMIN_H85686, Roles.GP_CLINICAL_H85686];

    const workspace = Cypress.env('WORKSPACE');
    const activePatient = workspace === 'ndr-dev' ? '9730153817' : '9000000002';
    const homeUrl = '/home';

    gpRoles.forEach((role) => {
        it(
            `[Smoke] Shows that non matching ODS patient on PDS is not accessable for this  ${roleName(
                role,
            )} `,
            { tags: 'smoke' },
            () => {
                cy.smokeLogin(role);

                cy.url({ timeout: 10000 }).should('eq', baseUrl + homeUrl);
                cy.getByTestId('search-patient-btn').should('exist');
                cy.getByTestId('search-patient-btn').click();

                cy.get('#nhs-number-input').click();
                cy.get('#nhs-number-input').type(activePatient);
                cy.get('#search-submit').click();
                // Assert
                cy.get('#nhs-number-input--error-message', { timeout: 20000 }).should(
                    'include.text',
                    'Sorry, patient data not found.',
                );
            },
        );
    });
});
