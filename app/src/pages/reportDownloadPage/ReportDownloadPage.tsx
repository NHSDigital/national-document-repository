import { Outlet, Route, Routes } from 'react-router-dom';
import useTitle from '../../helpers/hooks/useTitle';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { getReportByType, REPORT_TYPE } from '../../types/generic/reports';
import { routeChildren, routes } from '../../types/generic/routes';
import { useEffect } from 'react';
import { getLastURLPath } from '../../helpers/utils/urlManipulations';
import DownloadReportSelectStage from '../../components/blocks/_downloadReport/downloadReportSelectStage/DownloadReportSelectStage';
import DownloadReportCompleteStage from '../../components/blocks/_downloadReport/downloadReportCompleteStage/DownloadReportCompleteStage';

const RedirectToHomePage = (): React.JSX.Element => {
    const navigate = useNavigate();
    useEffect(() => {
        navigate(routes.HOME);
    });
    return <></>;
};

const ReportDownloadPage = (): React.JSX.Element => {
    useTitle({ pageTitle: 'Download report' });
    const [searchParams] = useSearchParams();

    const reportType = searchParams.get('reportType') as REPORT_TYPE;

    const report = getReportByType(reportType);

    if (!reportType || !report) {
        return <RedirectToHomePage />;
    }

    return (
        <>
            <div>
                <Routes>
                    <Route index element={<DownloadReportSelectStage report={report} />} />
                    <Route
                        path={getLastURLPath(routeChildren.REPORT_DOWNLOAD_COMPLETE) + '/*'}
                        element={<DownloadReportCompleteStage report={report} />}
                    />
                </Routes>

                <Outlet />
            </div>
        </>
    );
};

export default ReportDownloadPage;
