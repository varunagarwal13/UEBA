import React from 'react';

export default function AlertDetail({ alert, onClose }) {
    if (!alert) return null;

    const timeStr = alert.created_at ? alert.created_at.replace('T', ' ').split('.')[0] : 'UNKNOWN_TIME';
    const rules = alert.rules_triggered ? alert.rules_triggered.split('|') : [];

    return (
        <div className="panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden' }}>

            {/* ALERT HEADER */}
            <div style={{ padding: '20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                        <span className={`badge ${alert.severity ? alert.severity.toLowerCase() : 'low'}`} style={{ fontSize: '11px' }}>{alert.severity}</span>
                        <span className="mono text-tertiary" style={{ fontSize: '11px' }}>{timeStr}</span>
                    </div>
                    <div className="mono" style={{ fontSize: '20px', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {alert.user_id}
                    </div>
                </div>
                <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                    <div className="text-secondary" style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '4px' }}>RISK SCORE</div>
                    <div className="mono semibold text-critical" style={{ fontSize: '24px' }}>{typeof alert.risk_score === 'number' ? alert.risk_score.toFixed(1) : 'U/A'}</div>
                </div>
            </div>

            {/* ALERT CONTENT */}
            <div style={{ padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '32px' }}>

                {/* EVIDENCE SUMMARY */}
                <div>
                    <div className="panel-title">Correlated Evidence Extract</div>
                    <div style={{ fontSize: '13px', lineHeight: 1.6, color: 'var(--text-secondary)' }}>
                        {alert.explanation || "No backend explanation explicitly persisted against this alert artifact."}
                    </div>
                </div>

                {/* HARD FACT BOUNDING */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>

                    {/* CTMC STATE */}
                    <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', padding: '12px', borderRadius: 'var(--radius-sm)' }}>
                        <div className="panel-title" style={{ marginBottom: '8px', border: 'none' }}>CTMC Evidence</div>
                        {alert.ctmc_log_prob != null ? (
                            <div className="mono semibold" style={{ color: 'var(--text-primary)' }}>
                                LOG PROB: <span>{typeof alert.ctmc_log_prob === 'number' ? alert.ctmc_log_prob.toFixed(4) : alert.ctmc_log_prob}</span>
                            </div>
                        ) : (
                            <div className="badge" style={{ background: 'transparent', border: '1px solid var(--border-subtle)', color: 'var(--text-tertiary)' }}>UNAVAILABLE</div>
                        )}
                    </div>

                    {/* BASELINE/IF (Simulated as missing endpoint) */}
                    <div style={{ background: 'var(--bg-base)', border: '1px solid var(--border-subtle)', padding: '12px', borderRadius: 'var(--radius-sm)' }}>
                        <div className="panel-title" style={{ marginBottom: '8px', border: 'none' }}>Isolation Forest</div>
                        <div className="badge" style={{ background: 'transparent', border: '1px solid var(--border-subtle)', color: 'var(--text-tertiary)' }}>UNAVAILABLE</div>
                    </div>
                </div>

                {/* RULES TRIGGERED */}
                <div>
                    <div className="panel-title">Detection Rule Execution</div>
                    {rules.length > 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {rules.map((rule, idx) => (
                                <div key={idx} style={{
                                    padding: '8px 12px',
                                    background: 'var(--bg-base)',
                                    borderLeft: '2px solid var(--risk-high)',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    fontSize: '12px',
                                    borderRadius: '0 var(--radius-sm) var(--radius-sm) 0'
                                }}>
                                    <span style={{ color: 'var(--text-primary)' }}>{rule}</span>
                                    <span className="mono" style={{ color: 'var(--risk-high)' }}>+10.0</span>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div style={{ fontSize: '12px', color: 'var(--text-tertiary)', fontStyle: 'italic' }}>
                            No heuristics triggered exclusively via Behavioral ML vectors.
                        </div>
                    )}
                </div>

            </div>

            {/* ACTION FOOTER */}
            <div style={{ marginTop: 'auto', padding: '16px 20px', borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'flex-end' }}>
                <button
                    onClick={onClose}
                    style={{
                        background: 'transparent', border: '1px solid var(--border-focus)', color: 'var(--text-primary)',
                        padding: '8px 16px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontFamily: 'var(--font-ui)', fontWeight: 600, fontSize: '12px', textTransform: 'uppercase'
                    }}
                >
                    Dismiss Context
                </button>
            </div>
        </div>
    );
}
