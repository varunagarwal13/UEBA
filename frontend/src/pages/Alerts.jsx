import { useMemo, useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import { Search, Inbox } from 'lucide-react';
import { api, useResource } from '../api/client';
import { Panel, Sev, Entity, RiskBar, SkeletonRows } from '../components/ui';
import AlertDetail from '../components/AlertDetail';
import { SEV_ORDER, ago, prettyRule, splitRules, stamp } from '../lib/format';

const NONE = [];

export default function Alerts({ param, go }) {
  const res = useResource(api.alerts, [], { poll: 8000 });
  const [q, setQ] = useState('');
  const [sev, setSev] = useState('ALL');
  const [status, setStatus] = useState('open');

  const alerts = Array.isArray(res.data) ? res.data : NONE;
  const selected = alerts.find((a) => String(a.alert_id) === String(param));

  const rows = useMemo(() => [...alerts].sort((x, y) => y.risk_score - x.risk_score || y.alert_id - x.alert_id).filter((a) => {
    if (sev !== 'ALL' && a.severity !== sev) return false;
    if (status !== 'all' && a.status !== status) return false;
    if (q) {
      const s = q.toLowerCase();
      return a.user_id?.toLowerCase().includes(s) || a.rules_triggered?.toLowerCase().includes(s) || String(a.alert_id).includes(s);
    }
    return true;
  }), [alerts, q, sev, status]);

  const counts = useMemo(() => Object.fromEntries(SEV_ORDER.map((s) => [s, alerts.filter((a) => a.severity === s && (status === 'all' || a.status === status)).length])), [alerts, status]);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: selected ? 'minmax(0, 1fr) minmax(380px, 520px)' : '1fr', gap: 14, height: '100%' }}>
      <Panel bodyClass="flush" style={{ minHeight: 0 }}
        title="Alert queue" sub={`${rows.length} shown`}
        right={
          <div className="seg">
            {['open', 'reviewed', 'closed', 'all'].map((s) => (
              <button key={s} className={status === s ? 'on' : ''} onClick={() => setStatus(s)}>{s}</button>
            ))}
          </div>
        }>
        <div style={{ display: 'flex', gap: 10, padding: 12, borderBottom: '1px solid var(--line)', flexWrap: 'wrap' }}>
          <label className="field" style={{ flex: '1 1 240px' }}>
            <Search size={14} />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter by entity, rule or alert id" />
          </label>
          <div className="seg">
            <button className={sev === 'ALL' ? 'on' : ''} onClick={() => setSev('ALL')}>All</button>
            {SEV_ORDER.map((s) => (
              <button key={s} className={sev === s ? 'on' : ''} onClick={() => setSev(s)}>
                {s} <span className="faint">{counts[s]}</span>
              </button>
            ))}
          </div>
        </div>
        <div style={{ overflow: 'auto', flex: 1, minHeight: 0, maxHeight: 'calc(100vh - 210px)' }}>
          {res.loading && !res.data ? <SkeletonRows rows={12} /> : rows.length === 0 ? (
            <div className="notice"><Inbox size={18} /><span className="muted">Queue is clear for this filter.</span></div>
          ) : (
            <table className="tbl">
              <thead>
                <tr><th style={{ width: 70 }}>ID</th><th>Entity</th><th>Severity</th><th>Risk</th><th>Primary signal</th><th>Status</th><th className="num">Raised</th></tr>
              </thead>
              <tbody>
                {rows.map((a) => {
                  const r = splitRules(a.rules_triggered);
                  return (
                    <tr key={a.alert_id} className={selected?.alert_id === a.alert_id ? 'sel' : ''}
                      onClick={() => go('alerts', selected?.alert_id === a.alert_id ? undefined : a.alert_id)}>
                      <td className="mono faint">#{a.alert_id}</td>
                      <td><Entity id={a.user_id} /></td>
                      <td><Sev level={a.severity} /></td>
                      <td><RiskBar value={a.risk_score} width={48} /></td>
                      <td style={{ maxWidth: 240 }}>
                        <span style={{ fontSize: 'var(--fs-md)', color: 'var(--tx-1)' }}>{r[0] ? prettyRule(r[0]) : 'Behavioural anomaly'}</span>
                        {r.length > 1 && <span className="tag" style={{ marginLeft: 6, padding: '0 5px' }}>+{r.length - 1}</span>}
                      </td>
                      <td><span style={{ fontSize: 'var(--fs-sm)', textTransform: 'capitalize', color: a.status === 'open' ? 'var(--accent-strong)' : 'var(--tx-3)' }}>{a.status}</span></td>
                      <td className="num mono faint" title={stamp(a.created_at)}>{ago(a.created_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </Panel>

      <AnimatePresence mode="wait">
        {selected && <AlertDetail key={selected.alert_id} alert={selected} go={go} onChanged={res.reload} />}
      </AnimatePresence>
    </div>
  );
}
