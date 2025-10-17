import { NavigateFunction, useNavigate } from 'react-router-dom';

export interface EnhancedNavigate extends NavigateFunction {
    withParams: (pathname: string) => void;
}

export type JourneyType = 'new' | 'update' | undefined;

export function getLastURLPath(url: string) {
    return url.split('/').at(-1);
}

export const useEnhancedNavigate = (): EnhancedNavigate => {
    const navigate = useNavigate();

    return Object.assign(navigate, {
        withParams: (pathname: string) => {
            const searchParams = new URLSearchParams(globalThis.location.search);
            const journey = searchParams.get('journey');
            console.log('journey param:', journey);
            navigate({
                pathname,
                search: searchParams.toString(),
            });
        },
    });
};

export const getJourney = (): JourneyType => {
    return (new URLSearchParams(globalThis.location.search).get('journey') as JourneyType) || 'new';
};
