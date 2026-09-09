import React from 'react';
import UnavailableState from '../components/UnavailableState';

export default function Analytics() {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '1200px' }}>
            <div className="section-title">Model Contribution Analysis</div>
            <UnavailableState
                title="Explainability Metrics Missing"
                detail="The backend currently returns flat Risk Scores without transparent model attribution metadata. Evaluation endpoints for Welford/CTMC contributions are not exposed to the UI layer."
            />
        </div>
    );
}
