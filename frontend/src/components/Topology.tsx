'use client';

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Inbox, 
    Database, 
    Cpu, 
    ShieldAlert, 
    FileText, 
    GitMerge, 
    FileSpreadsheet, 
    Layers, 
    BellRing 
} from 'lucide-react';
import { PipelineTrace } from '@/lib/api';

interface TopologyProps {
    trace: PipelineTrace | null;
    isSimulating: boolean;
}

const NODES = [
    { name: 'Incoming Session', icon: Inbox, color: 'text-gray-400', glow: 'shadow-gray-500/20' },
    { name: 'Behavior Extraction', icon: Database, color: 'text-blue-400', glow: 'shadow-blue-500/20' },
    { name: 'State Encoding', icon: Layers, color: 'text-purple-400', glow: 'shadow-purple-500/20' },
    { name: 'CTMC Engine', icon: Cpu, color: 'text-cyan-400', glow: 'shadow-cyan-500/20' },
    { name: 'Rule Engine', icon: ShieldAlert, color: 'text-orange-400', glow: 'shadow-orange-500/20' },
    { name: 'Risk Fusion', icon: GitMerge, color: 'text-indigo-400', glow: 'shadow-indigo-500/20' },
    { name: 'Explainability', icon: FileSpreadsheet, color: 'text-pink-400', glow: 'shadow-pink-500/20' },
    { name: 'Alert Generation', icon: FileText, color: 'text-rose-400', glow: 'shadow-rose-500/20' },
    { name: 'SOC Queue', icon: BellRing, color: 'text-teal-400', glow: 'shadow-teal-500/20' },
];

export default function Topology({ trace, isSimulating }: TopologyProps) {
    const [activeNode, setActiveNode] = useState<number>(-1);
    const [animatePulse, setAnimatePulse] = useState<boolean>(false);

    // Coordinate mapping for SVG path traversal
    const width = 1000;
    const height = 120;
    const paddingX = 50;
    const stepX = (width - paddingX * 2) / (NODES.length - 1);
    const nodeCoords = NODES.map((_, i) => ({
        x: paddingX + i * stepX,
        y: height / 2
    }));

    // Trigger animation flow whenever a new trace is received
    useEffect(() => {
        if (!trace) {
            setActiveNode(-1);
            setAnimatePulse(false);
            return;
        }

        // Start particle traversal animation
        setAnimatePulse(true);
        setActiveNode(0);

        const interval = 220; // Time spent per segment in ms
        const timers: NodeJS.Timeout[] = [];

        NODES.forEach((_, idx) => {
            if (idx > 0) {
                const t = setTimeout(() => {
                    setActiveNode(idx);
                }, idx * interval);
                timers.push(t);
            }
        });

        // End pulse animation
        const endTimer = setTimeout(() => {
            setAnimatePulse(false);
        }, NODES.length * interval);
        timers.push(endTimer);

        return () => {
            timers.forEach(clearTimeout);
        };
    }, [trace]);

    const getPulseColor = () => {
        if (!trace) return '#06b6d4';
        if (trace.final_risk_score >= 8.0) return '#ef4444'; // Critical -> Red pulse
        if (trace.final_risk_score >= 5.0) return '#f97316'; // High -> Orange pulse
        return '#06b6d4'; // Medium/Low -> Cyan pulse
    };

    return (
        <div className="bg-[#111722] border border-white/5 rounded-xl p-6 flex flex-col items-center gap-6 relative overflow-hidden">
            {/* Header / Pipeline status */}
            <div className="flex justify-between items-center w-full">
                <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse"></span>
                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Live Detection Pipeline</h3>
                </div>
                <div className="text-[10px] text-gray-500">
                    {isSimulating ? (
                        <span className="text-cyan-400 font-semibold animate-pulse">Simulator Active — Processing Session</span>
                    ) : (
                        <span>Idle — Awaiting events</span>
                    )}
                </div>
            </div>

            {/* Pipeline SVG Visualizer */}
            <div className="relative w-full overflow-x-auto select-none no-scrollbar flex justify-center py-4">
                <div className="relative min-w-[1000px] h-[160px]">
                    {/* SVG Connections & Particle */}
                    <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox={`0 0 ${width} ${height}`}>
                        {/* Background connecting line */}
                        <line 
                            x1={nodeCoords[0].x} 
                            y1={nodeCoords[0].y} 
                            x2={nodeCoords[nodeCoords.length-1].x} 
                            y2={nodeCoords[nodeCoords.length-1].y}
                            stroke="rgba(255, 255, 255, 0.05)"
                            strokeWidth="3"
                            strokeLinecap="round"
                        />

                        {/* Illuminating active line path */}
                        {activeNode > 0 && (
                            <line 
                                x1={nodeCoords[0].x} 
                                y1={nodeCoords[0].y} 
                                x2={nodeCoords[activeNode].x} 
                                y2={nodeCoords[activeNode].y}
                                stroke="rgba(6, 182, 212, 0.25)"
                                strokeWidth="3"
                                strokeLinecap="round"
                            />
                        )}

                        {/* Glowing travelling particle */}
                        {animatePulse && (
                            <motion.circle
                                cx={nodeCoords[0].x}
                                cy={nodeCoords[0].y}
                                r="6"
                                fill={getPulseColor()}
                                className="shadow-lg filter drop-shadow-[0_0_8px_rgba(6,182,212,0.8)]"
                                animate={{
                                    cx: nodeCoords.map(c => c.x),
                                    cy: nodeCoords.map(c => c.y),
                                }}
                                transition={{
                                    duration: (NODES.length - 1) * 0.22,
                                    ease: 'easeInOut',
                                }}
                            />
                        )}
                    </svg>

                    {/* Nodes container */}
                    <div className="absolute inset-0 flex justify-between px-[25px]">
                        {NODES.map((node, idx) => {
                            const Icon = node.icon;
                            const isActive = activeNode === idx;
                            const isPassed = activeNode >= idx;

                            return (
                                <div 
                                    key={idx} 
                                    className="flex flex-col items-center justify-center relative w-[90px] h-full"
                                >
                                    {/* Node Bubble */}
                                    <motion.div
                                        className={`w-12 h-12 rounded-full flex items-center justify-center border transition-all duration-300 z-10 ${
                                            isActive 
                                                ? 'bg-cyan-500/10 border-cyan-400 shadow-[0_0_20px_rgba(6,182,212,0.3)]' 
                                                : isPassed 
                                                    ? 'bg-[#171E2B] border-cyan-500/20' 
                                                    : 'bg-[#090C12] border-white/5'
                                        }`}
                                        animate={isActive ? { scale: 1.15 } : { scale: 1 }}
                                        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                                    >
                                        <Icon className={`w-5 h-5 ${isActive ? 'text-cyan-400' : isPassed ? 'text-gray-300' : 'text-gray-600'}`} />
                                    </motion.div>

                                    {/* Node label */}
                                    <span className={`text-[9px] font-bold text-center mt-2.5 max-w-[80px] uppercase tracking-wider ${
                                        isActive ? 'text-cyan-400 font-extrabold' : isPassed ? 'text-gray-400' : 'text-gray-600'
                                    }`}>
                                        {node.name}
                                    </span>

                                    {/* Dynamic Value Tooltip beneath active node */}
                                    <div className="absolute bottom-[-10px] w-[110px] flex justify-center text-center">
                                        <AnimatePresence>
                                            {isActive && trace && (
                                                <motion.div
                                                    initial={{ opacity: 0, y: -4 }}
                                                    animate={{ opacity: 1, y: 0 }}
                                                    exit={{ opacity: 0, y: -4 }}
                                                    className="bg-[#171E2B] border border-cyan-500/20 rounded px-1.5 py-0.5 shadow-xl text-[8px] font-bold text-cyan-300 uppercase tracking-widest whitespace-nowrap"
                                                >
                                                    {idx === 0 && `ID: ${trace.session_id.substring(0, 8)}`}
                                                    {idx === 1 && `Events: ${trace.event_count}`}
                                                    {idx === 2 && `States: ${trace.states.length}`}
                                                    {idx === 3 && `Score: ${trace.ctmc_score}`}
                                                    {idx === 4 && `Violations: ${trace.rule_violations.length}`}
                                                    {idx === 5 && `Risk: ${trace.final_risk_score}`}
                                                    {idx === 6 && 'Narrative OK'}
                                                    {idx === 7 && (trace.alert_id != null ? `${trace.severity}` : 'No Alert')}
                                                    {idx === 8 && (trace.alert_id != null ? 'Pushed' : 'Ignored')}
                                                </motion.div>
                                            )}
                                        </AnimatePresence>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </div>
    );
}
