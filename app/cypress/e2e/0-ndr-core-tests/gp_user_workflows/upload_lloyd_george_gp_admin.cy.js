import { Roles } from '../../../support/roles';
import { routes } from '../../../support/routes';
import searchPatientPayload from '../../../fixtures/requests/GET_SearchPatientLGUpload.json';

const baseUrl = Cypress.config('baseUrl');
const lloydGeorgeViewUrl = '/patient/lloyd-george-record';
const lloydGeorgeUploadUrl = '/patient/document-upload';
const lloydGeorgeInfectedUrl = '/patient/document-upload/infected';

const clickContinueButton = () => {
    cy.get('#continue-button').click();
};

const testSearchPatientButton = () => {
    cy.getByTestId('search-patient-btn').should('be.visible');
    cy.getByTestId('search-patient-btn').click();
    cy.url().should('eq', baseUrl + routes.patientSearch);
};

const testUploadCompletePageContent = () => {
    cy.getByTestId('upload-complete-card').should('be.visible');
    cy.getByTestId('search-patient-link').should('be.visible');
    cy.getByTestId('home-btn').should('be.visible');
    cy.getByTestId('search-patient-link').click();
};

const uploadedFilePathNames = {
    LG: [
        'cypress/fixtures/lg-files/paula_inkley/1of3_Lloyd_George_Record_[Paula Inkley]_[9730211914]_[30-03-2023].pdf',
        [
            'cypress/fixtures/lg-files/paula_inkley/1of3_Lloyd_George_Record_[Paula Inkley]_[9730211914]_[30-03-2023].pdf',
            'cypress/fixtures/lg-files/paula_inkley/2of3_Lloyd_George_Record_[Paula Inkley]_[9730211914]_[30-03-2023].pdf',
        ],
        [
            'cypress/fixtures/lg-files/error_files/empty_file.pdf',
            'cypress/fixtures/lg-files/error_files/invalid_file.pdf',
            'cypress/fixtures/lg-files/error_files/password_protected.pdf',
        ],
    ],
};

const uploadedFileNames = {
    LG: [
        '1of3_Lloyd_George_Record_[Paula Inkley]_[9730211914]_[30-03-2023].pdf',
        [
            '1of3_Lloyd_George_Record_[Paula Inkley]_[9730211914]_[30-03-2023].pdf',
            '2of3_Lloyd_George_Record_[Paula Inkley]_[9730211914]_[30-03-2023].pdf',
        ],
        [
            'empty_file.pdf',
            'invalid_file.pdf',
            'password_protected.pdf',
        ],
    ],
};
const bucketUrlIdentifer = 'https://localhost:3000/Document';
const singleFileUsecaseIndex = 0;
const multiFileUsecaseIndex = 1;
const errorFileUsecaseIndex = 2;

const mockCreateDocRefHandler = (req) => {
    const uploadPayload = req.body.content[0].attachment;
    const clientIds = uploadPayload.map((document) => document.clientId);
    const responseBody = clientIds.reduce((body, id, currentIndex) => {
        body[id] = {
            url: 'https://' + bucketUrlIdentifer,
            fields: {
                key: `test key ${currentIndex}`,
                'x-amz-algorithm': 'xxxx-xxxx-SHA256',
                'x-amz-credential': 'xxxxxxxxxxx/20230904/eu-west-2/s3/aws4_request',
                'x-amz-date': '20230904T125954Z',
                'x-amz-security-token': 'xxxxxxxxx',
                'x-amz-signature': '9xxxxxxxx',
            },
        };
        return body;
    }, {});

    const response = { statusCode: 200, body: responseBody };

    req.reply(response);
};

describe('GP Workflow: Upload Lloyd George record when user is GP admin and patient has no record', () => {
    const beforeEachConfiguration = () => {
        cy.login(Roles.GP_ADMIN);
        cy.visit(routes.patientSearch);

        cy.intercept('GET', '/SearchPatient*', {
            statusCode: 200,
            body: searchPatientPayload,
        }).as('search');
        cy.intercept('POST', '/LloydGeorgeStitch*', {
            statusCode: 404,
        }).as('stitch');
        
        cy.getByTestId('nhs-number-input').type(searchPatientPayload.nhsNumber);
        cy.getByTestId('search-submit-btn').click();
        cy.wait('@search');
        cy.get('#verify-submit').click();
        cy.wait('@stitch');

        cy.getByTestId('upload-patient-record-button').click();
        cy.url().should('include', 'upload');
        cy.url().should('eq', baseUrl + lloydGeorgeUploadUrl);
        cy.intercept('POST', '**/UploadState**', (req) => {
            req.reply({
                statusCode: 204,
            });
        });
        
    };

    beforeEach(() => {
        beforeEachConfiguration();
    });

    context('Upload Lloyd George document for an active patient', () => {
        it(
            `User can upload a single LG file using the "Select files" button and can then view LG record`,
            { tags: 'regression' },
            () => {
                cy.intercept('POST', '**/CreateDocumentReference**', mockCreateDocRefHandler);
                cy.intercept('GET', '**/DocumentStatus*', {
                    statusCode: 200,
                    body: {"test key 0": {"status": "final"}},
                });

                cy.title().should(
                    'eq',
                    'Choose Lloyd George files to upload - Access and store digital patient documents',
                );

                cy.getByTestId('button-input').selectFile(
                    uploadedFilePathNames.LG[singleFileUsecaseIndex],
                    { force: true },
                );
                cy.get('#selected-documents-table').should('contain', uploadedFileNames.LG[singleFileUsecaseIndex]);
                clickContinueButton();

                cy.url({timeout: 25000}).should('contain', '/patient/document-upload/select-order');
                cy.get('#selected-documents-table').should(
                    'contain',
                    uploadedFileNames.LG[singleFileUsecaseIndex],
                );
                cy.getByTestId('form-submit-button').click();
                

                cy.getByTestId('upload-complete-page', { timeout: 25000 }).should('exist');
                cy.getByTestId('upload-complete-page')
                    .should('include.text', 'You have successfully uploaded a digital Lloyd George record for');

                testUploadCompletePageContent();
            },
        );

        it(
            `User can upload multiple LG files using the "Select files" button and can then view LG record`,
            { tags: 'regression' },
            () => {
                cy.intercept('POST', '**/CreateDocumentReference**', mockCreateDocRefHandler);
                cy.intercept('GET', '**/DocumentStatus*', {
                    statusCode: 200,
                    body: {"test key 0": {"status": "final"}},
                });

                cy.getByTestId('button-input').selectFile(
                    uploadedFilePathNames.LG[multiFileUsecaseIndex],
                    { force: true },
                );
                cy.get('#selected-documents-table')
                    .should('contain', uploadedFileNames.LG[multiFileUsecaseIndex][0])
                    .should('contain', uploadedFileNames.LG[multiFileUsecaseIndex][1]);

                clickContinueButton();
                cy.url({timeout: 25000}).should('contain', '/patient/document-upload/select-order');
                cy.get('#selected-documents-table')
                    .should('contain', uploadedFileNames.LG[multiFileUsecaseIndex][0])
                    .should('contain', uploadedFileNames.LG[multiFileUsecaseIndex][1]);
                cy.getByTestId('form-submit-button').click();
                
                cy.url({timeout: 25000}).should('contain', '/patient/document-upload/confirmation');
                cy.get('#selected-documents-table')
                    .should('contain', uploadedFileNames.LG[multiFileUsecaseIndex][0])
                    .should('contain', uploadedFileNames.LG[multiFileUsecaseIndex][1]);
                cy.getByTestId('confirm-button').click();

                cy.getByTestId('upload-complete-page', { timeout: 25000 }).should('exist');
                cy.getByTestId('upload-complete-page')
                    .should('include.text', 'You have successfully uploaded a digital Lloyd George record for');

                testUploadCompletePageContent();
            },
        );

        it(
            `User can upload a multiple LG file using drag and drop and can then view LG record`,
            { tags: 'regression' },
            () => {
                cy.intercept('POST', '**/CreateDocumentReference**', mockCreateDocRefHandler);
                cy.intercept('GET', '**/DocumentStatus*', {
                    statusCode: 200,
                    body: {"test key 0": {"status": "final"}},
                });

                cy.getByTestId('dropzone').selectFile(
                    uploadedFilePathNames.LG[multiFileUsecaseIndex],
                    { force: true, action: 'drag-drop' },
                );
                cy.get('#selected-documents-table')
                    .should('contain', uploadedFileNames.LG[multiFileUsecaseIndex][0])
                    .should('contain', uploadedFileNames.LG[multiFileUsecaseIndex][1]);

                clickContinueButton();
                cy.url({timeout: 25000}).should('contain', '/patient/document-upload/select-order');
                cy.get('#selected-documents-table')
                    .should('contain', uploadedFileNames.LG[multiFileUsecaseIndex][0])
                    .should('contain', uploadedFileNames.LG[multiFileUsecaseIndex][1]);
                cy.getByTestId('form-submit-button').click();
                
                cy.url({timeout: 25000}).should('contain', '/patient/document-upload/confirmation');
                cy.get('#selected-documents-table')
                    .should('contain', uploadedFileNames.LG[multiFileUsecaseIndex][0])
                    .should('contain', uploadedFileNames.LG[multiFileUsecaseIndex][1]);
                cy.getByTestId('confirm-button').click();

                cy.getByTestId('upload-complete-page', { timeout: 25000 }).should('exist');
                cy.getByTestId('upload-complete-page')
                    .should('include.text', 'You have successfully uploaded a digital Lloyd George record for');

                testUploadCompletePageContent();
            },
        );

        it.skip(
            'Error page is displayed when an empty file is uploaded',
            { tags: 'regression' },
            () => {
                cy.intercept('POST', '**/CreateDocumentReference**', mockCreateDocRefHandler);
                cy.intercept('GET', '**/DocumentStatus*', {
                    statusCode: 200,
                    body: {"test key 0": {"status": "final"}},
                });

                cy.getByTestId('button-input').selectFile(
                    uploadedFilePathNames.LG[errorFileUsecaseIndex][0],
                    { force: true },
                );
            }
        )
        
        it.skip(
            'Error page is displayed when an invalid file is uploaded',
            { tags: 'regression' },
            () => {
                cy.intercept('POST', '**/CreateDocumentReference**', mockCreateDocRefHandler);
                cy.intercept('GET', '**/DocumentStatus*', {
                    statusCode: 200,
                    body: {"test key 0": {"status": "final"}},
                });

                cy.getByTestId('button-input').selectFile(
                    uploadedFilePathNames.LG[errorFileUsecaseIndex][1],
                    { force: true },
                );
            }
        )

        it.skip(
            'Error page is displayed when a password protected file is uploaded',
            { tags: 'regression' },
            () => {
                cy.intercept('POST', '**/CreateDocumentReference**', mockCreateDocRefHandler);
                cy.intercept('GET', '**/DocumentStatus*', {
                    statusCode: 200,
                    body: {"test key 0": {"status": "final"}},
                });

                cy.getByTestId('button-input').selectFile(
                    uploadedFilePathNames.LG[errorFileUsecaseIndex][2],
                    { force: true },
                );
            }
        )
        

        it(
            `User's upload journey is stopped if an infected file is detected`,
            { tags: 'regression' },
            () => {
                cy.intercept('POST', '**/CreateDocumentReference**', mockCreateDocRefHandler);
                cy.intercept('GET', '**/DocumentStatus*', {
                    statusCode: 200,
                    body: {
                        "test key 0": 
                        {
                            "status": "infected",
                            "error_code": "UC_4005"
                        }
                    },
                });
                 cy.getByTestId('button-input').selectFile(
                    uploadedFilePathNames.LG[singleFileUsecaseIndex],
                    { force: true },
                );
                cy.get('#selected-documents-table').should('contain', uploadedFileNames.LG[singleFileUsecaseIndex]);
                clickContinueButton();

                cy.url({timeout: 25000}).should('contain', '/patient/document-upload/select-order');
                cy.get('#selected-documents-table').should(
                    'contain',
                    uploadedFileNames.LG[singleFileUsecaseIndex],
                );
                cy.getByTestId('form-submit-button').click();
                cy.url({timeout: 25000}).should('contain', lloydGeorgeInfectedUrl);
                cy.get('#maincontent').should('contain', 'We couldn\'t upload your files because we found a virus');
                cy.getByTestId('go-to-home-button').should('exist');
                cy.getByTestId('go-to-home-button').click();
                cy.url().should('eq', baseUrl + routes.home);
            },
        );
    });
});
