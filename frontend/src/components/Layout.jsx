import React, { useState, useEffect } from 'react';

export default function Layout({ activeTab, setActiveTab, children }) {
    const [time, setTime] = useState(new Date().toISOString());

    useEffect(() => {
        const timer = setInterval(() => setTime(new Date().toISOString()), 1000);
        return () => clearInterval(timer);
    }, []);

    const tabs = [
        { id: 'overview', label: 'Command Center' },
        { id: 'alerts', label: 'Alerts' },
        { id: 'investigations', label: 'Investigations' },
        { id: 'attackChains', label: 'Attack Chains' },
        { id: 'users', label: 'Users' },
        { id: 'health', label: 'System Health' }
    ];

    return (
        <div className="app-frame">
            {/* LEFT SIDEBAR */}
            <div className="sidebar">
                <div className="sidebar-header">
                    <span style={{ color: 'var(--text-primary)' }}>UEBA V2.1 // </span>
                    <span style={{ color: 'var(--text-tertiary)', marginLeft: '6px' }}>SOC</span>
                </div>
                <div className="sidebar-nav">
                    {tabs.map(t => (
                        <div
                            key={t.id}
                            className={`nav-item ${activeTab === t.id ? 'active' : ''}`}
                            onClick={() => setActiveTab(t.id)}
                            role="button"
                            tabIndex={0}
                        >
                            {t.label}
                        </div>
                    ))}
                </div>
            </div>

            {/* MAIN CONTENT AREA */}
            <div className="main-content">
                <div className="top-bar">
                    <div className="top-bar-stats">
                        <div className="stat-item">
                            <div className="status-dot online"></div>
                            SYSTEM: ONLINE
                        </div>
                        <div className="stat-item">
                            <div className="status-dot online"></div>
                            API: ONLINE
                        </div>
                        <div className="stat-item">
                            <div className="status-dot offline"></div>
                            ISOLATION FOREST: UNAVAILABLE
                        </div>
                    </div>
                    <div className="stat-item mono">
                        {time.split('T')[1].split('.')[0]} UTC
                    </div>
                </div>

                <div className="workspace animate-fade-in">
                    {children}
                </div>
            </div>
        </div>
    );
}
