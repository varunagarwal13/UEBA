export const SEV_ORDER = ['Critical', 'High', 'Medium', 'Low'];
export const SEV_COLOR = {
  Critical: 'var(--sev-critical)', High: 'var(--sev-high)', Medium: 'var(--sev-medium)', Low: 'var(--sev-low)',
};
// raw hex for SVG gradients / recharts, which can't resolve CSS vars in every attribute
export const SEV_HEX = { Critical: '#e5283c', High: '#ff7a00', Medium: '#f5c400', Low: '#12a874' };

export const sevOf = (score) => (score >= 85 ? 'Critical' : score >= 65 ? 'High' : score >= 40 ? 'Medium' : 'Low');
export const riskColor = (score) => SEV_COLOR[sevOf(score ?? 0)];

export const n = (v, d = 1) => (typeof v === 'number' && Number.isFinite(v) ? v.toFixed(d) : '—');
export const compact = (v) => new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(v ?? 0);
export const int = (v) => new Intl.NumberFormat('en').format(v ?? 0);

// Backend datetimes are naive UTC; without a suffix the browser would read them as local time.
export const toDate = (isoStr) => new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(isoStr) ? isoStr : `${isoStr}Z`);

export function stamp(isoStr) {
  if (!isoStr) return '—';
  const d = toDate(isoStr);
  return `${d.toISOString().slice(5, 10)} ${d.toISOString().slice(11, 19)}`;
}

export function ago(isoStr) {
  if (!isoStr) return '—';
  const s = Math.max(0, (Date.now() - toDate(isoStr).getTime()) / 1000);
  if (s < 60) return `${Math.floor(s)}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  return `${Math.floor(s / 86400)}d`;
}

// PRIVILEGE_ESCALATION -> Privilege escalation
export const stageLabel = (s) => (s ? s.toLowerCase().replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase()) : 'Unknown');
export const statusLabel = (s) => (s ? s.charAt(0) + s.slice(1).toLowerCase() : '');

export const splitRules = (r) => (r ? r.split(/[|,]/).map((x) => x.trim()).filter(Boolean) : []);
export const prettyRule = (r) => r.replace(/^Rule_/, '').replace(/_/g, ' ');

const HUES = ['#2b3dd8', '#0f7a5a', '#6a2fd1', '#00708a', '#3a3a3a', '#a3165f', '#7a5a00'];
export function hueFor(id = '') {
  let h = 0;
  for (const c of id) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return HUES[h % HUES.length];
}
export const initials = (id = '') => id.replace(/^(svc_|root_)/, '').split(/[._-]/).map((p) => p[0]).join('').slice(0, 2).toUpperCase();
