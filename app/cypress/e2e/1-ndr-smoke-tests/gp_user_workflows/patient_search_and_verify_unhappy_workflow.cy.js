import { Roles, roleName } from '../../../support/roles';
import { routes } from '../../../support/routes';

describe('GP Workflow: GP Role rejected from accessing a non mating ODS patient on PDS', () => {
    // env vars
    const baseUrl = Cypress.config('baseUrl');
    const gpRoles = [Roles.SMOKE_GP_ADMIN_H85686, Roles.SMOKE_GP_CLINICAL_H85686];

    const workspace = Cypress.env('WORKSPACE');
    const activePatient = workspace === 'ndr-dev' ? '9730153817' : '9000000002';

    gpRoles.forEach((role) => {
        it(
            `[Smoke] Shows that non matching ODS patient on PDS is not accessable for this  ${roleName(
                role,
            )} `,
            { tags: 'smoke' },
            () => {
                cy.smokeLogin(role);

                cy.url({ timeout: 10000 }).should('eq', baseUrl + routes.home);

                cy.navigateToPatientSearchPage();

                cy.get('#nhs-number-input').click();
                cy.get('#nhs-number-input').type(activePatient);
                cy.get('#search-submit').click();
                // Assert
                cy.get('#nhs-number-input--error-message', { timeout: 20000 }).should(
                    'include.text',
                    "You cannot access this patient's record",
                );
            },
        );
    });
});
