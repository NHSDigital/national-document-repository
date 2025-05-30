import useTitle from '../../helpers/hooks/useTitle';
import { Outlet, Route, Routes } from 'react-router';
import { routeChildren } from '../../types/generic/routes';
import CookiePolicy from '../../components/blocks/_cookiesPolicy/cookiesPolicy/CookiesPolicy';
import CookiesPolicyUpdatedStage from '../../components/blocks/_cookiesPolicy/cookiesPolicyUpdated/CookiesPolicyUpdatedStage';
import { getLastURLPath } from '../../helpers/utils/urlManipulations';

const CookiePolicyPage = () => {
    const pageTitle = 'Cookies policy';
    useTitle({ pageTitle });

    return (
        <div>
            <Routes>
                <Route index element={<CookiePolicy />} />
                <Route
                    path={getLastURLPath(routeChildren.COOKIES_POLICY_UPDATED + '/*')}
                    element={<CookiesPolicyUpdatedStage />}
                />
            </Routes>

            <Outlet />
        </div>
    );
};

export default CookiePolicyPage;
