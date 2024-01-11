const { Roles } = require('../../support/roles');

describe('Home Page', () => {
    const baseUrl = Cypress.config('baseUrl');
    const startUrl = '/';
    const homeUrl = '/home';

    beforeEach(() => {
        cy.visit(startUrl);
    });

    it('[Smoke] should visit expected URL', { tags: 'smoke' }, () => {
        cy.url().should('eq', baseUrl + startUrl);
    });

    context('Login tests', () => {
        it(
            '[Smoke] should display patient search page with navigation after user log in from homepage',
            { tags: 'smoke' },
            () => {
                cy.get('header').should('exist');

                cy.get('.nhsuk-logo__background').should('exist');
                cy.get('.nhsuk-header__transactional-service-name').should('exist');
                cy.get('.nhsuk-header__transactional-service-name')
                    .children()
                    .should('have.length', 1);
                cy.get('.nhsuk-header__transactional-service-name--link').should('exist');
                cy.get('.nhsuk-header__transactional-service-name--link').should(
                    'have.text',
                    'Access and store digital GP records',
                );
                cy.get('.nhsuk-header__navigation').should('not.exist');
                cy.get('.nhsuk-header__navigation-list').should('not.exist');

                cy.smokeLogin(Roles.GP_CLINICAL);

                cy.url().should('eq', baseUrl + homeUrl);
                cy.get('.nhsuk-header__navigation').should('exist');
                cy.get('.nhsuk-header__navigation-list').should('exist');
            },
        );
    });

    context('Logout tests', () => {
        it(
            '[Smoke] should display home page with no navigation after user log out',
            { tags: 'smoke' },
            () => {
                cy.get('header').should('exist');

                cy.get('.nhsuk-logo__background').should('exist');
                cy.get('.nhsuk-header__transactional-service-name').should('exist');
                cy.get('.nhsuk-header__transactional-service-name')
                    .children()
                    .should('have.length', 1);
                cy.get('.nhsuk-header__transactional-service-name--link').should('exist');
                cy.get('.nhsuk-header__transactional-service-name--link').should(
                    'have.text',
                    'Access and store digital GP records',
                );
                cy.get('.nhsuk-header__navigation').should('not.exist');
                cy.get('.nhsuk-header__navigation-list').should('not.exist');

                cy.smokeLogin(Roles.GP_CLINICAL);

                cy.url().should('eq', baseUrl + homeUrl);
                cy.get('.nhsuk-header__navigation').should('exist');
                cy.get('.nhsuk-header__navigation-list').should('exist');

                cy.getByTestId('logout-btn').should('exist');
                cy.getByTestId('logout-btn').click();
                cy.url({ timeout: 10000 }).should('eq', baseUrl + startUrl);

                cy.get('.nhsuk-header__navigation').should('not.exist');
                cy.get('.nhsuk-header__navigation-list').should('not.exist');
            },
        );
    });
});
