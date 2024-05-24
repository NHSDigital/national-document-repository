import { pdsPatients, stubPatients } from '../../../support/patients';
import { Roles } from '../../../support/roles';
import dbItem from '../../../fixtures/dynamo-db-items/active-patient.json';

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
            '[Smoke] non-BSOL GP ADMIN user can download and delete the Lloyd George document of an active patient',
            { tags: 'smoke', defaultCommandTimeout: 20000 },
            () => {
                cy.smokeLogin(Roles.GP_ADMIN);

                cy.getByTestId('search-patient-btn').click();

                cy.get('#nhs-number-input').click();
                cy.get('#nhs-number-input').type(activePatient);
                cy.get('#search-submit').click();

                cy.url().should('contain', patientVerifyUrl);
                cy.get('#verify-submit').click();

                cy.url().should('contain', lloydGeorgeRecordUrl);

                cy.getByTestId('pdf-viewer').should('be.visible');

                cy.getByTestId('download-and-remove-record-btn').click();
                cy.getByTestId('confirm-download-and-remove-checkbox').should('exist');
                cy.getByTestId('confirm-download-and-remove-checkbox').click();

                cy.downloadIframeReplace();

                cy.getByTestId('confirm-download-and-remove-btn').click();

                // Assert contents of page when downloading
                cy.getByTestId('lloydgeorge_downloadall-stage', { timeout: 10000 }).should('exist');
                cy.contains('Downloading documents').should('be.visible');
                cy.contains('Preparing download for').should('be.visible');
                cy.contains('Compressing record into a zip file').should('be.visible');
                cy.contains('Cancel').should('be.visible');

                // Assert contents of page after download
                cy.get('.lloydgeorge_download-complete', { timeout: 20000 }).should('exist');
                cy.contains('Download complete').should('be.visible');
                cy.contains('You have successfully downloaded the Lloyd George record of:').should(
                    'be.visible',
                );
                cy.contains(`NHS number: ${activePatient}`).should('be.visible');

                // Assert file has been downloaded
                cy.readFile(
                    `${Cypress.config('downloadsFolder')}/patient-record-${activePatient}.zip`,
                );
            },
        );
    });
});
