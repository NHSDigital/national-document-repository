import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import {
    buildLgSearchResult,
    buildPatientDetails,
    buildSearchResult,
} from '../../../../helpers/test/testBuilders';
import usePatient from '../../../../helpers/hooks/usePatient';
import LloydGeorgeSelectDownloadStage from './LloydGeorgeSelectDownloadStage';
import { getFormattedDate } from '../../../../helpers/utils/formatDate';
import LloydGeorgeRecordPage from '../../../../pages/lloydGeorgeRecordPage/LloydGeorgeRecordPage';
import axios from 'axios';
import { SEARCH_AND_DOWNLOAD_STATE } from '../../../../types/pages/documentSearchResultsPage/types';

jest.mock('../../../../helpers/hooks/usePatient');
jest.mock('../../../../helpers/hooks/useBaseAPIHeaders');
jest.mock('axios');
jest.mock('react-router', () => ({
    useNavigate: () => mockNavigate,
}));

const mockSetStage = jest.fn();
const mockSetDownloadStage = jest.fn();
const mockPatient = buildPatientDetails();
const mockedUsePatient = usePatient as jest.Mock;
const mockNavigate = jest.fn();
const mockSetSearchResults = jest.fn();
const mockSetSubmissionSearchState = jest.fn();
const mockAxios = axios as jest.Mocked<typeof axios>;
const searchResults = [
    buildSearchResult({ fileName: '1of2_test.pdf', ID: 'test-id-1' }),
    buildSearchResult({ fileName: '2of2_test.pdf', ID: 'test-id-2' }),
    buildSearchResult({ fileName: '1of1_test.pdf', ID: 'test-id-3' }),
];

describe('LloydGeorgeSelectDownloadStage', () => {
    beforeEach(() => {
        process.env.REACT_APP_ENVIRONMENT = 'jest';
        mockedUsePatient.mockReturnValue(mockPatient);
    });
    afterEach(() => {
        jest.clearAllMocks();
    });

    it('renders the page header, patient details and loading text', () => {
        render(
            <LloydGeorgeSelectDownloadStage
                setStage={mockSetStage}
                setDownloadStage={mockSetDownloadStage}
            />,
        );

        expect(
            screen.getByRole('heading', {
                name: 'Download the Lloyd George record for this patient',
            }),
        ).toBeInTheDocument();
        expect(screen.getByText('NHS number')).toBeInTheDocument();
        expect(screen.getByText(`${mockPatient.nhsNumber}`)).toBeInTheDocument();
        expect(screen.getByText('Surname')).toBeInTheDocument();
        expect(screen.getByText(`${mockPatient.familyName}`)).toBeInTheDocument();
        expect(screen.getByText('First name')).toBeInTheDocument();
        expect(screen.getByText(`${mockPatient.givenName}`)).toBeInTheDocument();
        expect(screen.getByText('Date of birth')).toBeInTheDocument();
        expect(
            screen.getByText(getFormattedDate(new Date(mockPatient.birthDate))),
        ).toBeInTheDocument();
        expect(screen.getByText('Postcode')).toBeInTheDocument();
        expect(screen.getByText(`${mockPatient.postalCode}`)).toBeInTheDocument();

        expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('renders initial lg record view with file info when LG record is returned by search', async () => {
        // mockAxios.get.mockImplementation(() => Promise.resolve());
        // mockAxios.get.mockReturnValue(Promise.resolve({data: searchResults}));
        render(
            <LloydGeorgeSelectDownloadStage
                setStage={mockSetStage}
                setDownloadStage={mockSetDownloadStage}
            />,
        );
        await waitFor(async () => {
            expect(
                screen.getByText('Download the Lloyd George record for this patient'),
            ).toBeInTheDocument();
        });

        // expect(mockSetSearchResults).toBeCalled();
        // expect(mockSetSubmissionSearchState).toBeCalledWith(SEARCH_AND_DOWNLOAD_STATE.SEARCH_SUCCEEDED);
    });
});
