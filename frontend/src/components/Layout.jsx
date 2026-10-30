import { useEffect, useState } from 'react';
import { Command } from 'cmdk';
import { Search, Sun, Moon } from 'lucide-react';
import { api, useResource } from '../api/client';
import { Sev } from './ui';
import { ago } from '../lib/format';

export const NAV = [
  { id: 'overview', label: 'Overview', title: 'Command Center', sub: 'Detections and exposure across every monitored identity.' },
  { id: 'alerts', label: 'Alerts', title: 'Alert Queue', sub: 'Triage by risk. Review or close each detection.' },
  { id: 'investigations', label: 'Cases', title: 'Cases', sub: 'Alerts correlated per user inside a 24-hour window.' },
  { id: 'attackChains', label: 'Attack chains', title: 'Attack Chains', sub: 'Kill-chain stages observed per user, with the evidence for each.' },
  { id: 'users', label: 'Entities', title: 'Entities', sub: 'Risk and behavioural baseline for each identity.' },
  { id: 'health', label: 'Pipeline', title: 'Pipeline Health', sub: 'API probes and the analytics stages each upload runs through.' },
];

const ENGINES = [['CTMC', 'var(--violet)'], ['Rules', 'var(--accent)'], ['Isolation forest', 'var(--cyan)'], ['Baseline', 'var(--sev-low)']];

function readTheme() {
  try {
    const saved = localStorage.getItem('sentinel-theme');
    if (saved === 'light' || saved === 'dark') return saved;
  } catch { /* storage blocked: fall through to system preference */ }
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function useTheme() {
  const [theme, setTheme] = useState(readTheme);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('sentinel-theme', theme); } catch { /* ignore */ }
  }, [theme]);
  return [theme, () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))];
}

function Clock() {
  const [t, setT] = useState(() => new Date());
  useEffect(() => { const i = setInterval(() => setT(new Date()), 1000); return () => clearInterval(i); }, []);
  return <span className="clock">{t.toISOString().slice(11, 19)} UTC</span>;
}

function Palette({ setOpen, go, alerts }) {
  return (
    <div className="cmdk-overlay" onMouseDown={(e) => e.target === e.currentTarget && setOpen(false)}>
      <Command label="Command palette" loop>
        <Command.Input autoFocus placeholder="Jump to a page, entity or alert" />
        <Command.List>
          <Command.Empty>No match.</Command.Empty>
          <Command.Group heading="Pages">
            {NAV.map(({ id, title }) => (
              <Command.Item key={id} value={title} onSelect={() => { go(id); setOpen(false); }}>{title}</Command.Item>
            ))}
          </Command.Group>
          <Command.Group heading="Open alerts">
            {alerts.filter((a) => a.status === 'open').slice(0, 30).map((a) => (
              <Command.Item key={a.alert_id} value={`${a.alert_id} ${a.user_id} ${a.rules_triggered}`}
                onSelect={() => { go('alerts', a.alert_id); setOpen(false); }}>
                <Sev level={a.severity} />
                <span className="strong" style={{ fontWeight: 600 }}>{a.user_id}</span>
                <span className="mono faint" style={{ marginLeft: 'auto' }}>#{a.alert_id} · {ago(a.created_at)} ago</span>
              </Command.Item>
            ))}
          </Command.Group>
        </Command.List>
      </Command>
    </div>
  );
}

export default function Layout({ active, go, children }) {
  const [open, setOpen] = useState(false);
  const [theme, toggleTheme] = useTheme();
  const health = useResource(api.health, [], { poll: 15000 });
  const alerts = useResource(api.alerts, [], { poll: 10000 });
  const list = Array.isArray(alerts.data) ? alerts.data : [];
  const openCount = list.filter((a) => a.status === 'open').length;
  const critCount = list.filter((a) => a.status === 'open' && a.severity === 'Critical').length;
  const live = health.source === 'live';

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setOpen((o) => !o); }
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const current = NAV.find((i) => i.id === active);

  return (
    <div className="shell">
      <header className="masthead">
        <div className="mast-row mast-top">
          <button className="wordmark" onClick={() => go('overview')}>
            <b>Sentinel</b><span>UEBA 2.1 / SOC</span>
          </button>
          <div className="mast-tools">
            <button className="kbd-btn" onClick={() => setOpen(true)}>
              <Search size={16} /> <span className="kbd-label">Search entities, alerts</span> <kbd>Ctrl K</kbd>
            </button>
            <button className="icon-btn" onClick={toggleTheme} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}>
              {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
            </button>
            <span className={`source-pill ${live ? 'live' : 'demo'}`} title={live ? 'Connected to backend' : 'Backend unreachable: showing bundled sample data'}>
              <span className="pulse" /> {live ? 'Live data' : 'Demo data'}
            </span>
            <Clock />
          </div>
        </div>
        <nav className="mast-row nav" aria-label="Pages">
          {NAV.map(({ id, label }) => (
            <button key={id} className={`nav-item ${active === id ? 'active' : ''}`} onClick={() => go(id)} aria-current={active === id ? 'page' : undefined}>
              {label}
              {id === 'alerts' && openCount > 0 && <span className={`nav-count ${critCount ? 'hot' : ''}`}>{openCount}</span>}
            </button>
          ))}
        </nav>
      </header>

      <main className="workspace" key={active}>
        <div className="page-head">
          <div>
            <h1>{current?.title}</h1>
          </div>
          <p>{current?.sub}</p>
          <div className="engines" aria-label="Detection engines">
            {ENGINES.map(([name, c]) => (
              <span key={name}><i style={{ background: live ? c : 'var(--sev-medium)' }} />{name}</span>
            ))}
          </div>
        </div>
        <div className="workspace-inner">{children}</div>
      </main>

      {open && <Palette setOpen={setOpen} go={go} alerts={list} />}
    </div>
  );
}
