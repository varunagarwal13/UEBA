// Deterministic sample dataset used only when the backend is unreachable.
// Shapes mirror backend/app/schemas.py so pages render identically in live mode.

function mulberry32(seed) {
  return () => {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rnd = mulberry32(2101);
const pick = (arr) => arr[Math.floor(rnd() * arr.length)];
const between = (a, b) => a + rnd() * (b - a);

export const RULES = [
  'After_Hours_Login', 'Weekend_Login', 'Multiple_Failed_Logins', 'Brute_Force_Login_Attempt',
  'Dormant_Account_Login', 'Excessive_Command_Execution', 'Repeated_Sensitive_Actions',
  'Unusual_Working_Hours', 'Behavioral_Deviation', 'Sensitive_File_Access',
  'Sensitive_File_Modification', 'Sensitive_File_Deletion', 'Privilege_Command_Usage',
];

export const CTMC_STATES = [
  'Login', 'Email', 'Browser', 'File_Access', 'File_Modify', 'File_Add', 'File_Delete',
  'Command', 'Suspicious_Command', 'Privilege_Command', 'Device_Event', 'Login_Failed', 'Logout',
];

export const STAGES = [
  'AUTHENTICATION', 'RECONNAISSANCE', 'DISCOVERY', 'PRIVILEGE_ESCALATION',
  'COLLECTION', 'STAGING', 'PERSISTENCE', 'EXFILTRATION',
];

const USERS = [
  ['arjun.mehta', 'Treasury Ops', 'analyst'], ['svc_backup', 'Infrastructure', 'service'],
  ['priya.nair', 'Retail Lending', 'manager'], ['k.oduya', 'Core Banking', 'dba'],
  ['l.fernandes', 'Card Payments', 'analyst'], ['root_ops', 'Infrastructure', 'admin'],
  ['m.castellanos', 'Wealth Mgmt', 'advisor'], ['t.brennan', 'Compliance', 'auditor'],
  ['h.sato', 'Fraud Desk', 'analyst'], ['d.volkov', 'SWIFT Gateway', 'engineer'],
  ['r.iyer', 'HR Systems', 'admin'], ['n.okafor', 'Trade Finance', 'analyst'],
  ['svc_etl', 'Data Platform', 'service'], ['a.kowalski', 'Risk Analytics', 'quant'],
  ['j.moreau', 'Customer Care', 'agent'], ['s.ahmed', 'Treasury Ops', 'trader'],
  ['e.lindqvist', 'IT Helpdesk', 'support'], ['c.reyes', 'Mortgages', 'underwriter'],
];

const NARRATIVES = [
  'Session departs from personal baseline: {n} privileged commands within 6 min, 4.1σ above 30-day mean.',
  'Off-hours login from new device followed by bulk access to sensitive share /finance/recon.',
  'CTMC transition File_Access → File_Delete observed with population probability < 0.002.',
  'Repeated failed authentication ({n}×) preceding a successful login on a dormant account.',
  'Archive creation after mass read of customer KYC records — matches staging pattern.',
  'Command cadence spike: {n} commands/min vs. learned profile of 3.2/min.',
];

const now = Date.now();
const iso = (t) => new Date(t).toISOString();
const sevFor = (s) => (s >= 85 ? 'Critical' : s >= 65 ? 'High' : s >= 40 ? 'Medium' : 'Low');

const userRisk = Object.fromEntries(USERS.map(([u], i) => [u, Math.max(8, 96 - i * 5.1 - rnd() * 9)]));

export const users = USERS.map(([user_id, department, role], i) => ({
  user_id, username: user_id, department, role, email: `${user_id}@bank.internal`,
  is_active: true, created_at: iso(now - (400 - i * 9) * 864e5),
}));

export const alerts = Array.from({ length: 64 }, (_, i) => {
  const [user_id] = rnd() < 0.55 ? pick(USERS.slice(0, 6)) : pick(USERS);
  const base = userRisk[user_id];
  const risk_score = Math.min(99.4, Math.max(14, base + between(-22, 8)));
  const nRules = 1 + Math.floor(rnd() * 3);
  const rules = [...new Set(Array.from({ length: nRules }, () => pick(RULES)))];
  return {
    alert_id: 4200 - i,
    user_id,
    risk_score,
    severity: sevFor(risk_score),
    status: i < 9 ? 'open' : pick(['open', 'open', 'open', 'reviewed', 'closed']),
    rules_triggered: rules.join('|'),
    ctmc_log_prob: -between(2, 19),
    explanation: pick(NARRATIVES).replace('{n}', String(4 + Math.floor(rnd() * 30))) +
      ' | Detections: ' + ['CTMC', 'Rules', rnd() > 0.4 ? 'Isolation_Forest' : 'Personal_Baseline'].join(', '),
    created_at: iso(now - (i * i * 0.012 + i * 0.35 + rnd() * 0.4) * 36e5),
  };
});

export const risk = USERS.map(([user_id]) => {
  const mine = alerts.filter((a) => a.user_id === user_id);
  const latest = userRisk[user_id];
  const total_events = 400 + Math.floor(rnd() * 5200);
  return {
    user_id,
    latest_risk_score: latest,
    max_risk_score: Math.max(latest, ...mine.map((a) => a.risk_score)),
    severity: sevFor(latest),
    total_alerts: mine.length,
    open_alerts: mine.filter((a) => a.status === 'open').length,
    total_events,
    anomaly_events: Math.floor(total_events * between(0.01, latest / 600)),
    last_seen: iso(now - rnd() * 6 * 36e5),
  };
}).sort((a, b) => b.latest_risk_score - a.latest_risk_score);

const events_by_type = {
  HTTP: 48211, EMAIL: 21904, FILE_ACCESS: 17330, LOGIN: 9921, COMMAND: 6402,
  LOGOFF: 9310, FILE_MODIFY: 3120, DEVICE: 1802, LOGIN_FAILED: 911, FILE_DELETE: 642,
};
const sevCount = (s) => alerts.filter((a) => a.severity === s).length;

export const dashboard = {
  total_users: users.length,
  total_events: Object.values(events_by_type).reduce((a, b) => a + b, 0),
  total_alerts: alerts.length,
  open_alerts: alerts.filter((a) => a.status === 'open').length,
  critical_alerts: sevCount('Critical'),
  high_alerts: sevCount('High'),
  anomaly_rate_pct: 2.84,
  top_risky_users: risk.slice(0, 8),
  alerts_by_severity: { Critical: sevCount('Critical'), High: sevCount('High'), Medium: sevCount('Medium'), Low: sevCount('Low') },
  events_by_type,
};

// ── V2.1 objects (tables exist in models.py; no HTTP routes yet) ──
export const attackChains = risk.slice(0, 6).map((r, i) => {
  const depth = Math.max(2, 7 - i);
  const stages = STAGES.slice(0, depth).map((stage, j) => ({
    stage,
    timestamp: iso(now - (depth - j) * between(1.5, 5) * 36e5),
    session_id: `S-${(7781 + i * 31 + j * 7).toString(16).toUpperCase()}`,
    evidence: pick(RULES).replace(/_/g, ' '),
    score: Math.min(99, 20 + j * 11 + rnd() * 10),
  }));
  return {
    chain_id: `AC-${2026}${(110 + i).toString().padStart(4, '0')}`,
    user_id: r.user_id,
    first_seen: stages[0].timestamp,
    last_seen: stages.at(-1).timestamp,
    current_stage: stages.at(-1).stage,
    stages,
    risk_score: r.latest_risk_score,
    confidence: between(0.62, 0.97),
    status: i < 4 ? 'OPEN' : 'CLOSED',
  };
});

export const cases = attackChains.slice(0, 5).map((c, i) => ({
  case_id: `CASE-${(3301 + i).toString()}`,
  user_id: c.user_id,
  status: ['INVESTIGATING', 'OPEN', 'OPEN', 'INVESTIGATING', 'RESOLVED'][i],
  risk_score: c.risk_score,
  severity: sevFor(c.risk_score),
  current_stage: c.current_stage,
  summary: `Correlated ${alerts.filter((a) => a.user_id === c.user_id).length} alerts for ${c.user_id} into chain ${c.chain_id}; behaviour progressed through ${c.stages.length} kill-chain stages.`,
  alert_ids: alerts.filter((a) => a.user_id === c.user_id).slice(0, 6).map((a) => a.alert_id),
  chain_id: c.chain_id,
  created_at: c.first_seen,
  updated_at: c.last_seen,
}));

export function profileFor(user_id) {
  const r = mulberry32([...user_id].reduce((a, ch) => a + ch.charCodeAt(0), 0));
  const raw = CTMC_STATES.map(() => r() ** 2);
  const sum = raw.reduce((a, b) => a + b, 0);
  const hourly = Array.from({ length: 7 }, (_, d) => Array.from({ length: 24 }, (_, h) => {
    const work = h >= 9 && h <= 18 && d < 5 ? 1 : 0.12;
    return Math.round(work * r() * 40 + (r() > 0.94 ? 30 : 0));
  }));
  return {
    user_id,
    profile_version: 3,
    session_count: 120 + Math.floor(r() * 900),
    confidence: 0.55 + r() * 0.43,
    state_distribution: Object.fromEntries(CTMC_STATES.map((s, i) => [s, raw[i] / sum])),
    statistics: {
      commands_per_session: { mean: 3 + r() * 6, std: 1 + r() * 3, current: 6 + r() * 30 },
      files_touched: { mean: 12 + r() * 20, std: 4 + r() * 6, current: 20 + r() * 140 },
      session_minutes: { mean: 30 + r() * 60, std: 10 + r() * 20, current: 20 + r() * 160 },
      failed_logins: { mean: r() * 0.5, std: 0.4, current: Math.floor(r() * 8) },
    },
    hourly,
  };
}
