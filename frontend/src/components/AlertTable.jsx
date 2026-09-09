import React from 'react';

export default function AlertTable({ alerts, onSelect, activeId }) {
    return (
        <table className="data-table" style={{ borderCollapse: 'collapse', width: '100%' }}>
            <thead>
                <tr>
                    <th style={{ width: '20%' }}>TIMESTAMP</th>
                    <th style={{ width: '25%' }}>MONITORED ENTITY</th>
                    <th style={{ width: '15%' }}>SEV</th>
                    <th style={{ width: '15%' }}>RISK</th>
                    <th style={{ width: '25%' }}>PRIMARY TRIGGER</th>
                </tr>
            </thead>
            <tbody>
                {alerts.map(a => {
                    const isActive = a.alert_id === activeId;
                    const primaryRule = a.rules_triggered ? a.rules_triggered.split('|')[0] : 'ANOMALY DETECTED';
                    const timeStr = a.created_at ? a.created_at.replace('T', ' ').split('.')[0] : 'UNKNOWN_TIME';

                    return (
                        <tr
                            key={a.alert_id}
                            onClick={() => onSelect(a)}
                            style={{
                                backgroundColor: isActive ? 'var(--bg-panel-hover)' : 'transparent',
                                borderLeft: isActive ? '2px solid var(--risk-critical)' : '2px solid transparent'
                            }}
                        >
                            <td className="mono" style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>{timeStr}</td>
                            <td className="mono" style={{ color: 'var(--text-primary)' }}>{a.user_id}</td>
                            <td><span className={`badge ${a.severity ? a.severity.toLowerCase() : 'low'}`}>{a.severity}</span></td>
                            <td className="mono semibold" style={{ color: a.risk_score > 80 ? 'var(--risk-critical)' : a.risk_score > 50 ? 'var(--risk-high)' : 'var(--text-primary)' }}>
                                {typeof a.risk_score === 'number' ? a.risk_score.toFixed(1) : '0.0'}
                            </td>
                            <td style={{ fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                                {primaryRule.length > 20 ? primaryRule.substring(0, 20) + '...' : primaryRule}
                            </td>
                        </tr>
                    );
                })}
            </tbody>
        </table>
    );
}
