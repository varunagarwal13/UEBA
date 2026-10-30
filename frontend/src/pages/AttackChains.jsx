import { api, useResource } from '../api/client';
import { Panel, Sev, Entity, NotExposed, SkeletonRows, RiskRing } from '../components/ui';
import AttackChainGraph from '../components/AttackChainGraph';
import { STAGES } from '../data/demo';
import { SEV_HEX, ago, n, sevOf, stamp, stageLabel, statusLabel } from '../lib/format';

export default function AttackChains({ param, go }) {
  const res = useResource(api.attackChains, []);

  if (res.loading && !res.data) return <Panel><SkeletonRows rows={8} /></Panel>;
  if (res.source === 'not_exposed') {
    return <Panel title="Attack chains"><NotExposed object="AttackChain" route="/attack-chains" table="attack_chains" /></Panel>;
  }

  const chains = res.data || [];
  const chain = chains.find((c) => c.chain_id === param || c.user_id === param) || chains[0];

  if (chains.length === 0) {
    return (
      <Panel title="Attack chains" sub="GET /attack-chains · 0 records">
        <div className="notice">
          <span className="tag cyan">No chains yet</span>
          <div className="display strong" style={{ fontSize: 'var(--fs-lg)' }}>No session has been mapped to a kill-chain stage</div>
          <div className="muted" style={{ maxWidth: 560, lineHeight: 1.6 }}>
            Chains are saved on <code>POST /logs/user</code> once <code>StageMapper</code> assigns a stage other than
            UNKNOWN. Alerts and cases still correlate without one.
          </div>
        </div>
      </Panel>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '320px minmax(0, 1fr)', gap: 14, height: 'calc(100vh - 96px)', minHeight: 520 }}>
      <Panel title="Chains" sub={`${chains.length} total · ${chains.filter((c) => c.status === 'OPEN').length} open`} bodyClass="flush" style={{ minHeight: 0 }}>
        <div style={{ height: '100%', overflowY: 'auto' }}>
        {chains.map((c) => {
          const hit = new Set(c.stages.map((s) => s.stage));
          const on = c.chain_id === chain?.chain_id;
          return (
            <button key={c.chain_id} onClick={() => go('attackChains', c.chain_id)}
              style={{ display: 'block', width: '100%', textAlign: 'left', padding: '12px 16px', border: 0, borderBottom: '1px solid var(--line)', cursor: 'pointer',
                background: on ? 'var(--accent-soft)' : 'none', boxShadow: on ? 'inset 3px 0 0 var(--acid)' : 'none' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <Entity id={c.user_id} meta={c.chain_id} />
                <span className="display" style={{ color: SEV_HEX[sevOf(c.risk_score)], fontSize: 'var(--fs-lg)' }}>{n(c.risk_score)}</span>
              </div>
              <div style={{ display: 'flex', gap: 3 }}>
                {STAGES.map((s, i) => (
                  <i key={s} title={s} style={{ flex: 1, height: 5, borderRadius: 0, background: hit.has(s) ? SEV_HEX[sevOf(25 + i * 11)] : 'var(--ink-4)' }} />
                ))}
              </div>
              <div className="faint" style={{ fontSize: 'var(--fs-sm)', marginTop: 8, display: 'flex', justifyContent: 'space-between' }}>
                <span>{stageLabel(c.current_stage)}</span><span>{statusLabel(c.status)} · {ago(c.last_seen)} ago</span>
              </div>
            </button>
          );
        })}
        </div>
      </Panel>

      {chain && (
        <div style={{ display: 'grid', gridTemplateRows: 'auto minmax(0, 1fr)', gap: 14, minHeight: 0 }}>
          <Panel delay={0.05}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
              <RiskRing value={chain.risk_score} size={92} stroke={7} />
              <div>
                <div className="mono faint" style={{ fontSize: 'var(--fs-xs)' }}>{chain.chain_id}</div>
                <div className="display strong" style={{ fontSize: 'var(--fs-xl)', margin: '2px 0 6px' }}>{chain.user_id}</div>
                <div style={{ display: 'flex', gap: 6 }}><Sev level={sevOf(chain.risk_score)} /><span className="tag">{statusLabel(chain.status)}</span></div>
              </div>
              {[
                ['Current stage', stageLabel(chain.current_stage)],
                ['Stages hit', `${chain.stages.length} / ${STAGES.length}`],
                ['Confidence', `${Math.round(chain.confidence * 100)}%`],
                ['Window', `${stamp(chain.first_seen).slice(0, 11)} → ${stamp(chain.last_seen).slice(6, 11)}`],
              ].map(([k, v]) => (
                <div key={k} style={{ paddingLeft: 20, borderLeft: '1px solid var(--line)' }}>
                  <div className="muted" style={{ fontSize: 'var(--fs-sm)' }}>{k}</div>
                  <div className="display strong" style={{ fontSize: 'var(--fs-lg)', marginTop: 4 }}>{v}</div>
                </div>
              ))}
              <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
                <button className="btn" onClick={() => go('users', chain.user_id)}>Entity profile</button>
                <button className="btn primary" onClick={() => go('investigations', chain.user_id)}>Open case</button>
              </div>
            </div>
          </Panel>
          <Panel title="Kill-chain progression" sub="drag to rearrange · scroll to zoom" bodyClass="flush" delay={0.1} style={{ minHeight: 0 }}>
            <div style={{ height: '100%', minHeight: 320 }}>
              <AttackChainGraph key={chain.chain_id} chain={chain} />
            </div>
          </Panel>
        </div>
      )}
    </div>
  );
}
