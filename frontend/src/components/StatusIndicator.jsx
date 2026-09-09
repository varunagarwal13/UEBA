import React from 'react';

export default function StatusIndicator({ state, label }) {
    let colorClass, iconLabel;
    switch (state) {
        case 'ONLINE':
            colorClass = 'var(--risk-low)';
            iconLabel = 'OPERATIONAL';
            break;
        case 'DEGRADED':
            colorClass = 'var(--risk-medium)';
            iconLabel = 'DEGRADED';
            break;
        case 'UNAVAILABLE':
            colorClass = 'var(--text-tertiary)';
            iconLabel = 'UNAVAILABLE';
            break;
        case 'ERROR':
            colorClass = 'var(--risk-critical)';
            iconLabel = 'FAILING';
            break;
        default:
            colorClass = 'var(--text-tertiary)';
            iconLabel = 'UNKNOWN';
    }

    return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px', borderBottom: '1px solid var(--border-subtle)' }}>
            <span style={{ fontWeight: 500 }}>{label}</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="mono" style={{ color: colorClass, fontSize: '11px', letterSpacing: '0.5px' }}>{iconLabel}</span>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: colorClass, boxShadow: state === 'ONLINE' ? '0 0 6px var(--risk-low)' : 'none' }}></div>
            </div>
        </div>
    );
}
