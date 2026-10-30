import { useMemo, useState } from 'react';
import { PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer, Tooltip } from 'recharts';
import { Search } from 'lucide-react';
import { api, useResource } from '../api/client';
import { Panel, Sev, Entity, RiskBar, RiskRing, NotExposed, SkeletonRows, ChartTip } from '../components/ui';
import { ago, compact, int, n, stageLabel } from '../lib/format';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function Heatmap({ grid }) {
  const max = Math.max(1, ...grid.flat());
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '30px repeat(24, 1fr)', gap: 2 }}>
      <span />
      {Array.from({ length: 24 }, (_, h) => <span key={h} className="mono faint" style={{ fontSize: 'var(--fs-xs)', textAlign: 'center' }}>{h % 6 === 0 ? h : ''}</span>)}
      {grid.map((row, d) => [
        <span key={`l${d}`} className="mono faint" style={{ fontSize: 'var(--fs-xs)' }}>{DAYS[d]}</span>,
        ...row.map((v, h) => {
          const off = h < 7 || h > 20 || d >= 5;
          const k = v / max;
          return (
            <i key={`${d}-${h}`} title={`${DAYS[d]} ${h}:00 · ${v} events`}
              style={{ aspectRatio: '1', borderRadius: 0, background: k < 0.04 ? 'var(--ink-3)' : `color-mix(in oklch, ${off ? 'var(--sev-critical)' : 'var(--accent)'} ${Math.round(20 + k * 80)}%, var(--ink-2))` }} />
          );
        }),
      ])}
    </div>
  );
}

function Deviation({ label, s }) {
  const z = (s.current - s.mean) / (s.std || 1);
  const color = Math.abs(z) > 3 ? 'var(--sev-critical)' : Math.abs(z) > 2 ? 'var(--sev-high)' : 'var(--sev-low)';
  const pos = Math.max(0, Math.min(100, 50 + z * 8));
  return (
    <div style={{ padding: '10px 0', borderBottom: '1px solid var(--line)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <span style={{ fontSize: 'var(--fs-md)', color: 'var(--tx-1)' }}>{label}</span>
        <span className="mono" style={{ color }}>{z >= 0 ? '+' : ''}{n(z, 1)}σ</span>
      </div>
      <div style={{ position: 'relative', height: 6, borderRadius: 0, background: 'linear-gradient(90deg, var(--ink-4) 42%, color-mix(in oklch, var(--sev-low) 45%, var(--ink-2)) 42% 58%, var(--ink-4) 58%)' }}>
        <i style={{ position: 'absolute', left: '50%', top: -4, width: 2, height: 14, marginLeft: -1, background: 'var(--tx-0)' }} />
        <i style={{ position: 'absolute', left: `${pos}%`, top: -3, width: 12, height: 14, marginLeft: -6, borderRadius: 0, background: color, outline: '2px solid var(--ink-2)' }} />
      </div>
      <div className="mono faint" style={{ fontSize: 'var(--fs-xs)', marginTop: 6, display: 'flex', justifyContent: 'space-between' }}>
        <span>μ {n(s.mean)} · σ {n(s.std)}</span><span>{s.min != null ? 'peak' : 'now'} {n(s.current)}</span>
      </div>
    </div>
  );
}

function ProfilePanel({ userId, risk, go }) {
  const prof = useResource(() => api.profile(userId), [userId]);
  const p = prof.data;
  const radar = useMemo(() => (p ? Object.entries(p.state_distribution).map(([k, v]) => ({ k: stageLabel(k), v: +(v * 100).toFixed(1) })) : []), [p]);

  return (
    <div className="grid" style={{ alignContent: 'start' }}>
      <Panel delay={0.05}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
          <RiskRing value={risk?.latest_risk_score ?? 0} size={96} stroke={7} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <Entity id={userId} meta={risk ? `last seen ${ago(risk.last_seen)} ago` : ''} />
            <div className="grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginTop: 14 }}>
              {[['Peak', n(risk?.max_risk_score)], ['Alerts', `${risk?.open_alerts ?? 0}/${risk?.total_alerts ?? 0}`], ['Anomalous', `${int(risk?.anomaly_events)}`]].map(([k, v]) => (
                <div key={k}><div className="muted" style={{ fontSize: 'var(--fs-sm)' }}>{k}</div><div className="display strong" style={{ fontSize: 'var(--fs-lg)' }}>{v}</div></div>
              ))}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
          <button className="btn" onClick={() => go('alerts')}>Alerts</button>
          <button className="btn" onClick={() => go('attackChains', userId)}>Attack chain</button>
        </div>
      </Panel>

      {prof.source === 'empty' ? (
        <Panel title="Behaviour profile">
          <div className="notice"><span className="tag">No profile</span><span className="muted">No sessions have been profiled for this entity yet.</span></div>
        </Panel>
      ) : prof.source === 'not_exposed' ? (
        <Panel title="Behaviour profile"><NotExposed object="PersonalBehaviorProfile" route="/profiles/{user_id}" table="personal_behavior_profiles" /></Panel>
      ) : !p ? <Panel><SkeletonRows rows={6} /></Panel> : (
        <>
          <Panel title="CTMC state distribution" sub={`v${p.profile_version} · ${p.session_count} sessions · ${Math.round(p.confidence * 100)}% confidence`} delay={0.1}>
            <div style={{ height: 250 }}>
              <ResponsiveContainer>
                <RadarChart data={radar} outerRadius="74%">
                  <PolarGrid />
                  <PolarAngleAxis dataKey="k" tick={{ fontSize: 12 }} />
                  <Tooltip content={<ChartTip fmt={(v) => `${v}%`} />} />
                  <Radar dataKey="v" name="share" stroke="#3346ff" fill="#3346ff" fillOpacity={0.18} strokeWidth={2} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </Panel>
          <Panel title="Baseline deviation" sub={prof.source === 'live' ? 'Welford running stats · peak vs mean' : 'Welford running stats'} delay={0.14}>
            {Object.entries(p.statistics).slice(0, 6).map(([k, s]) => <Deviation key={k} label={stageLabel(k)} s={s} />)}
          </Panel>
          <Panel title="Activity rhythm" sub="hour × weekday · red = off-hours" delay={0.18}>
            <Heatmap grid={p.hourly} />
          </Panel>
        </>
      )}
    </div>
  );
}

export default function Users({ param, go }) {
  const res = useResource(api.risk, []);
  const [q, setQ] = useState('');
  if (res.loading && !res.data) return <Panel><SkeletonRows rows={10} /></Panel>;

  const all = Array.isArray(res.data) ? res.data : [];
  const rows = all.filter((r) => !q || r.user_id.toLowerCase().includes(q.toLowerCase()));
  const selId = param || all[0]?.user_id;

  return (
    <div className="grid" style={{ gridTemplateColumns: 'minmax(0, 1.7fr) minmax(380px, 1fr)', alignItems: 'start' }}>
      <Panel title="Monitored entities" sub={`${all.length} principals`} bodyClass="flush"
        right={<label className="field" style={{ width: 220 }}><Search size={13} /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Find entity" /></label>}>
        <div style={{ maxHeight: 'calc(100vh - 170px)', overflow: 'auto' }}>
          <table className="tbl">
            <thead><tr><th>Entity</th><th>Latest risk</th><th>Severity</th><th className="num">Open alerts</th><th className="num">Anomalous / total</th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.user_id} className={r.user_id === selId ? 'sel' : ''} onClick={() => go('users', r.user_id)}>
                  <td><Entity id={r.user_id} meta={`seen ${ago(r.last_seen)} ago`} /></td>
                  <td><RiskBar value={r.latest_risk_score} /></td>
                  <td><Sev level={r.severity} /></td>
                  <td className="num mono strong">{r.open_alerts}</td>
                  <td className="num mono">{int(r.anomaly_events)} <span className="faint">/ {compact(r.total_events)}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
      {selId && <ProfilePanel key={selId} userId={selId} risk={all.find((r) => r.user_id === selId)} go={go} />}
    </div>
  );
}
