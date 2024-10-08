import { render, screen } from '@testing-library/react';
import LgRecordDetails, { Props } from './LloydGeorgeRecordDetails';
import { buildLgSearchResult } from '../../../../helpers/test/testBuilders';
import formatFileSize from '../../../../helpers/utils/formatFileSize';

const mockPdf = buildLgSearchResult();

describe('LloydGeorgeRecordDetails', () => {
    beforeEach(() => {
        process.env.REACT_APP_ENVIRONMENT = 'jest';
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    describe('Rendering', () => {
        it('renders the record details component', () => {
            renderComponent();

            expect(screen.getByText(`Last updated: ${mockPdf.lastUpdated}`)).toBeInTheDocument();
            expect(screen.getByText(`${mockPdf.numberOfFiles} files`)).toBeInTheDocument();
            expect(
                screen.getByText(`File size: ${formatFileSize(mockPdf.totalFileSizeInByte)}`),
            ).toBeInTheDocument();
            expect(screen.getByText('File format: PDF')).toBeInTheDocument();
        });
    });
});

const renderComponent = (propsOverride?: Partial<Props>) => {
    const props: Props = {
        lastUpdated: mockPdf.lastUpdated,
        numberOfFiles: mockPdf.numberOfFiles,
        totalFileSizeInByte: mockPdf.totalFileSizeInByte,
        ...propsOverride,
    };
    return render(<LgRecordDetails {...props} />);
};
