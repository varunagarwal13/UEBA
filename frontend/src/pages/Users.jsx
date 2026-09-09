import React, { useState, useEffect } from 'react';
import { fetchRiskProfiles } from '../api/client';
import CapabilityState from '../components/CapabilityState';

export default function Users() {
    const [profiles, setProfiles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        let isMounted = true;
        const load = async () => {
            const data = await fetchRiskProfiles();
            if (isMounted) {
                if (data.error === 'UNAVAILABLE' || !Array.isArray(data)) setError(true);
                else setProfiles(data);
                setLoading(false);
            }
        };
        load();
    }, []);

    if (loading) return <div style={{ color: 'var(--text-tertiary)', padding: '24px' }}>INITIALIZING ENTITY RISK VECTORS...</div>;
    if (error) return <CapabilityState status="OFFLINE" componentName="RISK CLASSIFICATION" reason="Unable to retrieve generic Risk Profiles. Backend /risk is failing." />;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', animation: 'fadeIn 300ms ease' }}>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ color: 'var(--text-primary)', fontSize: '20px', fontWeight: 600 }}>MONITORED ENTITIES</div>
                <div className="badge" style={{ border: '1px solid var(--border-focus)', background: 'transparent', color: 'var(--text-tertiary)' }}>SOURCE: /RISK</div>
            </div>

            <div className="metric-strip" style={{ marginBottom: '16px' }}>
                <CapabilityState status="API_NOT_EXPOSED" componentName="PERSONAL BEHAVIOR PROFILE" reason="Thorough V2.1 Welford Statistical Deviations exist natively in backend but currently lack API extraction routing." />
            </div>

            <div className="panel" style={{ overflowX: 'auto', padding: 0 }}>
                <table className="data-table">
                    <thead>
                        <tr>
                            <th>USER PRINCIPAL</th>
                            <th>INTENSITY SCORE</th>
                            <th>ALERTS</th>
                            <th>VECTORS</th>
                            <th>LAST ACTIVE</th>
                        </tr>
                    </thead>
                    <tbody>
                        {profiles.map(p => (
                            <tr key={p.user_id}>
                                <td className="mono" style={{ color: 'var(--text-primary)' }}>{p.user_id}</td>
                                <td className="mono semibold text-high">{p.latest_risk_score?.toFixed(1) || '0.0'}</td>
                                <td className="mono">{p.open_alerts} Open</td>
                                <td className="mono">{p.anomaly_events} / {p.total_events}</td>
                                <td className="mono text-tertiary" style={{ fontSize: '11px' }}>{p.last_seen ? p.last_seen.replace('T', ' ').split('.')[0] : 'UNKNOWN_TIME'}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

        </div>
    );
}
