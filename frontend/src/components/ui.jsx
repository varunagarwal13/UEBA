import { Area, AreaChart, ResponsiveContainer } from 'recharts';
import { Cable } from 'lucide-react';
import clsx from 'clsx';
import { API_BASE } from '../api/client';
import { hueFor, initials, riskColor, n } from '../lib/format';

export function Panel({ title, sub, right, children, className, bodyClass, glow, style }) {
  return (
    <section className={clsx('panel', glow && 'glow', className)} style={style}>
      {(title || right) && (
        <header className="panel-head">
          {title && <h2 className="panel-title" style={{ margin: 0 }}>{title}</h2>}
          {sub && <span className="panel-sub">{sub}</span>}
          {right && <div className="right">{right}</div>}
        </header>
      )}
      <div className={clsx('panel-body', bodyClass)}>{children}</div>
    </section>
  );
}

export const Sev = ({ level }) => <span className={clsx('sev', (level || 'low').toLowerCase())}>{level || 'Low'}</span>;

export function Avatar({ id, size = 26 }) {
  return (
    <span className="avatar" style={{ width: size, height: size, background: hueFor(id), fontSize: size * 0.42 }}>
      {initials(id)}
    </span>
  );
}

export function Entity({ id, meta }) {
  return (
    <span className="entity">
      <Avatar id={id} />
      <span style={{ minWidth: 0 }}>
        <span className="strong" style={{ display: 'block', fontSize: 'var(--fs-md)', fontWeight: 500 }}>{id}</span>
        {meta && <span className="faint" style={{ fontSize: 'var(--fs-sm)' }}>{meta}</span>}
      </span>
    </span>
  );
}

export function RiskBar({ value, width = 64 }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      <span className="mono strong" style={{ width: 34, textAlign: 'right' }}>{n(value)}</span>
      <span className="bar" style={{ width }}>
        <i style={{ width: `${Math.min(100, value ?? 0)}%`, background: riskColor(value) }} />
      </span>
    </span>
  );
}

// Big figure over a 10-block meter. Kept the RiskRing name so callers stay unchanged.
export function RiskRing({ value = 0, size = 120, label = 'risk' }) {
  const color = riskColor(value);
  const lit = Math.round(Math.min(100, value) / 10);
  return (
    <div className="ring-wrap" style={{ minWidth: size, flexShrink: 0 }}>
      <div className="faint" style={{ fontSize: 'var(--fs-sm)', fontWeight: 600, textTransform: 'capitalize' }}>{label}</div>
      <div className="display" style={{ fontSize: Math.round(size * 0.42), fontWeight: 800, fontStretch: '118%', color: 'var(--tx-0)', lineHeight: 1, letterSpacing: '-0.04em', margin: '4px 0 8px' }}>{n(value)}</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(10, 1fr)', gap: 2 }} aria-hidden>
        {Array.from({ length: 10 }, (_, i) => <i key={i} style={{ height: 10, background: i < lit ? color : 'var(--ink-4)' }} />)}
      </div>
    </div>
  );
}

export function Spark({ data, color = '#6394ff', id }) {
  const gid = `spark-${id}`;
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data.map((v, i) => ({ i, v }))} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.35} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} fill={`url(#${gid})`} isAnimationActive={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function ChartTip({ active, payload, label, fmt = (v) => v }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tip">
      <div className="faint" style={{ marginBottom: 4 }}>{label}</div>
      {payload.map((p) => (
        <div key={p.dataKey} style={{ display: 'flex', gap: 10, justifyContent: 'space-between' }}>
          <span style={{ color: p.color || p.fill }}>{p.name}</span><b>{fmt(p.value)}</b>
        </div>
      ))}
    </div>
  );
}

export function NotExposed({ object, route, table }) {
  return (
    <div className="notice">
      <span className="tag violet"><Cable size={13} /> Route not exposed</span>
      <div className="display strong" style={{ fontSize: 'var(--fs-lg)' }}>{object} is persisted but not served</div>
      <div className="muted" style={{ maxWidth: 520, lineHeight: 1.6 }}>
        The backend at <code>{API_BASE}</code> is online and the <code>{table}</code> table exists in
        <code>models.py</code>, but there is no HTTP route for it. Add <code>GET {route}</code> and this
        workspace will populate automatically.
      </div>
    </div>
  );
}

export const Skeleton = ({ h = 14, w = '100%', style }) => <div className="skeleton" style={{ height: h, width: w, ...style }} />;

export function SkeletonRows({ rows = 6 }) {
  return (
    <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
      {Array.from({ length: rows }, (_, i) => <Skeleton key={i} h={22} w={`${92 - (i % 3) * 12}%`} />)}
    </div>
  );
}
