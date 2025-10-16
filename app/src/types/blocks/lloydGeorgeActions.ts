import { REPOSITORY_ROLE } from '../generic/authRole';
import { routeChildren, routes } from '../generic/routes';
import { LG_RECORD_STAGE } from './lloydGeorgeStages';

export enum RECORD_ACTION {
    UPDATE = 0,
    DOWNLOAD = 1,
}

type ActionRoute = routeChildren | routes;

export type LGRecordActionLink = {
    label: string;
    key: string;
    stage?: LG_RECORD_STAGE;
    href?: ActionRoute;
    onClick?: () => void;
    type: RECORD_ACTION;
    unauthorised?: Array<REPOSITORY_ROLE>;
    showIfRecordInStorage: boolean;
};

export const lloydGeorgeRecordLinks: Array<LGRecordActionLink> = [
    {
        label: 'Remove record',
        key: 'delete-all-files-link',
        type: RECORD_ACTION.UPDATE,
        unauthorised: [REPOSITORY_ROLE.GP_CLINICAL],
        href: routeChildren.LLOYD_GEORGE_DELETE,
        showIfRecordInStorage: true,
    },
    {
        label: 'Download record',
        key: 'download-all-files-link',
        type: RECORD_ACTION.DOWNLOAD,
        unauthorised: [REPOSITORY_ROLE.GP_CLINICAL],
        href: routeChildren.LLOYD_GEORGE_DOWNLOAD,
        showIfRecordInStorage: true,
    },
];

type Args = {
    role: REPOSITORY_ROLE | null;
    hasRecordInStorage: boolean;
    inputLinks: Array<LGRecordActionLink>;
};

export const getRecordActionLinksAllowedForRole = ({
    role,
    hasRecordInStorage,
    inputLinks,
}: Args): Array<LGRecordActionLink> => {
    const allowedLinks = inputLinks.filter((link) => {
        if (!role || link.unauthorised?.includes(role)) {
            return false;
        }
        return hasRecordInStorage === link.showIfRecordInStorage;
    });
    return allowedLinks;
};

type ArgsLink = Omit<Args, 'inputLinks'>;

export const getUserRecordActionLinks = ({
    role,
    hasRecordInStorage,
}: ArgsLink): Array<LGRecordActionLink> => {
    const allowedLinks = getRecordActionLinksAllowedForRole({
        role,
        hasRecordInStorage,
        inputLinks: lloydGeorgeRecordLinks,
    });

    return allowedLinks;
};
