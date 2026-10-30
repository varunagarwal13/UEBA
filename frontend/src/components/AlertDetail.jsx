import { useState } from 'react';
import { toast } from 'sonner';
import { X, CheckCheck, Archive, RotateCcw, Fingerprint, Workflow, BrainCircuit, ScrollText } from 'lucide-react';
import { api } from '../api/client';
import { Sev, Avatar, RiskRing } from './ui';
import { n, prettyRule, splitRules, stamp } from '../lib/format';

const METHOD_TONE = { CTMC: 'violet', Rules: 'acid', Isolation_Forest: 'cyan', Personal_Baseline: 'cyan', Network_Heuristics: 'cyan' };

function parseExplanation(text) {
  if (!text) return { summary: null, methods: [] };
  const [summary, det] = text.split('| Detections:');
  return { summary: summary.trim(), methods: det ? det.split(',').map((s) => s.trim()).filter(Boolean) : [] };
}

export default function AlertDetail({ alert, go, onChanged }) {
  const [busy, setBusy] = useState(false);
  const rules = splitRules(alert.rules_triggered);
  const { summary, methods } = parseExplanation(alert.explanation);
  // The V2 pipeline writes its 0–100 CTMC anomaly score into ctmc_log_prob; older rows hold a
  // negative log-likelihood, which we map −20..0 onto 100..0.
  const ctmc = alert.ctmc_log_prob;
  const isScore = ctmc != null && ctmc >= 0;
  const surprise = ctmc == null ? null : isScore ? Math.min(100, ctmc) : Math.min(100, Math.max(0, (-ctmc / 20) * 100));

  async function setStatus(status) {
    setBusy(true);
    const res = await api.setAlertStatus(alert.alert_id, status);
    setBusy(false);
    if (res.source === 'not_exposed') return toast.error('Status endpoint not available');
    toast.success(`Alert #${alert.alert_id} marked ${status}`, { description: res.source === 'demo' ? 'Demo dataset — change is local only' : 'Persisted to backend' });
    onChanged?.();
  }

  return (
    <aside className="panel drawer" style={{ minHeight: 0, maxHeight: 'calc(100vh - 96px)' }}>
      <header className="panel-head">
        <span className="panel-title">Alert #{alert.alert_id}</span>
        <span className="panel-sub">{stamp(alert.created_at)} UTC</span>
        <div className="right"><button className="btn ghost" onClick={() => go('alerts')} aria-label="Close"><X size={15} /></button></div>
      </header>

      <div style={{ overflow: 'auto', flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 18, padding: 18, borderBottom: '1px solid var(--line)' }}>
          <RiskRing value={alert.risk_score} size={104} stroke={8} />
          <div style={{ minWidth: 0, flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
              <Avatar id={alert.user_id} size={32} />
              <div>
                <div className="strong" style={{ fontSize: 'var(--fs-lg)', fontWeight: 600 }}>{alert.user_id}</div>
                <div style={{ display: 'flex', gap: 6, marginTop: 4 }}><Sev level={alert.severity} /><span className="tag" style={{ textTransform: 'capitalize' }}>{alert.status}</span></div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              <button className="btn" onClick={() => go('users', alert.user_id)}><Fingerprint size={13} /> Profile</button>
              <button className="btn" onClick={() => go('attackChains', alert.user_id)}><Workflow size={13} /> Chain</button>
            </div>
          </div>
        </div>

        <section style={{ padding: 18, borderBottom: '1px solid var(--line)' }}>
          <div className="panel-title" style={{ fontSize: 'var(--fs-sm)', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}><ScrollText size={13} /> Explainer narrative</div>
          <p style={{ margin: 0, color: 'var(--tx-0)', fontSize: 'var(--fs-base)', lineHeight: 1.6 }}>
            {summary || <span className="faint">No explanation persisted for this alert.</span>}
          </p>
          {methods.length > 0 && (
            <div style={{ display: 'flex', gap: 6, marginTop: 12, flexWrap: 'wrap' }}>
              {methods.map((m) => <span key={m} className={`tag ${METHOD_TONE[m] || ''}`}>{m.replace(/_/g, ' ')}</span>)}
            </div>
          )}
        </section>

        <section style={{ padding: 18, borderBottom: '1px solid var(--line)' }}>
          <div className="panel-title" style={{ fontSize: 'var(--fs-sm)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}><BrainCircuit size={13} /> Model evidence</div>
          <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div style={{ padding: 12, background: 'var(--ink-1)', border: '1px solid var(--line)', borderRadius: 0 }}>
              <div className="muted" style={{ fontSize: 'var(--fs-sm)' }}>{isScore ? 'CTMC anomaly score' : 'CTMC log-likelihood'}</div>
              {surprise != null ? (
                <>
                  <div className="display" style={{ fontSize: 'var(--fs-xl)', color: 'var(--violet)', margin: '6px 0' }}>{n(ctmc, isScore ? 1 : 3)}</div>
                  <div className="bar"><i style={{ width: `${surprise}%`, background: 'var(--violet)' }} /></div>
                  <div className="faint" style={{ fontSize: 'var(--fs-sm)', marginTop: 6 }}>Surprise {Math.round(surprise)} of 100</div>
                </>
              ) : <div className="faint" style={{ marginTop: 8 }}>Not recorded</div>}
            </div>
            <div style={{ padding: 12, background: 'var(--ink-1)', border: '1px solid var(--line)', borderRadius: 0 }}>
              <div className="muted" style={{ fontSize: 'var(--fs-sm)' }}>Rules fired</div>
              <div className="display" style={{ fontSize: 'var(--fs-xl)', color: 'var(--acid)', margin: '6px 0' }}>{rules.length}</div>
              <div style={{ display: 'flex', gap: 3 }}>{Array.from({ length: 6 }, (_, i) => <i key={i} style={{ flex: 1, height: 4, borderRadius: 0, background: i < rules.length ? 'var(--acid)' : 'var(--ink-4)' }} />)}</div>
              <div className="faint" style={{ fontSize: 'var(--fs-sm)', marginTop: 6 }}>Heuristic layer</div>
            </div>
          </div>
        </section>

        <section style={{ padding: 18 }}>
          <div className="panel-title" style={{ fontSize: 'var(--fs-sm)', marginBottom: 10 }}>Rule trace</div>
          {rules.length ? rules.map((r, i) => (
            <div key={r} style={{ display: 'grid', gridTemplateColumns: '18px 1fr auto', alignItems: 'center', gap: 10, padding: '9px 0', borderBottom: '1px dashed var(--line)' }}>
              <span className="mono faint">{String(i + 1).padStart(2, '0')}</span>
              <span style={{ color: 'var(--tx-0)' }}>{prettyRule(r)}</span>
              <span className="faint" style={{ fontSize: 'var(--fs-sm)' }}>matched</span>
            </div>
          )) : <div className="faint">Flagged by behavioural models only — no heuristic rule matched.</div>}
        </section>
      </div>

      <footer style={{ display: 'flex', gap: 8, padding: 14, borderTop: '1px solid var(--line)' }}>
        {alert.status !== 'open' ? (
          <button className="btn" disabled={busy} onClick={() => setStatus('open')}><RotateCcw size={13} /> Reopen</button>
        ) : (
          <>
            <button className="btn primary" disabled={busy} onClick={() => setStatus('reviewed')}><CheckCheck size={14} /> Mark reviewed</button>
            <button className="btn" disabled={busy} onClick={() => setStatus('closed')}><Archive size={13} /> Close</button>
          </>
        )}
      </footer>
    </aside>
  );
}
