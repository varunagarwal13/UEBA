import React from 'react';

export default function UnavailableState({ title, detail }) {
    return (
        <div style={{ padding: '64px', border: '1px dashed var(--border-subtle)', borderRadius: '8px', textAlign: 'center', backgroundColor: 'var(--bg-app)', marginTop: '24px' }}>
            <div className="mono" style={{ color: 'var(--text-tertiary)', fontSize: '11px', letterSpacing: '1px', marginBottom: '12px' }}>TELEMETRY_UNAVAILABLE</div>
            <div style={{ fontSize: '18px', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: '8px' }}>{title}</div>
            <div style={{ fontSize: '14px', color: 'var(--text-tertiary)', maxWidth: '420px', margin: '0 auto', lineHeight: 1.6 }}>{detail}</div>
        </div>
    );
}
