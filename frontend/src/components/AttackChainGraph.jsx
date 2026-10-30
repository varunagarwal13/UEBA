import { useMemo } from 'react';
import { ReactFlow, Background, Controls, Handle, Position, MarkerType } from '@xyflow/react';
import { STAGES } from '../data/demo';
import { SEV_HEX, sevOf, stamp, n, stageLabel } from '../lib/format';

const COLS = 4;
const GAP_X = 260;
const GAP_Y = 160;

function StageNode({ data }) {
  const { stage, hit, current, idx, chainColor } = data;
  const color = hit ? (hit.score != null ? SEV_HEX[sevOf(hit.score)] : chainColor) : 'var(--ink-4)';
  return (
    <div style={{
      width: 220, padding: '12px 14px', borderRadius: 0,
      background: hit ? 'var(--ink-2)' : 'var(--ink-2)',
      border: `1px solid ${hit ? color : 'var(--line)'}`,
      boxShadow: current ? `5px 5px 0 ${color}` : 'none', borderWidth: current ? 2 : 1,
      opacity: hit ? 1 : 0.45,
    }}>
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span className="mono" style={{ fontSize: 'var(--fs-xs)', color: hit ? color : 'var(--tx-3)' }}>{String(idx + 1).padStart(2, '0')}</span>
        <span style={{ fontSize: 'var(--fs-base)', fontWeight: 600, color: hit ? 'var(--tx-0)' : 'var(--tx-2)' }}>{stageLabel(stage)}</span>
        {current && <span className="pulse" style={{ color, marginLeft: 'auto' }} />}
      </div>
      {hit ? (
        <>
          {hit.evidence && <div style={{ fontSize: 'var(--fs-md)', color: 'var(--tx-1)', marginTop: 6 }}>{hit.evidence}</div>}
          <div className="mono" style={{ fontSize: 'var(--fs-xs)', color: 'var(--tx-3)', marginTop: 6, display: 'flex', justifyContent: 'space-between' }}>
            <span>{hit.session_id || 'observed'}</span>{hit.score != null && <span style={{ color }}>{n(hit.score, 0)}</span>}
          </div>
          {hit.timestamp && <div className="mono" style={{ fontSize: 'var(--fs-xs)', color: 'var(--tx-3)', marginTop: 2 }}>{stamp(hit.timestamp)}</div>}
        </>
      ) : <div style={{ fontSize: 'var(--fs-sm)', color: 'var(--tx-3)', marginTop: 6 }}>Not observed</div>}
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
}

const nodeTypes = { stage: StageNode };

export default function AttackChainGraph({ chain }) {
  const chainColor = SEV_HEX[sevOf(chain?.risk_score ?? 0)];
  const { nodes, edges } = useMemo(() => {
    const hits = Object.fromEntries((chain?.stages || []).map((s) => [s.stage, s]));
    const lastIdx = STAGES.indexOf(chain?.current_stage);
    const nodes = STAGES.map((stage, idx) => {
      const row = Math.floor(idx / COLS);
      // snake layout: second row runs right-to-left so the chain reads continuously
      const col = row % 2 === 0 ? idx % COLS : COLS - 1 - (idx % COLS);
      return {
        id: stage, type: 'stage', draggable: true,
        position: { x: col * GAP_X, y: row * GAP_Y },
        data: { stage, idx, hit: hits[stage], current: idx === lastIdx, chainColor },
      };
    });
    const edges = STAGES.slice(1).map((stage, i) => {
      const prev = STAGES[i];
      const lit = hits[prev] && hits[stage];
      const color = lit ? (hits[stage].score != null ? SEV_HEX[sevOf(hits[stage].score)] : chainColor) : 'var(--ink-4)';
      return {
        id: `${prev}-${stage}`, source: prev, target: stage, type: 'smoothstep',
        animated: !!lit,
        style: { stroke: color, strokeWidth: lit ? 2 : 1, strokeDasharray: lit ? undefined : '4 4' },
        markerEnd: { type: MarkerType.ArrowClosed, color, width: 16, height: 16 },
      };
    });
    return { nodes, edges };
  }, [chain, chainColor]);

  return (
    <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.08 }}
      proOptions={{ hideAttribution: true }} nodesConnectable={false} minZoom={0.4} maxZoom={1.6}>
      <Background color="rgba(128,128,128,0.35)" gap={20} size={1} />
      <Controls showInteractive={false} position="bottom-right" />
    </ReactFlow>
  );
}
