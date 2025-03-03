import { pdsPatients, stubPatients } from '../../../support/patients';
import { Roles } from '../../../support/roles';
import dbItem from '../../../fixtures/dynamo-db-items/active-patient.json';
import { formatNhsNumber } from '../../../../src/helpers/utils/formatNhsNumber';

const workspace = Cypress.env('WORKSPACE');
dbItem.FileLocation = dbItem.FileLocation.replace('{env}', workspace);
const activePatient =
    workspace === 'ndr-dev' ? pdsPatients.activeUpload : stubPatients.activeUpload;
const bucketName = `${workspace}-lloyd-george-store`;
const tableName = `${workspace}_LloydGeorgeReferenceMetadata`;
const fileName = `${activePatient}/e4a6d7f7-01f3-44be-8964-515b2c0ec180`;

const patientVerifyUrl = '/patient/verify';
const lloydGeorgeRecordUrl = '/patient/lloyd-george-record';

describe('GP Workflow: View Lloyd George record', () => {
    context('Download Lloyd George document', () => {
        beforeEach(() => {
            cy.deleteFileFromS3(bucketName, fileName);
            cy.deleteItemFromDynamoDb(tableName, dbItem.ID);
            cy.addPdfFileToS3(bucketName, fileName, 'test_patient_record.pdf');
            cy.addItemToDynamoDb(tableName, dbItem);
        });

        afterEach(() => {
            cy.deleteFileFromS3(bucketName, fileName);
            cy.deleteItemFromDynamoDb(tableName, dbItem.ID);
        });

        it(
            '[Smoke] GP ADMIN user can download the Lloyd George document of an active patient',
            { tags: 'smoke', defaultCommandTimeout: 20000 },
            () => {
                cy.smokeLogin(Roles.GP_ADMIN);
                cy.get('.nhsuk-navigation-container').should('exist');
                cy.navigateToPatientSearchPage();
                cy.get('#nhs-number-input').click();
                cy.get('#nhs-number-input').type(activePatient);
                cy.get('#search-submit').click();

                cy.url().should('contain', patientVerifyUrl);
                cy.get('#verify-submit').click();

                cy.url().should('contain', lloydGeorgeRecordUrl);
                cy.contains('Loading...').should('be.visible');

                cy.getByTestId('pdf-viewer', { timeout: 30000 }).should('be.visible');

                cy.getByTestId('download-all-files-link').click();

                cy.getByTestId('available-files-table-title').should('exist');
                cy.getByTestId('download-file-btn').click();

                cy.downloadIframeReplace();

                cy.intercept('POST', '**/DocumentManifest*').as('postDocumentManifest');

                // Assert contents of page when downloading
                cy.getByTestId('lloydgeorge_downloadall-stage', { timeout: 10000 }).should('exist');
                cy.contains('Downloading documents').should('be.visible');
                cy.contains('Preparing download for').should('be.visible');
                cy.contains('Compressing record into a zip file').should('be.visible');
                cy.contains('Cancel').should('be.visible');

                // Assert contents of page after download
                cy.title({ timeout: 30000 }).should(
                    'eq',
                    'Download complete - Access and store digital patient documents',
                );
                cy.getByTestId('downloaded-record-card-header').should('exist');
                cy.contains('You have downloaded the record of:').should('be.visible');

                const nhsNumberFormatted = formatNhsNumber(activePatient.toString());
                cy.contains(`NHS number: ${nhsNumberFormatted}`).should('be.visible');

                cy.wait('@postDocumentManifest').then(({ response }) => {
                    const downloadJobId = response.body['jobId'];
                    cy.readFile(
                        `${Cypress.config('downloadsFolder')}/patient-record-${downloadJobId}.zip`,
                    );
                });

                cy.getByTestId('logout-btn').click();
                cy.url({ timeout: 10000 }).should('eq', Cypress.config('baseUrl') + '/');
                cy.get('.nhsuk-navigation-container').should('not.exist');
            },
        );
    });
});
