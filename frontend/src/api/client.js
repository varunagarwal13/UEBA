const API_BASE = 'http://localhost:8000';

export async function fetchAlerts() {
    try {
        const response = await fetch(`${API_BASE}/alerts`);
        if (!response.ok) throw new Error('API degraded');
        return await response.json();
    } catch (e) {
        return { error: 'UNAVAILABLE', details: e.message };
    }
}

export async function fetchHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        if (!response.ok) return { status: 'DEGRADED' };
        return await response.json();
    } catch {
        return { status: 'DEGRADED' };
    }
}

export async function fetchDashboard() {
    try {
        const response = await fetch(`${API_BASE}/dashboard`);
        if (!response.ok) throw new Error('API degraded');
        return await response.json();
    } catch (e) {
        return { error: 'UNAVAILABLE', details: e.message };
    }
}

export async function fetchRiskProfiles() {
    try {
        const response = await fetch(`${API_BASE}/risk`);
        if (!response.ok) throw new Error('API degraded');
        return await response.json();
    } catch (e) {
        return { error: 'UNAVAILABLE', details: e.message };
    }
}
