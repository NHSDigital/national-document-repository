import viewLloydGeorgePayload from '../../../fixtures/requests/GET_LloydGeorgeStitch.json';
import searchPatientPayload from '../../../fixtures/requests/GET_SearchPatient.json';

const baseUrl = Cypress.env('CYPRESS_BASE_URL') ?? 'http://localhost:3000/';
const gpRoles = ['GP_ADMIN', 'GP_CLINICAL'];

describe('View Lloyd George record has a GP role', () => {
    const assertEmptyLloydGeorgeCard = () => {
        cy.getByTestId('pdf-card').should('include.text', 'Lloyd George record');
        cy.getByTestId('pdf-card').should('include.text', 'No documents are available');
    };

    const assertPatientInfo = () => {
        cy.getByTestId('patient-name').should(
            'have.text',
            `${searchPatientPayload.givenName} ${searchPatientPayload.familyName}`,
        );
        cy.getByTestId('patient-nhs-number').should('have.text', `NHS number: 900 000 0009`);
        cy.getByTestId('patient-dob').should('have.text', `Date of birth: 01 January 1970`);
    };

    const beforeEachConfiguration = (role) => {
        cy.login(role);
        // search patient
        cy.intercept('GET', '/SearchPatient*', {
            statusCode: 200,
            body: searchPatientPayload,
        }).as('search');
        cy.getByTestId('nhs-number-input').type(searchPatientPayload.nhsNumber);
        cy.getByTestId('search-submit-btn').click();
        cy.wait('@search');
    };

    gpRoles.forEach((role) => {
        beforeEach(() => {
            beforeEachConfiguration(role);
        });

        context('View Lloyd George document for ' + role + ' role', () => {
            it(role + ' can view a Lloyd George document of an active patient', () => {
                cy.intercept('GET', '/LloydGeorgeStitch*', {
                    statusCode: 200,
                    body: viewLloydGeorgePayload,
                }).as('lloydGeorgeStitch');

                cy.get('#verify-submit').click();
                cy.wait('@lloydGeorgeStitch');

                // Assert
                assertPatientInfo();
                cy.getByTestId('pdf-card')
                    .should('include.text', 'Lloyd George record')
                    .should('include.text', 'Last updated: 09 October 2023 at 15:41:38')
                    .should('include.text', '12 files | File size: 502 KB | File format: PDF');
                cy.getByTestId('pdf-viewer').should('be.visible');

                // Act - open full screen view
                cy.getByTestId('full-screen-btn').click();

                // Assert
                assertPatientInfo();
                cy.getByTestId('pdf-card').should('not.exist');
                cy.getByTestId('pdf-viewer').should('be.visible');

                //  Act - close full screen view
                cy.getByTestId('back-link').click();

                // Assert
                cy.getByTestId('pdf-card').should('be.visible');
                cy.getByTestId('pdf-viewer').should('be.visible');
            });

            it(
                'It displays an empty Lloyd George card when no Lloyd George record exists for the patient for a ' +
                    role,
                () => {
                    cy.intercept('GET', '/LloydGeorgeStitch*', {
                        statusCode: 404,
                    });
                    cy.get('#verify-submit').click();

                    // Assert
                    assertPatientInfo();
                    assertEmptyLloydGeorgeCard();
                },
            );

            it(
                'It displays an empty Lloyd George card when the Lloyd George Stitch API call fails for a ' +
                    role,
                () => {
                    cy.intercept('GET', '/LloydGeorgeStitch*', {
                        statusCode: 500,
                    });
                    cy.get('#verify-submit').click();

                    //Assert
                    assertPatientInfo();
                    assertEmptyLloydGeorgeCard();
                },
            );
        });
    });

    context('Download Lloyd George document', () => {
        it('GP ADMIN user can download the Lloyd George document of an active patient', () => {
            beforeEachConfiguration('GP_ADMIN');

            cy.intercept('GET', '/LloydGeorgeStitch*', {
                statusCode: 200,
                body: viewLloydGeorgePayload,
            }).as('lloydGeorgeStitch');

            cy.get('#verify-submit').click();
            cy.wait('@lloydGeorgeStitch');

            cy.intercept('GET', '/DocumentManifest*', {
                statusCode: 200,
                body: baseUrl + 'browserconfig.xml', // uses public served file in place of a ZIP file
            }).as('documentManifest');

            cy.getByTestId('actions-menu').click();
            cy.getByTestId('download-all-files-link').click();

            cy.wait('@documentManifest');

            // Assert contents of page when downloading
            cy.contains('Downloading documents').should('be.visible');
            cy.contains(
                `Preparing download for ${viewLloydGeorgePayload.number_of_files} files`,
            ).should('be.visible');
            cy.contains('Compressing record into a zip file').should('be.visible');
            cy.contains('Cancel').should('be.visible');

            // Assert contents of page after download
            cy.contains('Download complete').should('be.visible');
            cy.contains('Documents from the Lloyd George record of:').should('be.visible');
            cy.contains(
                `${searchPatientPayload.givenName} ${searchPatientPayload.familyName}`,
            ).should('be.visible');
            cy.contains(`(NHS number: ${searchPatientPayload.nhsNumber})`).should('be.visible');

            // Assert file has been downloaded
            cy.readFile(`${Cypress.config('downloadsFolder')}/browserconfig.xml`);

            cy.getByTestId('return-btn').click();

            // Assert return button returns to pdf view
            cy.getByTestId('pdf-card').should('be.visible');
        });

        it('No download option or menu exists when no Lloyd George record exists for a patient as a GP ADMIN role', () => {
            beforeEachConfiguration('GP_ADMIN');

            cy.intercept('GET', '/LloydGeorgeStitch*', {
                statusCode: 404,
            }).as('lloydGeorgeStitch');

            cy.get('#verify-submit').click();
            cy.wait('@lloydGeorgeStitch');

            cy.getByTestId('actions-menu').should('not.exist');
        });

        it('No download option exists when a Lloyd George record exists for the patient as a GP CLINICAL role', () => {
            beforeEachConfiguration('GP_CLINICAL');

            cy.intercept('GET', '/LloydGeorgeStitch*', {
                statusCode: 200,
                body: viewLloydGeorgePayload,
            }).as('lloydGeorgeStitch');

            cy.get('#verify-submit').click();
            cy.wait('@lloydGeorgeStitch');

            cy.getByTestId('actions-menu').click();
            cy.getByTestId('download-all-files-link').should('not.exist');
        });

        it.skip('It displays an error when the document manifest API call fails as a GP CLINICAL role', () => {
            cy.intercept('GET', '/LloydGeorgeStitch*', {
                statusCode: 200,
                body: viewLloydGeorgePayload,
            }).as('lloydGeorgeStitch');

            cy.intercept('GET', '/DocumentManifest*', {
                statusCode: 500,
            }).as('documentManifest');

            cy.get('#verify-submit').click();
            cy.wait('@lloydGeorgeStitch');

            cy.getByTestId('actions-menu').click();
            cy.getByTestId('download-all-files-link').click();

            cy.wait('@documentManifest');

            // Assert
            cy.contains('appropriate error for when the document manifest API call fails').should(
                'be.visible',
            );
        });
    });

    context('Delete Lloyd George document', () => {
        it('A GP ADMIN user can delete the Lloyd George document of an active patient', () => {
            beforeEachConfiguration('GP_ADMIN');

            cy.intercept('GET', '/LloydGeorgeStitch*', {
                statusCode: 200,
                body: viewLloydGeorgePayload,
            }).as('lloydGeorgeStitch');

            cy.get('#verify-submit').click();
            cy.wait('@lloydGeorgeStitch');

            cy.getByTestId('actions-menu').click();
            cy.getByTestId('delete-all-files-link').click();

            // assert delete confirmation page is as expected
            cy.contains('Are you sure you want to permanently delete files for:').should(
                'be.visible',
            );
            cy.contains('GivenName Surname').should('be.visible');
            cy.contains('NHS number: 900 000 0009').should('be.visible');
            cy.contains('Date of birth: 01 January 1970').should('be.visible');

            cy.intercept(
                'DELETE',
                `/DocumentDelete?patientId=${searchPatientPayload.nhsNumber}&docType=LG`,
                {
                    statusCode: 200,
                    body: 'Success',
                },
            ).as('documentDelete');

            cy.getByTestId('yes-radio-btn').click();
            cy.getByTestId('delete-submit-btn').click();

            cy.wait('@documentDelete');

            // assert delete success page is as expected
            cy.contains('Deletion complete').should('be.visible');
            cy.contains('12 files from the Lloyd George record of:').should('be.visible');
            cy.contains('GivenName Surname').should('be.visible');
            cy.contains('(NHS number: 900 000 0009)').should('be.visible');

            cy.getByTestId('lg-return-btn').click();

            // assert user is returned to view Lloyd George page
            cy.contains('Lloyd George record').should('be.visible');
            cy.contains('No documents are available').should('be.visible');
            cy.getByTestId('pdf-card').should('be.visible');
        });

        it('Page returns user to view Lloyd George page on the cancel action of delete as a GP ADMIN', () => {
            beforeEachConfiguration('GP_ADMIN');

            cy.intercept('GET', '/LloydGeorgeStitch*', {
                statusCode: 200,
                body: viewLloydGeorgePayload,
            }).as('lloydGeorgeStitch');

            cy.get('#verify-submit').click();
            cy.wait('@lloydGeorgeStitch');

            cy.getByTestId('actions-menu').click();
            cy.getByTestId('delete-all-files-link').click();

            // cancel delete
            cy.getByTestId('no-radio-btn').click();
            cy.getByTestId('delete-submit-btn').click();

            // assert user is returned to view Lloyd George page
            cy.contains('Lloyd George record').should('be.visible');
            cy.getByTestId('pdf-card').should('be.visible');
            cy.getByTestId('pdf-viewer').should('be.visible');
        });

        it('It displays an error when the delete Lloyd George document API call fails as A GP ADMIN', () => {
            beforeEachConfiguration('GP_ADMIN');

            cy.intercept('GET', '/LloydGeorgeStitch*', {
                statusCode: 200,
                body: viewLloydGeorgePayload,
            }).as('lloydGeorgeStitch');

            cy.get('#verify-submit').click();
            cy.wait('@lloydGeorgeStitch');

            cy.getByTestId('actions-menu').click();
            cy.getByTestId('delete-all-files-link').click();

            cy.intercept(
                'DELETE',
                `/DocumentDelete?patientId=${searchPatientPayload.nhsNumber}&docType=LG`,
                {
                    statusCode: 500,
                    body: 'Failed to delete documents',
                },
            ).as('documentDelete');

            cy.getByTestId('yes-radio-btn').click();
            cy.getByTestId('delete-submit-btn').click();

            cy.wait('@documentDelete');

            // assert
            cy.getByTestId('service-error').should('be.visible');
        });

        it('No download option or menu exists when no Lloyd George record exists for the patient for a GP CLINICAL user', () => {
            beforeEachConfiguration('GP_CLINICAL');

            cy.intercept('GET', '/LloydGeorgeStitch*', {
                statusCode: 404,
            }).as('lloydGeorgeStitch');

            cy.get('#verify-submit').click();
            cy.wait('@lloydGeorgeStitch');

            cy.getByTestId('actions-menu').should('not.exist');
        });

        it('No download option exists when a Lloyd George record exists for a GP CLINICAL user', () => {
            beforeEachConfiguration('GP_CLINICAL');
            cy.intercept('GET', '/LloydGeorgeStitch*', {
                statusCode: 200,
                body: viewLloydGeorgePayload,
            }).as('lloydGeorgeStitch');

            cy.get('#verify-submit').click();
            cy.wait('@lloydGeorgeStitch');

            cy.getByTestId('actions-menu').click();
            cy.getByTestId('download-all-files-link').should('not.exist');
        });
    });
});
