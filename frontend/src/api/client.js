import { useCallback, useEffect, useRef, useState } from 'react';
import * as demo from '../data/demo';

export const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

// source: 'live'        → real backend response
//         'demo'        → backend unreachable, bundled sample data
//         'not_exposed' → backend up, but this V2.1 route does not exist yet
//         'empty'       → route exists, but has no record for this id
// After a network failure, skip the round-trip for a while so demo mode stays snappy.
let offlineUntil = 0;

export const resetOffline = () => { offlineUntil = 0; };

async function request(path, fallback, init) {
  const demoResult = () => ({ source: 'demo', data: typeof fallback === 'function' ? fallback() : fallback, path });
  if (Date.now() < offlineUntil) return demoResult();
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 2500);
  try {
    const res = await fetch(`${API_BASE}${path}`, { ...init, signal: ctrl.signal });
    if (res.status === 405) return { source: 'not_exposed', data: null, path };
    if (res.status === 404) {
      // FastAPI answers unknown routes with the generic "Not Found"; our handlers send their own detail
      const body = await res.json().catch(() => ({}));
      return { source: body.detail === 'Not Found' ? 'not_exposed' : 'empty', data: null, path };
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return { source: 'live', data: await res.json(), path };
  } catch {
    offlineUntil = Date.now() + 12000;
    return demoResult();
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  health: () => request('/health', { status: 'demo' }),
  dashboard: () => request('/dashboard', demo.dashboard),
  alerts: () => request('/alerts?limit=2000', () => [...demo.alerts]),
  risk: () => request('/risk?limit=100', demo.risk),
  users: () => request('/users', demo.users),
  attackChains: () => request('/attack-chains', demo.attackChains),
  cases: () => request('/cases', demo.cases),
  profile: (userId) => request(`/profiles/${encodeURIComponent(userId)}`, () => demo.profileFor(userId)),

  async setAlertStatus(alertId, status) {
    const res = await request(`/alerts/${alertId}/status`, null, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    if (res.source === 'demo') {
      const a = demo.alerts.find((x) => x.alert_id === alertId);
      if (a) a.status = status;
    }
    return res;
  },
};

export function useResource(loader, deps = [], { poll } = {}) {
  const [state, setState] = useState({ loading: true, source: null, data: null });
  const alive = useRef(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(loader, deps);

  const reload = useCallback(async () => {
    const res = await run();
    if (alive.current) setState({ loading: false, ...res });
  }, [run]);

  useEffect(() => {
    alive.current = true;
    setState((s) => ({ ...s, loading: true }));
    reload();
    const t = poll ? setInterval(reload, poll) : null;
    return () => { alive.current = false; if (t) clearInterval(t); };
  }, [reload, poll]);

  return { ...state, reload };
}
