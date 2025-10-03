import { verify } from 'crypto';
import { pdsPatients, stubPatients } from '../../../support/patients';
import { Roles } from '../../../support/roles';

const workspace = Cypress.env('WORKSPACE');

const uploadedFilePathNames = [
    'cypress/fixtures/lg-files/paula_inkley/1of3_Lloyd_George_Record_[Paula Inkley]_[9730211914]_[30-03-2023].pdf',
    'cypress/fixtures/lg-files/paula_inkley/2of3_Lloyd_George_Record_[Paula Inkley]_[9730211914]_[30-03-2023].pdf',
    'cypress/fixtures/lg-files/paula_inkley/3of3_Lloyd_George_Record_[Paula Inkley]_[9730211914]_[30-03-2023].pdf',
];
const uploadedFileNames = [
    '1of3_Lloyd_George_Record_[Paula Inkley]_[9730211914]_[30-03-2023].pdf',
    '2of3_Lloyd_George_Record_[Paula Inkley]_[9730211914]_[30-03-2023].pdf',
    '3of3_Lloyd_George_Record_[Paula Inkley]_[9730211914]_[30-03-2023].pdf',
];

const baseUrl = Cypress.config('baseUrl');
const bucketName = `${workspace}-lloyd-george-store`;
const tableName = `${workspace}_LloydGeorgeReferenceMetadata`;

const searchPatientUrl = '/patient/search';
const patientVerifyUrl = '/patient/verify';
const lloydGeorgeRecordUrl = '/patient/lloyd-george-record';
const selectOrderUrl = '/patient/document-upload/select-order';
const confirmationUrl = '/patient/document-upload/confirmation';

const activePatient = pdsPatients.activeNoUpload;

describe('GP Workflow: Upload Lloyd George record', () => {
    context('Upload a Lloyd George document', () => {
        beforeEach(() => {
            //delete any records present for the active patient
            cy.deleteItemsBySecondaryKeyFromDynamoDb(
                tableName,
                'NhsNumberIndex',
                'NhsNumber',
                activePatient.toString(),
            );
            uploadedFileNames.forEach((file) => {
                cy.deleteFileFromS3(bucketName, file);
            });
        });

        afterEach(() => {
            //clean up any records present for the active patient
            cy.deleteItemsBySecondaryKeyFromDynamoDb(
                tableName,
                'NhsNumberIndex',
                'NhsNumber',
                activePatient.toString(),
            );
            uploadedFileNames.forEach((file) => {
                cy.deleteFileFromS3(bucketName, file);
            });
        });

        it(
            '[Smoke] GP ADMIN can upload multiple files and then view a Lloyd George record for an active patient with no record',
            { defaultCommandTimeout: 20000 },
            () => {
                cy.smokeLogin(Roles.SMOKE_GP_ADMIN);

                cy.navigateToPatientSearchPage();

                cy.get('#nhs-number-input').should('exist');
                cy.get('#nhs-number-input').click();
                cy.get('#nhs-number-input').type(activePatient);
                cy.getByTestId('search-submit-btn').should('exist');
                cy.getByTestId('search-submit-btn').click();

                cy.url({ timeout: 15000 }).should('contain', patientVerifyUrl);

                cy.get('#verify-submit').should('exist');
                cy.get('#verify-submit').click();

                cy.url().should('contain', lloydGeorgeRecordUrl);
                cy.getByTestId('no-records-title').should(
                    'include.text',
                    'This patient does not have a Lloyd George record',
                );
                cy.getByTestId('upload-patient-record-button').should('exist');
                cy.getByTestId('upload-patient-record-button').click();
                uploadedFilePathNames.forEach((file) => {
                    cy.getByTestId('button-input').selectFile(file, { force: true });
                    var index = uploadedFilePathNames.indexOf(file);
                    cy.get('#selected-documents-table').should('contain', uploadedFileNames[index]);
                });
                cy.get('#continue-button').click();

                cy.url().should('contain', selectOrderUrl);
                cy.get('#selected-documents-table').should('exist');
                uploadedFileNames.forEach((name) => {
                    cy.get('#selected-documents-table').should('contain', name);
                });
                cy.getByTestId('form-submit-button').click();

                cy.url().should('contain', confirmationUrl);
                uploadedFileNames.forEach((name) => {
                    cy.get('#selected-documents-table').should('contain', name);
                });
                cy.getByTestId('confirm-button').click();
                
                cy.getByTestId('upload-complete-page', { timeout: 25000 }).should('exist');
                cy.getByTestId('upload-complete-page')
                    .should('include.text', 'You have successfully uploaded a digital Lloyd George record for');

                cy.getByTestId('upload-complete-card').should('be.visible');
                cy.getByTestId('search-patient-link').should('be.visible');
                cy.getByTestId('home-btn').should('be.visible');
                cy.getByTestId('search-patient-link').click();
                
                cy.url().should('contain', searchPatientUrl);
                cy.get('#nhs-number-input').type(activePatient);
                cy.getByTestId('search-submit-btn').click();

                cy.url({ timeout: 15000 }).should('contain', patientVerifyUrl);
                cy.get('#verify-submit').click();

                cy.url().should('contain', lloydGeorgeRecordUrl);
                cy.getByTestId('pdf-card').should('exist');
            },
        );
    });
});
