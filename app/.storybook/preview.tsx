import React from 'react';
import type { Preview } from '@storybook/react';
import '../src/styles/App.scss';
import { MemoryRouter } from 'react-router';
import PatientDetailsProvider from '../src/providers/patientProvider/PatientProvider';
import ConfigProvider from '../src/providers/configProvider/ConfigProvider';
import config from '../src/config';

import { buildPatientDetails } from '../src/helpers/test/testBuilders';
const preview: Preview = {
    parameters: {
        actions: { argTypesRegex: '^on[A-Z].*' },
        controls: {
            matchers: {
                color: /(background|color)$/i,
                date: /Date$/,
            },
        },
    },
    decorators: [
        (Story) => (
            <ConfigProvider config={config}>
                <PatientDetailsProvider patientDetails={{ ...buildPatientDetails() }}>
                    <MemoryRouter initialEntries={['/']}>
                        <div
                            className="nhsuk-width-container"
                            style={{
                                margin: `0 auto`,
                                maxWidth: 960,
                                padding: `0 1.0875rem 1.45rem`,
                                minHeight: '75vh',
                            }}
                        >
                            <main
                                className="nhsuk-main-wrapper app-homepage"
                                id="maincontent"
                                role="main"
                            >
                                <section className="app-homepage-content">
                                    <div>
                                        <Story />
                                    </div>
                                </section>
                            </main>
                        </div>
                    </MemoryRouter>
                </PatientDetailsProvider>
            </ConfigProvider>
        ),
    ],
};
export default preview;
