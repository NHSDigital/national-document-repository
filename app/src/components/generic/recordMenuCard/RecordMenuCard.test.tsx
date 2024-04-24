import { render, screen } from '@testing-library/react';
import RecordMenuCard from './RecordMenuCard';
import useRole from '../../../helpers/hooks/useRole';
import { RECORD_ACTION } from '../../../types/blocks/lloydGeorgeActions';
import { REPOSITORY_ROLE } from '../../../types/generic/authRole';
import { LinkProps } from 'react-router-dom';
import { LG_RECORD_STAGE } from '../../../types/blocks/lloydGeorgeStages';
import { routes } from '../../../types/generic/routes';
import userEvent from '@testing-library/user-event';
import { act } from 'react-dom/test-utils';

jest.mock('../../../helpers/hooks/useRole');
const mockSetStage = jest.fn();
const mockedUseNavigate = jest.fn();
const mockedUseRole = useRole as jest.Mock;

const mockLinks = [
    {
        label: 'Upload files',
        key: 'upload-files-link',
        type: RECORD_ACTION.UPLOAD,
        href: routes.HOME,
        unauthorised: [REPOSITORY_ROLE.GP_CLINICAL],
    },
    {
        label: 'Remove a selection of files',
        key: 'delete-file-link',
        type: RECORD_ACTION.DOWNLOAD,
        stage: LG_RECORD_STAGE.DELETE_ALL,
        unauthorised: [],
    },
];

jest.mock('react-router-dom', () => ({
    __esModule: true,
    Link: (props: LinkProps) => <a {...props} role="link" />,
    useNavigate: () => mockedUseNavigate,
}));

describe('RecordMenuCard', () => {
    beforeEach(() => {
        process.env.REACT_APP_ENVIRONMENT = 'jest';
        mockedUseRole.mockReturnValue(REPOSITORY_ROLE.GP_ADMIN);
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    describe('Rendering', () => {
        it('renders menu', () => {
            const { rerender } = render(
                <RecordMenuCard setStage={mockSetStage} recordLinks={mockLinks} hasPdf={true} />,
            );
            expect(screen.getByRole('heading', { name: 'Download record' })).toBeInTheDocument();
            expect(
                screen.getByRole('link', { name: 'Remove a selection of files' }),
            ).toBeInTheDocument();

            rerender(
                <RecordMenuCard setStage={mockSetStage} recordLinks={mockLinks} hasPdf={false} />,
            );
            expect(screen.getByRole('heading', { name: 'Update record' })).toBeInTheDocument();
            expect(screen.getByRole('link', { name: 'Upload files' })).toBeInTheDocument();
        });

        it('does not render menu item if unauthorised', () => {
            mockedUseRole.mockReturnValue(REPOSITORY_ROLE.GP_ADMIN);

            const { rerender } = render(
                <RecordMenuCard setStage={mockSetStage} recordLinks={mockLinks} hasPdf={false} />,
            );
            expect(screen.getByRole('heading', { name: 'Update record' })).toBeInTheDocument();
            expect(screen.getByRole('link', { name: 'Upload files' })).toBeInTheDocument();

            mockedUseRole.mockReturnValue(REPOSITORY_ROLE.GP_CLINICAL);

            rerender(
                <RecordMenuCard setStage={mockSetStage} recordLinks={mockLinks} hasPdf={false} />,
            );
            expect(
                screen.queryByRole('heading', { name: 'Update record' }),
            ).not.toBeInTheDocument();
            expect(screen.queryByRole('link', { name: 'Upload files' })).not.toBeInTheDocument();
        });

        it("does not render 'update record' if hasPdf", () => {
            const { rerender } = render(
                <RecordMenuCard setStage={mockSetStage} recordLinks={mockLinks} hasPdf={true} />,
            );
            expect(
                screen.queryByRole('heading', { name: 'Update record' }),
            ).not.toBeInTheDocument();
            expect(screen.queryByRole('link', { name: 'Upload files' })).not.toBeInTheDocument();

            rerender(
                <RecordMenuCard setStage={mockSetStage} recordLinks={mockLinks} hasPdf={false} />,
            );
            expect(screen.getByRole('heading', { name: 'Update record' })).toBeInTheDocument();
            expect(screen.getByRole('link', { name: 'Upload files' })).toBeInTheDocument();
        });

        it("does not render 'download record' if not hasPdf", () => {
            const { rerender } = render(
                <RecordMenuCard setStage={mockSetStage} recordLinks={mockLinks} hasPdf={false} />,
            );
            expect(
                screen.queryByRole('heading', { name: 'Download record' }),
            ).not.toBeInTheDocument();
            expect(
                screen.queryByRole('link', { name: 'Remove a selection of files' }),
            ).not.toBeInTheDocument();

            rerender(
                <RecordMenuCard setStage={mockSetStage} recordLinks={mockLinks} hasPdf={true} />,
            );
            expect(screen.getByRole('heading', { name: 'Download record' })).toBeInTheDocument();
            expect(
                screen.getByRole('link', { name: 'Remove a selection of files' }),
            ).toBeInTheDocument();
        });
    });
    describe('Navigation', () => {
        it('navigates to href when clicked', () => {
            render(
                <RecordMenuCard setStage={mockSetStage} recordLinks={mockLinks} hasPdf={false} />,
            );
            expect(screen.getByRole('heading', { name: 'Update record' })).toBeInTheDocument();
            expect(screen.getByRole('link', { name: 'Upload files' })).toBeInTheDocument();
            act(() => {
                userEvent.click(screen.getByRole('link', { name: 'Upload files' }));
            });
            expect(mockedUseNavigate).toHaveBeenCalledWith(routes.HOME);
        });

        it('navigates to stage when clicked', () => {
            render(
                <RecordMenuCard setStage={mockSetStage} recordLinks={mockLinks} hasPdf={true} />,
            );
            expect(screen.getByRole('heading', { name: 'Download record' })).toBeInTheDocument();
            expect(
                screen.getByRole('link', { name: 'Remove a selection of files' }),
            ).toBeInTheDocument();

            act(() => {
                userEvent.click(screen.getByRole('link', { name: 'Remove a selection of files' }));
            });
            expect(mockSetStage).toHaveBeenCalledWith(LG_RECORD_STAGE.DELETE_ALL);
        });
    });
});
