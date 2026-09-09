import React from 'react';
import { motion } from 'framer-motion';

export default function AttackChainGraph({ stage }) {
    const defaultStages = ['RECONNAISSANCE', 'AUTHENTICATION', 'DISCOVERY', 'STAGING', 'EXFILTRATION'];

    // Normalize stage string
    const activeStage = stage ? stage.toUpperCase() : 'UNKNOWN';
    let matchIdx = defaultStages.indexOf(activeStage);

    // If not in generic flow, append it for visual context mapping
    let renderStages = [...defaultStages];
    if (activeStage !== 'UNKNOWN' && matchIdx === -1) {
        renderStages.push(activeStage);
        matchIdx = renderStages.length - 1;
    }

    if (activeStage === 'UNKNOWN' || activeStage === 'ANOMALY') {
        return (
            <div style={{ color: 'var(--text-tertiary)', fontSize: '13px' }}>
                <span className="mono" style={{ letterSpacing: '0.5px' }}>ISOLATED_ANOMALY</span>
                <p style={{ marginTop: '4px', lineHeight: 1.5 }}>No longitudinal attack sequence mapped. Event evaluates independently of external phase matrices.</p>
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {renderStages.map((s, idx) => {
                const isActive = matchIdx >= idx;
                const isCurrent = matchIdx === idx;

                return (
                    <div key={s} style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '20px' }}>
                            <div style={{
                                width: '12px', height: '12px', borderRadius: '50%',
                                backgroundColor: isCurrent ? 'var(--risk-critical)' : isActive ? 'var(--risk-high)' : 'var(--border-subtle)',
                                boxShadow: isCurrent ? '0 0 8px var(--risk-critical)' : 'none'
                            }} />
                            {idx < renderStages.length - 1 && (
                                <div style={{ width: '2px', height: '24px', backgroundColor: isActive ? 'var(--risk-high)' : 'var(--border-subtle)', marginTop: '4px', marginBottom: '4px' }} />
                            )}
                        </div>
                        <span className="mono" style={{
                            fontSize: '12px',
                            color: isActive ? 'var(--text-primary)' : 'var(--text-tertiary)',
                            fontWeight: isActive ? 600 : 400
                        }}>
                            {s}
                        </span>
                    </div>
                );
            })}
        </div>
    );
}
