const { Roles } = require('../../support/roles');

describe('Feedback Page', () => {
    const baseUrl = Cypress.config('baseUrl');
    const startUrl = '/';
    const feedbackUrl = '/feedback';
    const rolesToTest = [Roles.GP_ADMIN, Roles.GP_CLINICAL, Roles.PCSE];

    const loginAndVisitFeedbackPage = (role) => {
        cy.login(role);
        cy.visit(feedbackUrl);
    };

    const fillInForm = (formData) => {
        for (const [fieldName, value] of Object.entries(formData)) {
            if (fieldName === 'howSatisfied') {
                cy.get(`.nhsuk-radios__item:has(label:contains(${value}))`)
                    .find('input[type=radio]')
                    .click();
            } else {
                cy.get(`[data-testid=${fieldName}]`).type(value);
            }
        }
    };

    rolesToTest.forEach((role) => {
        const nameOfRole = Roles[role];
        describe(`Role: ${nameOfRole}`, () => {
            it(
                'opens the feedback page when a logged in user clicks the link at phase banner',
                { tags: 'regression' },
                () => {
                    cy.login(role);

                    cy.get('.govuk-phase-banner__text a')
                        .should('exist')
                        .and('have.attr', { target: '_blank' });
                    cy.get('.govuk-phase-banner__text a')
                        // for test purpose, remove "target=_blank" as cypress not supporting multiple tabs
                        .invoke('removeAttr', 'target')
                        .click();
                    cy.url().should('eq', baseUrl + feedbackUrl);
                    cy.title().should(
                        'eq',
                        'Give feedback on this service - Access and store digital patient documents',
                    );
                },
            );

            it('displays the correct page title on feedback page', { tags: 'regression' }, () => {
                loginAndVisitFeedbackPage(role);

                cy.get('.app-homepage-content h1').should(
                    'have.text',
                    'Give feedback on this service',
                );
            });

            it(
                'blocks access to feedback page if user is not logged in',
                { tags: 'regression' },
                () => {
                    cy.visit(startUrl);
                    cy.get('.govuk-phase-banner__text a').should('not.exist');

                    cy.visit(feedbackUrl);
                    cy.url().should('eq', baseUrl + '/unauthorised');
                },
            );

            context('Submitting feedback', () => {
                it(
                    'should display a confirmation screen after user has filled in and submitted the feedback form',
                    { tags: 'regression' },
                    () => {
                        cy.intercept('POST', '/Feedback*', {
                            statusCode: 200,
                        }).as('feedback');
                        const mockInputData = {
                            feedbackContent: 'Some awesome feedback',
                            howSatisfied: 'Very satisfied',
                            respondentName: 'Jane Smith',
                            respondentEmail: 'jane_smith@fake-email-for-smoke-test.com',
                        };

                        loginAndVisitFeedbackPage(role);
                        fillInForm(mockInputData);

                        cy.get('#submit-feedback').click();
                        cy.wait('@feedback');
                        cy.get('.app-homepage-content h1', { timeout: 5000 }).should(
                            'have.text',
                            'We’ve received your feedback',
                        );
                        cy.title().should(
                            'eq',
                            'Feedback sent - Access and store digital patient documents',
                        );
                    },
                );

                it(
                    'should allow user submit the form without filling in the name and email',
                    { tags: 'regression' },
                    () => {
                        cy.intercept('POST', '/Feedback*', {
                            statusCode: 200,
                        }).as('feedback');
                        const mockInputData = {
                            feedbackContent: 'Some awesome feedback',
                            howSatisfied: 'Satisfied',
                        };

                        loginAndVisitFeedbackPage(role);
                        fillInForm(mockInputData);

                        cy.get('#submit-feedback').click();
                        cy.wait('@feedback');
                        cy.get('.app-homepage-content h1', { timeout: 5000 }).should(
                            'have.text',
                            'We’ve received your feedback',
                        );
                    },
                );

                it(
                    'should display error messages when user try to submit a blank form',
                    { tags: 'regression' },
                    () => {
                        loginAndVisitFeedbackPage(role);
                        cy.get('#submit-feedback').click();

                        cy.get('.nhsuk-error-message')
                            .should('be.visible')
                            .and('have.length', 2)
                            .as('errors');
                        cy.get('@errors')
                            .eq(1)
                            .should('have.text', 'Error: Please enter your feedback');
                        cy.get('@errors')
                            .first()
                            .should('have.text', 'Error: Please select an option');
                    },
                );

                it(
                    'should display an error message when user provided an invalid email address',
                    { tags: 'regression' },
                    () => {
                        const mockInputData = {
                            feedbackContent: 'Some valuable feedback',
                            howSatisfied: 'Dissatisfied',
                            respondentName: 'Jane Smith',
                            respondentEmail: 'some_random_string_which_is_not_valid_email',
                        };

                        loginAndVisitFeedbackPage(role);
                        fillInForm(mockInputData);
                        cy.get('#submit-feedback').click();

                        cy.get('.nhsuk-error-message')
                            .should('be.visible')
                            .and('have.text', 'Error: Enter a valid email address');
                    },
                );
            });
        });
    });
});
