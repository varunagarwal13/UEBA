import React from 'react';
import CapabilityState from '../components/CapabilityState';

export default function AttackChains() {
    return (
        <div style={{ padding: '24px', maxWidth: '800px', animation: 'fadeIn 300ms ease' }}>
            <div className="section-title" style={{ color: 'var(--text-primary)', fontSize: '20px', fontWeight: 600, marginBottom: '24px' }}>
                Attack Chain Intelligence
            </div>

            <div className="panel" style={{ display: 'flex', flexDirection: 'column', gap: '32px', padding: '32px' }}>
                <CapabilityState
                    status="API_NOT_EXPOSED"
                    componentName="LONGITUDINAL SEQUENCE ENGINE"
                    reason="AttackChain objects are fully materialized in backend V2.1, but public route serialization is currently missing prohibiting explicit visual sequence rendering."
                />
            </div>
        </div>
    );
}
