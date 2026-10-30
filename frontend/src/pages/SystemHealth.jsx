import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Server, Database, GitBranch, BrainCircuit, Scale, Trees, UserCheck, Network, Link2, FolderKanban, MessageSquareText, RefreshCw } from 'lucide-react';
import { API_BASE, api, resetOffline } from '../api/client';
import { Panel } from '../components/ui';

const PROBES = [
  { key: 'health', path: '/health', label: 'FastAPI gateway', icon: Server },
  { key: 'dashboard', path: '/dashboard', label: 'Dashboard aggregator', icon: Database },
  { key: 'alerts', path: '/alerts', label: 'Alert store', icon: Database },
  { key: 'risk', path: '/risk', label: 'Risk profiles', icon: Database },
  { key: 'attackChains', path: '/attack-chains', label: 'Attack chain API', icon: Link2 },
  { key: 'cases', path: '/cases', label: 'Case API', icon: FolderKanban },
];

// Order matches analytics/pipeline/analytics_pipeline.py
const PIPELINE = [
  { label: 'State extraction', mod: 'state_extraction', icon: GitBranch },
  { label: 'CTMC scorer', mod: 'ctmc', icon: BrainCircuit },
  { label: 'Rule engine', mod: 'rule_engine', icon: Scale },
  { label: 'Isolation forest', mod: 'models/if_model.pkl', icon: Trees },
  { label: 'Personal baseline', mod: 'risk_scoring', icon: UserCheck },
  { label: 'Risk fusion', mod: 'risk_scorer', icon: Scale },
  { label: 'Attack chain engine', mod: 'attack_chain', icon: Link2 },
  { label: 'Case engine', mod: 'cases', icon: FolderKanban },
  { label: 'Explainer', mod: 'explainability', icon: MessageSquareText },
];

const TONE = { live: ['var(--sev-low)', 'Online'], not_exposed: ['var(--violet)', 'No route'], demo: ['var(--sev-critical)', 'Unreachable'] };

export default function SystemHealth() {
  const [probes, setProbes] = useState({});
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let alive = true;
    resetOffline();
    PROBES.forEach(async (p) => {
      const t0 = performance.now();
      const r = await api[p.key]();
      if (alive) setProbes((s) => ({ ...s, [p.key]: { source: r.source, ms: Math.round(performance.now() - t0) } }));
    });
    return () => { alive = false; };
  }, [tick]);

  const up = probes.health?.source === 'live';

  return (
    <div className="grid" style={{ gap: 14 }}>
      <Panel title="Service probes" sub={API_BASE}
        right={<button className="btn" onClick={() => { setProbes({}); setTick((t) => t + 1); }}><RefreshCw size={13} /> Re-probe</button>}>
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 10 }}>
          {PROBES.map(({ key, path, label, icon: Icon }) => {
            const pr = probes[key];
            const [color, word] = pr ? TONE[pr.source] : ['var(--tx-3)', 'Probing…'];
            return (
              <div key={key}
                style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 14, borderRadius: 0, background: 'var(--ink-1)', border: '1px solid var(--line)', borderLeft: `3px solid ${color}` }}>
                <Icon size={18} style={{ color }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="strong" style={{ fontWeight: 600 }}>{label}</div>
                  <div className="mono faint">GET {path}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ color, fontSize: 'var(--fs-sm)', fontWeight: 500, display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'flex-end' }}><span className="pulse" />{word}</div>
                  <div className="mono faint" style={{ fontSize: 'var(--fs-xs)' }}>{pr ? `${pr.ms} ms` : '…'}</div>
                </div>
              </div>
            );
          })}
        </div>
      </Panel>

      <Panel title="Analytics pipeline" sub="V2.1 · per-session inference path" delay={0.1}>
        <div style={{ display: 'flex', alignItems: 'stretch', gap: 0, overflowX: 'auto', paddingBottom: 6 }}>
          {PIPELINE.map(({ label, mod, icon: Icon }, i) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center' }}>
              <div
                style={{ width: 140, padding: 12, background: 'var(--ink-2)', border: '1px solid var(--rule)', borderTop: `4px solid ${up ? 'var(--accent)' : 'var(--ink-4)'}` }}>
                <Icon size={16} style={{ color: up ? 'var(--acid)' : 'var(--tx-2)' }} />
                <div className="strong" style={{ fontSize: 'var(--fs-md)', fontWeight: 600, marginTop: 8 }}>{label}</div>
                <div className="mono faint" style={{ fontSize: 'var(--fs-xs)', marginTop: 2, wordBreak: 'break-all' }}>{mod}</div>
              </div>
              {i < PIPELINE.length - 1 && (
                <div style={{ width: 28, height: 2, position: 'relative', background: 'var(--line-strong)', overflow: 'hidden' }}>
                  {up && <motion.i animate={{ x: [-10, 30] }} transition={{ repeat: Infinity, duration: 1.1, delay: i * 0.12, ease: 'linear' }}
                    style={{ position: 'absolute', width: 10, height: 2, background: 'var(--acid)' }} />}
                </div>
              )}
            </div>
          ))}
        </div>
        <p className="muted" style={{ margin: '14px 0 0', fontSize: 'var(--fs-md)' }}>
          Runs inside <span className="mono strong">POST /logs/user</span> on ingest. Network flows take the separate
          <span className="mono strong"> network_pipeline</span> path via <span className="mono strong">POST /logs/network</span>.
        </p>
      </Panel>

      <Panel title="Ingest-side coverage" delay={0.15}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Network size={18} style={{ color: 'var(--cyan)' }} />
          <span className="muted">SPEDIA telemetry carries session, file, email, HTTP, command and device activity — no packet-level flow data, so network analytics relies on uploaded flow CSVs.</span>
        </div>
      </Panel>
    </div>
  );
}
