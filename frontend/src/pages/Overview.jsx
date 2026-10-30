import { useMemo } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, Cell } from 'recharts';
import { Users as UsersIcon, Database, Siren, Flame, Percent, ArrowUpRight } from 'lucide-react';
import { api, useResource } from '../api/client';
import { Panel, Sev, Entity, RiskBar, RiskRing, ChartTip, SkeletonRows } from '../components/ui';
import { SEV_ORDER, SEV_HEX, ago, compact, int, n, prettyRule, sevOf, splitRules } from '../lib/format';

const NONE = [];

// Alerts per 10-point risk band. Independent of ingest timing, unlike a time series,
// so a bulk upload still shows how risk is spread.
function riskBands(alerts) {
  const rows = Array.from({ length: 10 }, (_, i) => ({ band: `${i * 10}–${i * 10 + 9}`, lo: i * 10, alerts: 0 }));
  for (const a of alerts) rows[Math.min(9, Math.floor((a.risk_score ?? 0) / 10))].alerts += 1;
  return rows;
}

function Kpi({ icon: Icon, label, value, suffix, delta, color, i }) {
  return (
    <Panel delay={i * 0.04} bodyClass="kpi">
      <div className="kpi-label"><Icon size={16} style={{ color }} /> {label}</div>
      <div className="kpi-value" style={{ color: color === 'var(--sev-critical)' ? color : undefined }}>
        {value}{suffix && <small>{suffix}</small>}
      </div>
      <div className="kpi-delta faint">{delta}</div>
    </Panel>
  );
}

export default function Overview({ go }) {
  const dash = useResource(api.dashboard, [], { poll: 10000 });
  const al = useResource(api.alerts, [], { poll: 10000 });

  const alerts = Array.isArray(al.data) ? al.data : NONE;
  const m = dash.data;
  const bands = useMemo(() => riskBands(alerts), [alerts]);

  const rules = useMemo(() => {
    const c = {};
    alerts.forEach((a) => splitRules(a.rules_triggered).forEach((r) => { c[r] = (c[r] || 0) + 1; }));
    return Object.entries(c).sort((a, b) => b[1] - a[1]).slice(0, 8);
  }, [alerts]);

  if (!m) return <Panel><SkeletonRows rows={10} /></Panel>;

  const sev = m.alerts_by_severity || {};
  const sevTotal = SEV_ORDER.reduce((s, k) => s + (sev[k] || 0), 0) || 1;
  const top = m.top_risky_users || [];
  const posture = top.length ? top.slice(0, 5).reduce((s, u) => s + u.latest_risk_score, 0) / Math.min(5, top.length) : 0;
  const titleCase = (k) => k.toLowerCase().replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
  const events = Object.entries(m.events_by_type || {}).sort((a, b) => b[1] - a[1]).slice(0, 8)
    .map(([k, v]) => ({ k: titleCase(k), v }));

  return (
    <div className="grid">
      <div className="kpis">
        <Kpi i={0} icon={UsersIcon} label="Monitored identities" value={int(m.total_users)} delta={`${top.length} on watchlist`} color="var(--cyan)" />
        <Kpi i={1} icon={Database} label="Events ingested" value={compact(m.total_events)} delta={`${Object.keys(m.events_by_type || {}).length} event types`} color="var(--violet)" />
        <Kpi i={2} icon={Siren} label="Open alerts" value={int(m.open_alerts)} delta={`of ${int(m.total_alerts)} raised`} color="var(--accent-strong)" />
        <Kpi i={3} icon={Flame} label="Critical alerts" value={int(m.critical_alerts)} delta={`plus ${int(m.high_alerts)} high severity`} color="var(--sev-critical)" />
        <Kpi i={4} icon={Percent} label="Anomalous events" value={n(m.anomaly_rate_pct, 1)} suffix="%" delta="of all ingested events" color="var(--sev-medium)" />
      </div>

      <div className="grid" style={{ gridTemplateColumns: 'minmax(0, 2fr) minmax(320px, 1fr)' }}>
        <Panel title="Risk distribution" sub={`${int(alerts.length)} alerts by risk score`} delay={0.1}>
          <div style={{ height: 280 }}>
            <ResponsiveContainer>
              <BarChart data={bands} barCategoryGap={6} margin={{ top: 8, right: 4, bottom: 0, left: -12 }}>
                <CartesianGrid vertical={false} strokeDasharray="3 5" />
                <XAxis dataKey="band" tickLine={false} axisLine={false} />
                <YAxis tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip content={<ChartTip fmt={int} />} />
                <Bar dataKey="alerts" name="alerts" radius={0}>
                  {bands.map((b) => <Cell key={b.band} fill={SEV_HEX[sevOf(b.lo + 5)]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Threat posture" sub="mean risk of top 5 entities" delay={0.14}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 24, marginBottom: 20 }}>
            <RiskRing value={posture} size={128} label="posture" />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <span className="muted" style={{ fontSize: 'var(--fs-sm)' }}>Elevated entities</span>
              <span className="display strong" style={{ fontSize: 'var(--fs-2xl)' }}>{top.filter((u) => u.latest_risk_score >= 65).length}</span>
              <span className="muted" style={{ fontSize: 'var(--fs-sm)' }}>risk 65 or above</span>
            </div>
          </div>
          <div style={{ display: 'flex', height: 8, gap: 3, marginBottom: 12 }}>
            {SEV_ORDER.map((s) => (
              <i key={s}
                style={{ flexGrow: (sev[s] || 0) / sevTotal, background: SEV_HEX[s], flexBasis: 0, minWidth: sev[s] ? 6 : 0, borderRadius: 0 }} />
            ))}
          </div>
          {SEV_ORDER.map((s) => (
            <div key={s} style={{ display: 'flex', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--line)' }}>
              <Sev level={s} />
              <span className="strong" style={{ marginLeft: 'auto', fontWeight: 600 }}>{int(sev[s] || 0)}</span>
              <span className="faint" style={{ width: 52, textAlign: 'right', fontSize: 'var(--fs-sm)' }}>{Math.round(((sev[s] || 0) / sevTotal) * 100)}%</span>
            </div>
          ))}
        </Panel>
      </div>

      <div className="grid" style={{ gridTemplateColumns: 'minmax(0, 1.6fr) minmax(0, 1fr)' }}>
        <Panel title="Watchlist" sub="ranked by latest risk" bodyClass="flush" delay={0.18}
          right={<button className="btn ghost" onClick={() => go('users')}>All entities <ArrowUpRight size={15} /></button>}>
          <table className="tbl">
            <thead><tr><th>Entity</th><th>Risk</th><th>Severity</th><th className="num">Open alerts</th><th className="num">Anomalous events</th></tr></thead>
            <tbody>
              {top.map((u) => (
                <tr key={u.user_id} onClick={() => go('users', u.user_id)}>
                  <td><Entity id={u.user_id} meta={`last seen ${ago(u.last_seen)} ago`} /></td>
                  <td><RiskBar value={u.latest_risk_score} width={90} /></td>
                  <td><Sev level={u.severity} /></td>
                  <td className="num">{int(u.open_alerts)}</td>
                  <td className="num">{int(u.anomaly_events)} <span className="faint">/ {compact(u.total_events)}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        <Panel title="Latest detections" sub={al.source === 'live' ? 'refreshes every 10s' : 'sample data'} bodyClass="flush" delay={0.22}>
          <div style={{ maxHeight: 520, overflow: 'auto' }}>
            {alerts.slice(0, 10).map((a) => (
              <button key={a.alert_id} onClick={() => go('alerts', a.alert_id)}
                style={{ display: 'grid', gridTemplateColumns: '4px 1fr auto', gap: 14, width: '100%', padding: '12px 20px', border: 0, borderBottom: '1px solid var(--line)', background: 'none', cursor: 'pointer', textAlign: 'left' }}>
                <i style={{ background: SEV_HEX[a.severity], borderRadius: 0 }} />
                <span style={{ minWidth: 0 }}>
                  <span className="strong" style={{ fontWeight: 500 }}>{a.user_id}</span>
                  <span className="muted" style={{ display: 'block', fontSize: 'var(--fs-sm)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {splitRules(a.rules_triggered).map(prettyRule).join(' · ') || 'Behavioural anomaly'}
                  </span>
                </span>
                <span style={{ textAlign: 'right' }}>
                  <span className="strong" style={{ color: SEV_HEX[a.severity], display: 'block', fontWeight: 600 }}>{n(a.risk_score)}</span>
                  <span className="faint" style={{ fontSize: 'var(--fs-xs)' }}>{ago(a.created_at)} ago</span>
                </span>
              </button>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid" style={{ gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)' }}>
        <Panel title="Event mix" sub="ingested events by type" delay={0.26}>
          <div style={{ height: 260 }}>
            <ResponsiveContainer>
              <BarChart data={events} layout="vertical" margin={{ top: 0, right: 12, bottom: 0, left: 0 }} barCategoryGap={6}>
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="k" width={110} tickLine={false} axisLine={false} />
                <Tooltip content={<ChartTip fmt={int} />} />
                <Bar dataKey="v" name="events" radius={0} fill="#3346ff" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Most frequent rules" sub="across all alerts" delay={0.3}>
          {rules.length === 0 && <div className="faint">No rules fired.</div>}
          {rules.map(([r, c]) => (
            <div key={r} style={{ display: 'grid', gridTemplateColumns: '1fr 120px 48px', alignItems: 'center', gap: 14, padding: '7px 0' }}>
              <span style={{ color: 'var(--tx-1)' }}>{prettyRule(r)}</span>
              <span className="bar"><i style={{ width: `${(c / rules[0][1]) * 100}%`, background: 'var(--accent)' }} /></span>
              <span className="strong" style={{ textAlign: 'right', fontWeight: 600 }}>{int(c)}</span>
            </div>
          ))}
        </Panel>
      </div>
    </div>
  );
}
