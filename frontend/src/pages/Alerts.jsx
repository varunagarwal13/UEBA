import React, { useState, useEffect } from 'react';
import { fetchAlerts } from '../api/client';
import AlertTable from '../components/AlertTable';
import AlertDetail from '../components/AlertDetail';
import CapabilityState from '../components/CapabilityState';

export default function Alerts() {
    const [alerts, setAlerts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);
    const [selectedAlert, setSelectedAlert] = useState(null);
    const [search, setSearch] = useState("");
    const [filterSev, setFilterSev] = useState("ALL");

    useEffect(() => {
        let isMounted = true;
        const load = async () => {
            const data = await fetchAlerts();
            if (isMounted) {
                if (data.error === 'UNAVAILABLE') setError(true);
                else setAlerts(data);
                setLoading(false);
            }
        };
        load();
        const t = setInterval(load, 5000);
        return () => { isMounted = false; clearInterval(t); };
    }, []);

    if (loading) return <div style={{ color: 'var(--text-tertiary)', padding: '24px' }}>INITIALIZING ACTIVE INVESTIGATIONS...</div>;

    if (error) {
        return <CapabilityState status="OFFLINE" componentName="DETECTION PIPELINE" reason="The backend /alerts endpoint failed to respond." />;
    }

    const filtered = alerts.filter(a => {
        if (filterSev !== "ALL" && a.severity !== filterSev) return false;
        if (search && !a.user_id?.toLowerCase().includes(search.toLowerCase()) &&
            !a.rules_triggered?.toLowerCase().includes(search.toLowerCase())) return false;
        return true;
    });

    return (
        <div style={{ display: 'flex', gap: '24px', height: '100%', overflow: 'hidden', animation: 'fadeIn 300ms ease' }}>

            {/* ALERT QUEUE */}
            <div style={{ flex: selectedAlert ? '1' : '1.5', display: 'flex', flexDirection: 'column', transition: 'flex 250ms ease-out', minWidth: '400px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px', gap: '16px' }}>
                    <input
                        type="text"
                        placeholder="Search entities or rules (Ctrl+K)..."
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        style={{ padding: '8px 12px', background: 'var(--bg-panel)', border: '1px solid var(--border-focus)', color: 'var(--text-primary)', outline: 'none', borderRadius: 'var(--radius-sm)', flex: 1, fontFamily: 'var(--font-ui)', fontSize: '13px' }}
                    />
                    <select
                        value={filterSev}
                        onChange={e => setFilterSev(e.target.value)}
                        style={{ padding: '8px 12px', background: 'var(--bg-panel)', border: '1px solid var(--border-focus)', color: 'var(--text-primary)', outline: 'none', borderRadius: 'var(--radius-sm)' }}
                    >
                        <option value="ALL">Severity: ALL</option>
                        <option value="Critical">Critical</option>
                        <option value="High">High</option>
                        <option value="Medium">Medium</option>
                        <option value="Low">Low</option>
                    </select>
                </div>

                <div className="panel" style={{ flex: 1, overflowY: 'auto', padding: 0 }}>
                    <div style={{ padding: '16px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-panel)' }}>
                        <div className="panel-title" style={{ margin: 0 }}>Active Alert Queue ({filtered.length})</div>
                    </div>
                    {filtered.length === 0 ? (
                        <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-tertiary)' }}>No alerts match current criteria.</div>
                    ) : (
                        <AlertTable alerts={filtered} onSelect={setSelectedAlert} activeId={selectedAlert?.alert_id} />
                    )}
                </div>
            </div>

            {/* INVESTIGATION DRAWER */}
            {selectedAlert && (
                <div className="animate-slide-in" style={{ flex: 1, minWidth: '350px', maxWidth: '600px', display: 'flex', flexDirection: 'column' }}>
                    <AlertDetail alert={selectedAlert} onClose={() => setSelectedAlert(null)} />
                </div>
            )}
        </div>
    );
}
