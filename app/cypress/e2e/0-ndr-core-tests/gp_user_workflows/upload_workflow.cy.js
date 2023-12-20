import { Roles, roleName } from '../../../support/roles';

// env vars
const baseUrl = Cypress.config('baseUrl');

const formTypes = Object.freeze({
    LG: 'LG',
    ARF: 'ARF',
});

const testPatient = '9000000009';
const patient = {
    birthDate: '1970-01-01',
    familyName: 'Default Surname',
    givenName: ['Default Given Name'],
    nhsNumber: testPatient,
    postalCode: 'AA1 1AA',
    superseded: false,
    restricted: false,
    active: false,
};

const bucketUrlIdentifer = 'document-store.s3.amazonaws.com';
const serverError = 500;
const successNoContent = 204;
const homeUrl = '/';

const selectForm = (formType) => cy.get(`#${formType}-documents-input`);

const navigateToUploadPage = () => {
    cy.intercept('GET', '/SearchPatient*', {
        statusCode: 200,
        body: patient,
    }).as('search');

    cy.get('#nhs-number-input').click();
    cy.get('#nhs-number-input').type(testPatient);

    cy.get('#search-submit').click();
    cy.wait('@search');

    cy.get('#verify-submit').click();
};

const clickUploadButton = () => {
    cy.get('#upload-button').click();
    cy.wait(20);
};

const testStartAgainButton = () => {
    cy.get('#start-again-button').should('have.text', 'Start Again');
    cy.get('#start-again-button').click();
    cy.url().should('eq', baseUrl + homeUrl);
};

const singleFileUsecaseIndex = 0;
const multiFileUSecaseIndex = 1;

const uploadedFilePathNames = {
    ARF: [
        'cypress/fixtures/test_patient_record.pdf',
        [
            'cypress/fixtures/test_patient_record.pdf',
            'cypress/fixtures/test_patient_record_two.pdf',
        ],
    ],
    LG: [
        'cypress/fixtures/lg-files/1of1_Lloyd_George_Record_[Testy Test]_[0123456789]_[01-01-2011].pdf',
        [
            'cypress/fixtures/lg-files/1of2_Lloyd_George_Record_[Testy Test]_[0123456789]_[01-01-2011].pdf',
            'cypress/fixtures/lg-files/2of2_Lloyd_George_Record_[Testy Test]_[0123456789]_[01-01-2011].pdf',
        ],
    ],
};

const uploadedFileNames = {
    ARF: ['test_patient_record.pdf', ['test_patient_record.pdf', 'test_patient_record_two.pdf']],
    LG: [
        '1of1_Lloyd_George_Record_[Testy Test]_[0123456789]_[01-01-2011].pdf',
        [
            '1of2_Lloyd_George_Record_[Testy Test]_[0123456789]_[01-01-2011].pdf',
            '2of2_Lloyd_George_Record_[Testy Test]_[0123456789]_[01-01-2011].pdf',
        ],
    ],
};

const gpRoles = [Roles.GP_ADMIN, Roles.GP_CLINICAL];

describe('GP Workflow: Upload docs and verify', () => {
    gpRoles.forEach((role) => {
        beforeEach(() => {
            cy.login(role);
            navigateToUploadPage();
        });
        it(
            `On Start now button click as ${roleName(role)} redirect to uploads is successful`,
            { tags: 'regression' },
            () => {
                cy.url().should('include', 'upload');
                cy.url().should('eq', baseUrl + '/upload/submit');
            },
        );

        it.skip(
            `On Upload button click with a single file for ARF and LG, renders 'Upload Summary' screen for successful upload as a ${roleName(
                role,
            )}`,
            { tags: 'regression' },
            () => {
                cy.intercept('POST', '**/DocumentReference**', {
                    statusCode: 200,
                    body: {
                        url: 'http://' + bucketUrlIdentifer,
                        fields: {
                            key: 'test key',
                            'x-amz-algorithm': 'xxxx-xxxx-SHA256',
                            'x-amz-credential': 'xxxxxxxxxxx/20230904/eu-west-2/s3/aws4_request',
                            'x-amz-date': '20230904T125954Z',
                            'x-amz-security-token': 'xxxxxxxxx',
                            'x-amz-signature': '9xxxxxxxx',
                        },
                    },
                });

                cy.intercept('POST', '**' + bucketUrlIdentifer + '**', {
                    statusCode: 204,
                });
                selectForm(formTypes.ARF).selectFile(
                    uploadedFilePathNames.ARF[singleFileUsecaseIndex],
                );
                selectForm(formTypes.LG).selectFile(
                    uploadedFilePathNames.LG[singleFileUsecaseIndex],
                );

                clickUploadButton();

                cy.get('#upload-summary-confirmation').should('be.visible');
                cy.get('#upload-summary-header').should('be.visible');
                cy.get('#successful-uploads-dropdown').should('be.visible');
                cy.get('#successful-uploads-dropdown').click();

                cy.get('#successful-uploads tbody tr').should('have.length', 2);
                cy.get('#successful-uploads tbody tr')
                    .eq(0)
                    .should('contain', uploadedFileNames.ARF[singleFileUsecaseIndex]);
                cy.get('#successful-uploads tbody tr')
                    .eq(1)
                    .should('contain', uploadedFileNames.LG[singleFileUsecaseIndex]);
                cy.get('#close-page-warning').should('be.visible');

                testStartAgainButton();
            },
        );

        Object.values(formTypes).forEach((type) => {
            describe(`[${type}] Upload: `, () => {
                it(
                    `Single file: On Choose files button click, file selection is visible for ${type} input as a ${roleName(
                        role,
                    )} `,
                    { tags: 'regression' },
                    () => {
                        cy.get('#selected-documents-table').should('not.exist');
                        selectForm(type).selectFile(
                            uploadedFilePathNames[type][singleFileUsecaseIndex],
                        );
                        cy.get('#selected-documents-table').should('be.visible');
                        cy.get('#selected-documents-table tbody tr').should('have.length', 1);
                        cy.get('#selected-documents-table tbody tr')
                            .first()
                            .get('td')
                            .first()
                            .should(
                                'contain.text',
                                uploadedFileNames[type][singleFileUsecaseIndex],
                            );
                    },
                );

                it(
                    `Single file: On Upload button click, renders 'Upload Summary' view with error box when DocumentReference returns a 500 for ${type} input as a ${roleName(
                        role,
                    )} `,
                    { tags: 'regression' },
                    () => {
                        // intercept this response and return an error
                        cy.intercept('POST', '*/DocumentReference*', {
                            statusCode: 500,
                        });

                        selectForm(type).selectFile(
                            uploadedFilePathNames[type][singleFileUsecaseIndex],
                        );

                        clickUploadButton();

                        cy.get('#failed-document-uploads-summary-title').should('be.visible');
                        cy.get('#failed-uploads').should('be.visible');
                        cy.get('#failed-uploads tbody tr').should('have.length', 1);
                        cy.get('#failed-uploads tbody tr')
                            .first()
                            .get('td')
                            .first()
                            .should('contain', uploadedFileNames[type][0]);
                        cy.get('#failed-uploads').should(
                            'contain',
                            '1 of 1 files failed to upload',
                        );
                        cy.get('#close-page-warning').should('be.visible');

                        testStartAgainButton();
                    },
                );

                it(
                    `Single file: On Upload button click, renders 'Upload Summary' view with error box when DocumentReference returns a 404 for ${type} input as a ${roleName(
                        role,
                    )} `,
                    { tags: 'regression' },
                    () => {
                        // intercept this response and return an error
                        cy.intercept('POST', '*/DocumentReference*', {
                            statusCode: 404,
                        });

                        selectForm(type).selectFile(
                            uploadedFilePathNames[type][singleFileUsecaseIndex],
                        );

                        clickUploadButton();

                        cy.get('#failed-document-uploads-summary-title').should('be.visible');
                        cy.get('#failed-uploads').should('be.visible');
                        cy.get('#failed-uploads tbody tr').should('have.length', 1);
                        cy.get('#failed-uploads tbody tr')
                            .first()
                            .children()
                            .first()
                            .should('contain', uploadedFileNames[type][singleFileUsecaseIndex]);
                        cy.get('#failed-uploads').should(
                            'contain',
                            '1 of 1 files failed to upload',
                        );
                        cy.get('#close-page-warning').should('be.visible');

                        testStartAgainButton();
                    },
                );

                it(
                    `Single file: On Upload button click, renders 'Upload Summary' view with error box when the S3 bucket POST request fails for ${type} input as a ${roleName(
                        role,
                    )} `,
                    { tags: 'regression' },
                    () => {
                        // intercept this response and return an error
                        cy.intercept('POST', bucketUrlIdentifer, {
                            statusCode: 500,
                        });

                        selectForm(type).selectFile(
                            uploadedFilePathNames[type][singleFileUsecaseIndex],
                        );

                        clickUploadButton();

                        cy.get('#failed-document-uploads-summary-title').should('be.visible');
                        cy.get('#failed-uploads').should('be.visible');
                        cy.get('#failed-uploads tbody tr').should('have.length', 1);
                        cy.get('#failed-uploads tbody tr')
                            .first()
                            .children()
                            .first()
                            .should(
                                'contain.text',
                                uploadedFileNames[type][singleFileUsecaseIndex],
                            );
                        cy.get('#failed-uploads').should(
                            'contain',
                            '1 of 1 files failed to upload',
                        );
                        cy.get('#close-page-warning').should('be.visible');

                        testStartAgainButton();
                    },
                );

                it(
                    `Multiple files: On Choose files button click, file selection is visible for ${type} input as a ${roleName(
                        role,
                    )}`,
                    { tags: 'regression' },
                    () => {
                        cy.get('#selected-documents-table').should('not.exist');
                        selectForm(type).selectFile(
                            uploadedFilePathNames[type][multiFileUSecaseIndex],
                        );
                        cy.get('#selected-documents-table').should('be.visible');
                        cy.get('#selected-documents-table tbody tr').should('have.length', 2);

                        cy.get('#selected-documents-table tbody tr')
                            .first()
                            .children()
                            .first()
                            .should('have.text', uploadedFileNames[type][multiFileUSecaseIndex][0]);
                        cy.get('#selected-documents-table tbody tr')
                            .eq(1)
                            .children()
                            .first()
                            .should('have.text', uploadedFileNames[type][multiFileUSecaseIndex][1]);
                    },
                );

                it.skip(
                    `Multiple files: On Upload button click, renders 'Upload Summary' view for successful upload for ${type} input as a ${roleName(
                        role,
                    )}`,
                    { tags: 'regression' },
                    () => {
                        cy.intercept('POST', '**/DocumentReference**', {
                            statusCode: 200,
                            body: {
                                url: 'http://' + bucketUrlIdentifer,
                                fields: {
                                    key: 'test key',
                                    'x-amz-algorithm': 'xxxx-xxxx-SHA256',
                                    'x-amz-credential':
                                        'xxxxxxxxxxx/20230904/eu-west-2/s3/aws4_request',
                                    'x-amz-date': '20230904T125954Z',
                                    'x-amz-security-token': 'xxxxxxxxx',
                                    'x-amz-signature': '9xxxxxxxx',
                                },
                            },
                        });

                        cy.intercept('POST', '**' + bucketUrlIdentifer + '**', {
                            statusCode: 204,
                        });

                        selectForm(type).selectFile(
                            uploadedFilePathNames[type][multiFileUSecaseIndex],
                        );

                        clickUploadButton();

                        cy.get('#upload-summary-confirmation').should('be.visible');
                        cy.get('#upload-summary-header').should('be.visible');
                        cy.get('#successful-uploads-dropdown').should('be.visible');
                        cy.get('#successful-uploads tbody tr').should('have.length', 2);
                        cy.get('#successful-uploads tbody tr')
                            .first()
                            .children()
                            .first()
                            .should('contain', uploadedFileNames[type][multiFileUSecaseIndex][0]);
                        cy.get('#close-page-warning').should('be.visible');

                        testStartAgainButton();
                    },
                );

                it(
                    `Multiple files: On Upload button click, renders Uploading Stage for ${type} input as a ${roleName(
                        role,
                    )}`,
                    { tags: 'regression' },
                    () => {
                        cy.intercept('POST', '**/DocumentReference*', (req) => {
                            req.reply({
                                statusCode: 200,
                                delay: 1500,
                                body: {
                                    url: bucketUrlIdentifer,
                                    fields: {
                                        key: 'xxxxxxxxxxxx2',
                                        'x-amz-algorithm': 'AWS4-HMAC-SHA256',
                                        'x-amz-credential':
                                            'xxxxxxxxxxxxxxxxxx/20230904/eu-west-2/s3/aws4_request',
                                        'x-amz-date': '20230904T125954Z',
                                        'x-amz-security-token': 'xxxxxxxxxxxxxxxx',
                                        policy: 'xxxxxxxxx====',
                                        'x-amz-signature': 'xxxxxxxxx',
                                    },
                                },
                            });
                        });

                        selectForm(type).selectFile(
                            uploadedFilePathNames[type][multiFileUSecaseIndex],
                        );

                        clickUploadButton();

                        cy.get('#upload-stage-warning').should('be.visible');
                    },
                );

                it(
                    `Multiple files: On Upload button click, renders 'Upload Summary' view  with error box when DocumentReference returns a 500 for ${type} input as a ${roleName(
                        role,
                    )}`,
                    { tags: 'regression' },
                    () => {
                        // intercept this response and return an error
                        cy.intercept('POST', '*/DocumentReference*', {
                            statusCode: 500,
                        });

                        selectForm(type).selectFile(uploadedFilePathNames[type][1]);

                        clickUploadButton();

                        cy.get('#failed-document-uploads-summary-title').should('be.visible');
                        cy.get('#failed-uploads').should('be.visible');
                        cy.get('#failed-uploads tbody tr').should(
                            'have.length',
                            uploadedFilePathNames[type][1].length,
                        );

                        cy.get('#failed-uploads tbody tr')
                            .first()
                            .children()
                            .first()
                            .should(
                                'contain.text',
                                uploadedFileNames[type][multiFileUSecaseIndex][0],
                            );

                        const fileCount = uploadedFilePathNames[type][multiFileUSecaseIndex].length;
                        cy.get('#failed-uploads').should(
                            'contain',
                            fileCount + ' of ' + fileCount + ' files failed to upload',
                        );

                        cy.get('#close-page-warning').should('be.visible');

                        testStartAgainButton();
                    },
                );

                it(
                    `Multiple files: On Upload button click, renders 'Upload Summary' view with error box when DocumentReference returns a 404 for ${type} input as a ` +
                        role,
                    { tags: 'regression' },
                    () => {
                        // intercept this response and return an error
                        cy.intercept('POST', '*/DocumentReference*', {
                            statusCode: 404,
                        });

                        selectForm(type).selectFile(
                            uploadedFilePathNames[type][multiFileUSecaseIndex],
                        );

                        clickUploadButton();

                        cy.get('#failed-document-uploads-summary-title').should('be.visible');
                        cy.get('#failed-uploads').should('be.visible');
                        cy.get('#failed-uploads tbody tr').should(
                            'have.length',
                            uploadedFilePathNames[type][multiFileUSecaseIndex].length,
                        );

                        cy.get('#failed-uploads tbody tr')
                            .first()
                            .children()
                            .first()
                            .should(
                                'contain.text',
                                uploadedFileNames[type][multiFileUSecaseIndex][0],
                            );

                        const fileCount = uploadedFilePathNames[type][multiFileUSecaseIndex].length;
                        cy.get('#failed-uploads').should(
                            'contain',
                            fileCount + ' of ' + fileCount + ' files failed to upload',
                        );

                        cy.get('#close-page-warning').should('be.visible');

                        testStartAgainButton();
                    },
                );

                it.skip(
                    `Multiple files: On Upload button click, renders 'Upload Summary' view with both failed and successful documents for ${type} input as a ${roleName(
                        role,
                    )}`,
                    { tags: 'regression' },
                    () => {
                        cy.intercept('POST', '**/DocumentReference*', {
                            statusCode: 200,
                            body: {
                                url: bucketUrlIdentifer,
                                fields: {
                                    key: 'xxxxxxxxxxxx2',
                                    'x-amz-algorithm': 'AWS4-HMAC-SHA256',
                                    'x-amz-credential':
                                        'xxxxxxxxxxxxxxxxxx/20230904/eu-west-2/s3/aws4_request',
                                    'x-amz-date': '20230904T125954Z',
                                    'x-amz-security-token': 'xxxxxxxxxxxxxxxx',
                                    policy: 'xxxxxxxxx====',
                                    'x-amz-signature': 'xxxxxxxxx',
                                },
                            },
                        });

                        let requestCount = 0;
                        cy.intercept('POST', '**' + bucketUrlIdentifer + '**', (req) => {
                            requestCount += 1;
                            req.reply({
                                statusCode: requestCount % 2 === 1 ? serverError : successNoContent,
                            });
                        });

                        selectForm(type).selectFile(
                            uploadedFilePathNames[type][multiFileUSecaseIndex],
                        );

                        clickUploadButton();

                        cy.get('#upload-summary-header').should('be.visible');
                        cy.get('#failed-uploads').should(
                            'contain',
                            '1 of 2 files failed to upload',
                        );
                        cy.get('#failed-uploads tbody tr').should('have.length', 1);
                        cy.get('#successful-uploads tbody tr').should('have.length', 1);
                        cy.get('#close-page-warning').should('be.visible');

                        testStartAgainButton();
                    },
                );
            });
        });
    });
});
