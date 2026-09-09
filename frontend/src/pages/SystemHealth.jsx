import React, { useState, useEffect } from 'react';
import { fetchHealth } from '../api/client';
import CapabilityState from '../components/CapabilityState';

export default function SystemHealth() {
    const [health, setHealth] = useState(null);

    useEffect(() => {
        let isMounted = true;
        const load = async () => {
            const h = await fetchHealth();
            if (isMounted) setHealth(h);
        };
        load();
    }, []);

    const isOnline = health?.status === 'ok';

    return (
        <div style={{ maxWidth: '1000px', display: 'flex', flexDirection: 'column', gap: '32px', animation: 'fadeIn 300ms ease', padding: '16px' }}>

            {/* SYSTEM HEALTH */}
            <div>
                <div style={{ color: 'var(--text-primary)', fontSize: '18px', fontWeight: 600, marginBottom: '24px', letterSpacing: '0.5px' }}>SYSTEM INFRASTRUCTURE</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>

                    <div className="panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <div className="mono text-tertiary" style={{ fontSize: '11px', marginBottom: '4px' }}>ROUTING & AGGREGATION</div>
                            <div className="semibold" style={{ color: 'var(--text-primary)' }}>FastAPI Gateway</div>
                        </div>
                        <span className={`badge ${isOnline ? 'low' : 'critical'}`} style={{ color: isOnline ? 'var(--status-normal)' : undefined, borderColor: isOnline ? 'var(--status-normal)' : undefined }}>
                            {isOnline ? 'ONLINE' : 'OFFLINE'}
                        </span>
                    </div>

                    <div className="panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <div className="mono text-tertiary" style={{ fontSize: '11px', marginBottom: '4px' }}>PERSISTENCE LAYER</div>
                            <div className="semibold" style={{ color: 'var(--text-primary)' }}>SQLite Database</div>
                        </div>
                        <span className={`badge ${isOnline ? 'low' : 'critical'}`} style={{ color: isOnline ? 'var(--status-normal)' : undefined, borderColor: isOnline ? 'var(--status-normal)' : undefined }}>
                            {isOnline ? 'ONLINE' : 'DEGRADED'}
                        </span>
                    </div>

                </div>
            </div>

            <hr style={{ border: 0, borderBottom: '1px solid var(--border-subtle)' }} />

            {/* ANALYTICS CAPABILITY */}
            <div>
                <div style={{ color: 'var(--text-primary)', fontSize: '18px', fontWeight: 600, marginBottom: '24px', letterSpacing: '0.5px' }}>ANALYTICS CAPABILITY</div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
                    <CapabilityState status={isOnline ? "AVAILABLE" : "DEGRADED"} componentName="Rule Engine" reason="Heuristic extraction is online." />
                    <CapabilityState status="API_NOT_EXPOSED" componentName="CTMC Dynamics" reason="Probabilities exist in Alert logs, but granular state arrays are missing dedicated endpoints." />
                    <CapabilityState status="API_NOT_EXPOSED" componentName="Welford Profiling" reason="Personal profiles track natively in DB but lack UI endpoints." />
                    <CapabilityState status="UNAVAILABLE" componentName="Network Analytics" reason="Underlying SPEDIA telemetry inherently lacks deep packet-flow data structures." />
                </div>
            </div>

        </div>
    );
}
