import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { Dispatch, ReactNode, SetStateAction } from 'react';
import { UserAuth } from '../../types/blocks/userAuth';

type SetSessionOverride = (session: Session) => void;

type Props = {
    children: ReactNode;
    sessionOverride?: Partial<Session>;
    setSessionOverride?: SetSessionOverride;
};
export type Session = {
    auth: UserAuth | null;
    isLoggedIn: boolean;
    sessionOverride?: Partial<Session>;
    isFullscreen?: boolean;
};

export type SessionContext = [Session, Dispatch<SetStateAction<Session>> | SetSessionOverride];

const UserSessionContext = createContext<SessionContext | null>(null);
const SessionProvider = ({
    children,
    sessionOverride,
    setSessionOverride,
}: Props): React.JSX.Element => {
    const emptySession = useMemo(
        () => ({ auth: null, isLoggedIn: false, ...sessionOverride, isFullscreen: false }),
        [sessionOverride],
    );

    const userSessionValue = sessionStorage.getItem('UserSession');
    const userSession: Session = userSessionValue ? JSON.parse(userSessionValue) : emptySession;
    const [session, setSession] = useState<Session>({
        ...userSession,
        sessionOverride,
        isFullscreen: false,
    });

    useEffect(() => {
        sessionStorage.setItem('UserSession', JSON.stringify(session) ?? emptySession);
    }, [session, emptySession]);

    return (
        <UserSessionContext.Provider value={[session, setSessionOverride ?? setSession]}>
            {children}
        </UserSessionContext.Provider>
    );
};

export default SessionProvider;
export const useSessionContext = (): SessionContext =>
    useContext(UserSessionContext) as SessionContext;
