import { useCallback, useEffect, useState } from 'react';
import { Toaster } from 'sonner';
import Layout from './components/Layout';
import Overview from './pages/Overview';
import Alerts from './pages/Alerts';
import Investigations from './pages/Investigations';
import AttackChains from './pages/AttackChains';
import Users from './pages/Users';
import SystemHealth from './pages/SystemHealth';

const PAGES = { overview: Overview, alerts: Alerts, investigations: Investigations, attackChains: AttackChains, users: Users, health: SystemHealth };

// #/alerts/4200 → { page: 'alerts', param: '4200' }
function parseHash() {
  const [, page, param] = window.location.hash.split('/');
  return { page: PAGES[page] ? page : 'overview', param: param ? decodeURIComponent(param) : null };
}

export default function App() {
  const [route, setRoute] = useState(parseHash);

  useEffect(() => {
    const onHash = () => setRoute(parseHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const go = useCallback((page, param) => {
    window.location.hash = `/${page}${param != null ? `/${encodeURIComponent(param)}` : ''}`;
  }, []);

  const Page = PAGES[route.page];
  return (
    <>
      <Layout active={route.page} go={go}>
        <Page param={route.param} go={go} />
      </Layout>
      <Toaster theme="dark" position="bottom-right" toastOptions={{
        style: { background: 'var(--ink-2)', border: '1px solid var(--line-strong)', color: 'var(--tx-0)', fontFamily: 'var(--font-ui)' },
      }} />
    </>
  );
}
