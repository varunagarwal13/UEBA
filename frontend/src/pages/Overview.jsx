import React, { useState, useEffect } from 'react';
import { fetchDashboard } from '../api/client';
import CapabilityState from '../components/CapabilityState';

export default function Overview({ setActiveTab }) {
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        let isMounted = true;
        const load = async () => {
            const data = await fetchDashboard();
            if (isMounted) {
                if (data.error === 'UNAVAILABLE') setError(true);
                else setMetrics(data);
                setLoading(false);
            }
        };
        load();
        const t = setInterval(load, 5000);
        return () => { isMounted = false; clearInterval(t); };
    }, []);

    if (loading) return <div style={{ color: 'var(--text-tertiary)', padding: '24px' }}>INITIALIZING TELEMETRY...</div>;

    if (error) {
        return <CapabilityState status="OFFLINE" componentName="TELEMETRY PIPELINE" reason="The backend /dashboard endpoint failed to respond." />;
    }

    // Prepare severity distribution visual bars
    const sevData = metrics.alerts_by_severity || {};
    const totalSelectedAlerts = Object.values(sevData).reduce((a, b) => a + b, 0) || 1;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', animation: 'fadeIn 300ms ease' }}>

            {/* TOP SYSTEM STRIP */}
            <div className="metric-strip animate-fade-in">
                <div className="metric-block">
                    <span className="metric-label">Monitored Identities</span>
                    <span className="metric-value">{metrics.total_users || 0}</span>
                </div>
                <div className="metric-block">
                    <span className="metric-label">Ingested Vectors</span>
                    <span className="metric-value">{metrics.total_events || 0}</span>
                </div>
                <div className="metric-block">
                    <span className="metric-label">Critical Incidents</span>
                    <span className="metric-value" style={{ color: 'var(--risk-critical)' }}>{metrics.critical_alerts || 0}</span>
                </div>
                <div className="metric-block">
                    <span className="metric-label">High Incidents</span>
                    <span className="metric-value" style={{ color: 'var(--risk-high)' }}>{metrics.high_alerts || 0}</span>
                </div>
                <div className="metric-block">
                    <span className="metric-label">Anomaly Rate</span>
                    <span className="metric-value mono">{metrics.anomaly_rate_pct?.toFixed(1) || 0}%</span>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 1fr) minmax(300px, 2fr)', gap: '24px' }}>
                {/* RISK LANDSCAPE */}
                <div className="panel" style={{ display: 'flex', flexDirection: 'column' }}>
                    <div className="panel-title">Active Alert Distribution</div>
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '16px', justifyContent: 'center' }}>
                        {['Critical', 'High', 'Medium', 'Low'].map(sev => {
                            const count = sevData[sev] || 0;
                            const pct = Math.round((count / totalSelectedAlerts) * 100);
                            const activeColor = `var(--risk-${sev.toLowerCase()})`;

                            return (
                                <div key={sev} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                                        <span>{sev}</span>
                                        <span className="mono">{count}</span>
                                    </div>
                                    <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--border-subtle)', borderRadius: '2px', overflow: 'hidden' }}>
                                        <div style={{ width: `${pct}%`, height: '100%', backgroundColor: activeColor, transition: 'width 500ms ease' }}></div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* HIGH-RISK ENTITY TRACKER */}
                <div className="panel" style={{ display: 'flex', flexDirection: 'column' }}>
                    <div className="panel-title">Highest Risk Entities (Watchlist)</div>
                    <div style={{ flex: 1, overflowX: 'auto' }}>
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Entity</th>
                                    <th>Risk</th>
                                    <th>Severity</th>
                                    <th>Events</th>
                                </tr>
                            </thead>
                            <tbody>
                                {metrics.top_risky_users && metrics.top_risky_users.length > 0 ? (
                                    metrics.top_risky_users.map(u => (
                                        <tr key={u.user_id} onClick={() => setActiveTab('users')}>
                                            <td className="mono">{u.user_id}</td>
                                            <td className="mono semibold text-high">{u.latest_risk_score?.toFixed(1) || '0.0'}</td>
                                            <td><span className={`badge ${u.severity?.toLowerCase()}`}>{u.severity}</span></td>
                                            <td className="mono">{u.anomaly_events}/{u.total_events}</td>
                                        </tr>
                                    ))
                                ) : (
                                    <tr>
                                        <td colSpan="4" style={{ textAlign: 'center', color: 'var(--text-tertiary)', padding: '32px' }}>
                                            No entities currently exceeding threshold bounds.
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}
