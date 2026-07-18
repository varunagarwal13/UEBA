'use client';

import React from 'react';
import { 
    Play, 
    Pause, 
    ChevronRight, 
    RotateCcw,
    Activity,
    Wifi
} from 'lucide-react';
import { SimulatorStatus } from '@/lib/api';

interface HeaderProps {
    stats: SimulatorStatus | null;
    onStep: () => void;
    onToggleAutoRun: () => void;
    onReset: () => void;
    isStepLoading: boolean;
    isResetLoading: boolean;
    isAutoRunLoading: boolean;
}

export default function Header({
    stats,
    onStep,
    onToggleAutoRun,
    onReset,
    isStepLoading,
    isResetLoading,
    isAutoRunLoading
}: HeaderProps) {
    const isAutoRunActive = stats?.auto_run ?? false;
    const processed = stats?.processed ?? 0;
    const totalTest = stats?.total_test_sessions ?? 0;
    const isCompleted = totalTest > 0 && processed >= totalTest;

    return (
        <header className="bg-[#111722] border-b border-white/5 px-6 py-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 w-full relative z-30">
            {/* Brand Logo & Connection */}
            <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center text-white shadow-xl shadow-cyan-500/10">
                    <Activity className="w-5 h-5 text-gray-100" />
                </div>
                <div className="flex flex-col">
                    <h1 className="text-sm font-extrabold tracking-wider uppercase text-gray-100 flex items-center gap-2">
                        EUBA
                        <span className="text-[9px] font-black text-cyan-400 bg-cyan-400/5 border border-cyan-400/10 px-1.5 py-0.5 rounded tracking-normal">SOC PORTAL</span>
                    </h1>
                    <span className="text-[10px] text-gray-500 font-semibold flex items-center gap-1">
                        <Wifi className="w-3 h-3 text-teal-400" />
                        FastAPI Service Connected
                    </span>
                </div>
            </div>

            {/* Simulation controls */}
            <div className="flex items-center gap-2 flex-wrap">
                <button
                    onClick={onStep}
                    disabled={isStepLoading || isAutoRunActive || isCompleted}
                    className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider px-3.5 py-2 rounded bg-cyan-500 hover:bg-cyan-600 text-gray-900 font-bold transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                >
                    {isStepLoading ? 'Running...' : (
                        <>
                            Next Session
                            <ChevronRight className="w-3.5 h-3.5" />
                        </>
                    )}
                </button>

                <button
                    onClick={onToggleAutoRun}
                    disabled={isAutoRunLoading || isCompleted}
                    className={`flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider px-3.5 py-2 rounded transition-all border ${
                        isAutoRunActive
                            ? 'bg-red-500/10 text-red-400 border-red-500/20 hover:bg-red-500/15'
                            : 'bg-[#171E2B] text-gray-300 border-white/5 hover:text-gray-100 hover:bg-[#171E2B]/80'
                    }`}
                >
                    {isAutoRunActive ? (
                        <>
                            <Pause className="w-3.5 h-3.5" />
                            Pause Auto-Run
                        </>
                    ) : (
                        <>
                            <Play className="w-3.5 h-3.5" />
                            Auto-Run
                        </>
                    )}
                </button>

                <button
                    onClick={onReset}
                    disabled={isResetLoading}
                    className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider px-3.5 py-2 rounded bg-black/20 hover:bg-black/30 text-gray-400 hover:text-gray-200 border border-white/5 transition-all"
                >
                    <RotateCcw className="w-3.5 h-3.5" />
                    Reset
                </button>

                {/* Simulation status indicator */}
                <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-black/10 border border-white/5 ml-2">
                    <span className={`w-2 h-2 rounded-full ${isAutoRunActive ? 'bg-cyan-500 animate-pulse' : 'bg-gray-600'}`}></span>
                    <span className="text-[9px] font-extrabold uppercase tracking-widest text-gray-500">
                        {isCompleted ? 'COMPLETED' : isAutoRunActive ? 'SIMULATING' : 'PAUSED'}
                    </span>
                </div>
            </div>
        </header>
    );
}
