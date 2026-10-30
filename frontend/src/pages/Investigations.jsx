import { Workflow, Fingerprint } from 'lucide-react';
import { api, useResource } from '../api/client';
import { Panel, Sev, Entity, NotExposed, SkeletonRows, RiskBar } from '../components/ui';
import { SEV_HEX, ago, n, prettyRule, splitRules, stamp, stageLabel, statusLabel } from '../lib/format';

const LANES = [
  ['OPEN', 'var(--acid)'],
  ['INVESTIGATING', 'var(--sev-high)'],
  ['RESOLVED', 'var(--tx-3)'],
];

export default function Investigations({ param, go }) {
  const cases = useResource(api.cases, []);
  const al = useResource(api.alerts, []);

  if (cases.loading && !cases.data) return <Panel><SkeletonRows rows={8} /></Panel>;
  if (cases.source === 'not_exposed') {
    return <Panel title="Investigation cases"><NotExposed object="InvestigationCase" route="/cases" table="investigation_cases" /></Panel>;
  }

  const list = cases.data || [];
  const alerts = Array.isArray(al.data) ? al.data : [];
  const sel = list.find((c) => c.case_id === param || c.user_id === param) || list[0];
  const linked = sel ? alerts.filter((a) => (sel.alert_ids ? sel.alert_ids.includes(a.alert_id) : a.user_id === sel.user_id)) : [];

  return (
    <div className="grid" style={{ gridTemplateColumns: 'minmax(0, 1.2fr) minmax(360px, 1fr)', alignItems: 'start' }}>
      <div className="grid" style={{ gridTemplateColumns: 'repeat(3, minmax(0, 1fr))' }}>
        {LANES.map(([lane, color], li) => {
          const items = list.filter((c) => c.status === lane);
          return (
            <Panel key={lane} delay={li * 0.05} bodyClass="flush"
              title={<span style={{ display: 'flex', alignItems: 'center', gap: 8 }}><i style={{ width: 8, height: 8, background: color, borderRadius: 0 }} />{statusLabel(lane)}</span>}
              right={<span className="nav-count">{items.length}</span>}>
              <div style={{ padding: 10, display: 'flex', flexDirection: 'column', gap: 8, minHeight: 120 }}>
                {items.map((c) => {
                  const on = c.case_id === sel?.case_id;
                  return (
                    <button key={c.case_id} onClick={() => go('investigations', c.case_id)}
                      style={{ textAlign: 'left', padding: 12, borderRadius: 0, cursor: 'pointer', background: 'var(--ink-1)',
                        border: `1px solid ${on ? 'var(--acid)' : 'var(--line)'}`, boxShadow: on ? '0 0 0 3px var(--acid-dim)' : 'none' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                        <span className="mono faint" style={{ fontSize: 'var(--fs-xs)', whiteSpace: 'nowrap' }}>{c.case_id}</span><Sev level={c.severity} />
                      </div>
                      <Entity id={c.user_id} />
                      <div style={{ marginTop: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        {c.current_stage && c.current_stage !== 'UNKNOWN'
                          ? <span className="tag violet">{stageLabel(c.current_stage)}</span>
                          : <span className="tag">No stage</span>}
                        <span className="faint" style={{ fontSize: 'var(--fs-sm)' }}>{ago(c.updated_at)} ago</span>
                      </div>
                    </button>
                  );
                })}
                {items.length === 0 && <div className="faint" style={{ padding: 12, fontSize: 'var(--fs-sm)' }}>No cases</div>}
              </div>
            </Panel>
          );
        })}
      </div>

      {sel && (
        <Panel key={sel.case_id} title={sel.case_id} sub={`opened ${stamp(sel.created_at)}`} delay={0.1}
          right={<Sev level={sel.severity} />}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
            <Entity id={sel.user_id} meta={`${linked.length} correlated alerts`} />
            <RiskBar value={sel.risk_score} width={80} />
          </div>
          <p style={{ margin: '0 0 14px', color: 'var(--tx-0)', lineHeight: 1.6 }}>{sel.summary}</p>
          <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
            <button className="btn" disabled={!sel.chain_id} onClick={() => go('attackChains', sel.chain_id)}><Workflow size={13} /> Attack chain</button>
            <button className="btn" onClick={() => go('users', sel.user_id)}><Fingerprint size={13} /> Behaviour profile</button>
          </div>

          <div className="panel-title" style={{ fontSize: 'var(--fs-sm)', marginBottom: 12 }}>
            Evidence timeline {linked.length > 12 && <span className="panel-sub">latest 12 of {linked.length}</span>}
          </div>
          <div className="tl">
            {linked.length === 0 && <div className="faint">No alerts linked.</div>}
            {[...linked].sort((x, y) => y.alert_id - x.alert_id).slice(0, 12).map((a) => (
              <div className="tl-item" key={a.alert_id}>
                <i className="tl-dot" style={{ background: SEV_HEX[a.severity] }} />
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}>
                  <button onClick={() => go('alerts', a.alert_id)} className="mono strong" style={{ background: 'none', border: 0, padding: 0, cursor: 'pointer' }}>
                    #{a.alert_id} <span style={{ color: SEV_HEX[a.severity] }}>{n(a.risk_score)}</span>
                  </button>
                  <span className="mono faint">{stamp(a.created_at)}</span>
                </div>
                <div className="muted" style={{ fontSize: 'var(--fs-md)', marginTop: 3 }}>
                  {splitRules(a.rules_triggered).map(prettyRule).join(' · ') || 'Behavioural anomaly'}
                </div>
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}
