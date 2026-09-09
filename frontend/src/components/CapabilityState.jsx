import React from 'react';

const CapabilityState = ({ status, componentName, reason }) => {
    // status: "AVAILABLE", "DEGRADED", "UNAVAILABLE", "API_NOT_EXPOSED", "OFFLINE"

    let colorVar = "var(--status-unavailable)";
    if (status === "API_NOT_EXPOSED") colorVar = "var(--text-tertiary)";
    if (status === "DEGRADED") colorVar = "var(--status-degraded)";
    if (status === "UNAVAILABLE") colorVar = "var(--status-unavailable)";
    if (status === "OFFLINE") colorVar = "var(--risk-critical)";

    return (
        <div className="capability-box animate-fade-in">
            <div className="capability-title" style={{ color: colorVar }}>
                {componentName}
            </div>
            <div className="capability-label" style={{ color: colorVar, borderColor: colorVar }}>
                {status.replace(/_/g, ' ')}
            </div>
            {reason && (
                <div style={{ maxWidth: '400px', fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                    {reason}
                </div>
            )}
        </div>
    );
};

export default CapabilityState;
