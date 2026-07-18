const API_BASE = typeof window !== 'undefined' 
    ? (window.location.port === '3000' ? 'http://localhost:8080' : '') 
    : 'http://localhost:8080';

export interface SimulatorStatus {
    initialized: boolean;
    processed: number;
    total_test_sessions: number;
    current_index: number;
    tp: number;
    fp: number;
    tn: number;
    fn: number;
    precision: number;
    recall: number;
    f1_score: number;
    alerts_generated: number;
    auto_run: boolean;
}

export interface RuleViolation {
    rule_id: string;
    rule_name: string;
    severity: string;
}

export interface ExplanationPayload {
    summary: string;
    reasons: string[];
    recommended_actions: string[];
    risk_context: string;
    detection_methods: string[];
}

export interface TimelinePayload {
    timeline: string[];
    timeline_compact: string[];
}

export interface PipelineTrace {
    session_id: string;
    event_count: number;
    states: string[];
    ctmc_score: number;
    rules_checked: number;
    rule_score: number;
    rule_violations: RuleViolation[];
    final_risk_score: number;
    severity: string;
    confidence: number;
    alert_id: string | null;
    explanation: ExplanationPayload;
    timeline: TimelinePayload;
}

export interface SimulationStepResponse {
    status: string;
    session_id: string;
    user_id: string;
    ground_truth: number;
    event_count: number;
    alert_triggered: boolean;
    pipeline_trace: PipelineTrace;
}

export interface Alert {
    alert_id: number;
    user_id: string;
    risk_score: number;
    severity: string;
    status: string;
    rules_triggered: string | null;
    created_at: string;
    explanation: Record<string, unknown> | string;
}

export interface RiskProfile {
    user_id: string;
    latest_risk_score: number;
    max_risk_score: number;
    severity: string;
    total_alerts: number;
    open_alerts: number;
    total_events: number;
    anomaly_events: number;
    last_seen: string | null;
}

export interface UserHistoryResponse {
    user_id: string;
    username: string;
    department: string | null;
    role: string | null;
    email: string | null;
    is_active: boolean;
    risk_profile: {
        latest_risk_score: number;
        max_risk_score: number;
        severity: string;
        total_alerts: number;
        open_alerts: number;
    } | null;
    total_events: number;
    alerts: {
        alert_id: number;
        risk_score: number;
        severity: string;
        status: string;
        rules_triggered: string | null;
        created_at: string;
    }[];
}

export interface ChartMetricsResponse {
    threat_trend: { date: string; count: number }[];
    risk_distribution: { range: string; count: number }[];
    severity_breakdown: { name: string; value: number }[];
    hourly_activity: { hour: string; events: number }[];
}

export async function fetchSimulatorStatus(): Promise<SimulatorStatus> {
    const res = await fetch(`${API_BASE}/simulator/status`);
    if (!res.ok) throw new Error("Failed to fetch simulator status");
    return res.json();
}

export async function stepSimulation(): Promise<SimulationStepResponse> {
    const res = await fetch(`${API_BASE}/simulator/step`, { method: 'POST' });
    if (!res.ok) throw new Error("Failed to step simulation");
    return res.json();
}

export async function resetSimulation(): Promise<{ status: string; message: string }> {
    const res = await fetch(`${API_BASE}/simulator/reset`, { method: 'POST' });
    if (!res.ok) throw new Error("Failed to reset simulation");
    return res.json();
}

export async function toggleAutoRun(): Promise<{ auto_run: boolean }> {
    const res = await fetch(`${API_BASE}/simulator/auto-run/toggle`, { method: 'POST' });
    if (!res.ok) throw new Error("Failed to toggle auto run");
    return res.json();
}

export async function fetchAlerts(severity?: string): Promise<Alert[]> {
    const url = severity 
        ? `${API_BASE}/alerts?severity=${severity}&limit=100`
        : `${API_BASE}/alerts?limit=100`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to fetch alerts");
    return res.json();
}

export async function fetchAlertDetail(alertId: number): Promise<Alert> {
    const res = await fetch(`${API_BASE}/alerts/${alertId}`);
    if (!res.ok) throw new Error(`Failed to fetch alert ${alertId}`);
    return res.json();
}

export async function updateAlertStatus(alertId: number, status: string): Promise<Alert> {
    const res = await fetch(`${API_BASE}/alerts/${alertId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
    });
    if (!res.ok) throw new Error("Failed to update alert status");
    return res.json();
}

export async function fetchRiskProfiles(): Promise<RiskProfile[]> {
    const res = await fetch(`${API_BASE}/risk?limit=10`);
    if (!res.ok) throw new Error("Failed to fetch risk profiles");
    return res.json();
}

export async function fetchUserHistory(userId: string): Promise<UserHistoryResponse> {
    const res = await fetch(`${API_BASE}/users/${userId}/history`);
    if (!res.ok) throw new Error(`Failed to fetch user history for ${userId}`);
    return res.json();
}

export async function fetchDashboardCharts(): Promise<ChartMetricsResponse> {
    const res = await fetch(`${API_BASE}/dashboard/charts`);
    if (!res.ok) throw new Error("Failed to fetch dashboard charts");
    return res.json();
}
