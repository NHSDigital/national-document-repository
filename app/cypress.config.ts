import { defineConfig } from 'cypress';
import * as dotenv from 'dotenv';

function getBaseUrlFromEnv() {
    dotenv.config();
    return ensureEndsWithSlash(process.env.CYPRESS_BASE_URL);
}

function ensureEndsWithSlash(url: string): string {
    return url.endsWith('/') ? url : url + '/';
}

export default defineConfig({
    e2e: {
        setupNodeEvents(on, config) {
            // implement node event listeners here
        },
        downloadsFolder: 'cypress/downloads',
        trashAssetsBeforeRuns: true,
        baseUrl: getBaseUrlFromEnv(),
    },

    component: {
        devServer: {
            framework: 'create-react-app',
            bundler: 'webpack',
        },
    },

    reporter: 'mochawesome',
    reporterOptions: {
        reportDir: 'cypress/results',
        overwrite: false,
        html: false,
        json: true,
    },
});
