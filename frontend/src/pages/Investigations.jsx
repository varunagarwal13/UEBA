import React from 'react';
import CapabilityState from '../components/CapabilityState';

export default function Investigations() {
    return (
        <div style={{ padding: '24px', maxWidth: '800px', animation: 'fadeIn 300ms ease' }}>
            <div className="section-title" style={{ color: 'var(--text-primary)', fontSize: '20px', fontWeight: 600, marginBottom: '24px' }}>
                Investigation Workspace
            </div>

            <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '32px', padding: '32px' }}>
                <CapabilityState
                    status="API_NOT_EXPOSED"
                    componentName="CASE CORRELATION ENGINE"
                    reason="Backend internal model InvestigationCase explicitly exists in persistence, but no frontend-consumable REST API endpoint schema is currently exposed for telemetry extraction."
                />
            </div>
        </div>
    );
}
