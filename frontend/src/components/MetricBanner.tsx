'use client';

import React from 'react';
import { 
    Users, 
    Layers, 
    AlertTriangle 
} from 'lucide-react';
import { SimulatorStatus } from '@/lib/api';

interface MetricBannerProps {
    stats: SimulatorStatus | null;
    totalUsers: number;
}

export default function MetricBanner({ stats, totalUsers }: MetricBannerProps) {
    const processed = stats?.processed ?? 0;
    const totalTest = stats?.total_test_sessions ?? 0;
    const alertsGenerated = stats?.alerts_generated ?? 0;
    const f1 = stats?.f1_score ?? 0.0;
    const precision = stats?.precision ?? 0.0;
    const recall = stats?.recall ?? 0.0;
    const tp = stats?.tp ?? 0;
    const fp = stats?.fp ?? 0;
    const tn = stats?.tn ?? 0;
    const fn = stats?.fn ?? 0;

    return (
        <section className="grid grid-cols-1 md:grid-cols-4 gap-4 w-full">
            {/* KPI 1: Monitored Users */}
            <div className="bg-[#111722] border border-white/5 hover:border-white/15 rounded-xl p-4 flex items-center gap-4 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-2xl hover:shadow-black/50">
                <div className="w-12 h-12 rounded-lg bg-cyan-500/5 border border-cyan-500/10 flex items-center justify-center text-cyan-400">
                    <Users className="w-6 h-6" />
                </div>
                <div className="flex flex-col">
                    <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Monitored Profiles</span>
                    <span className="text-2xl font-extrabold tracking-tight text-gray-100">{totalUsers}</span>
                </div>
            </div>

            {/* KPI 2: Sessions Processed */}
            <div className="bg-[#111722] border border-white/5 hover:border-white/15 rounded-xl p-4 flex items-center gap-4 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-2xl hover:shadow-black/50">
                <div className="w-12 h-12 rounded-lg bg-teal-500/5 border border-teal-500/10 flex items-center justify-center text-teal-400">
                    <Layers className="w-6 h-6" />
                </div>
                <div className="flex flex-col">
                    <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Simulated Sessions</span>
                    <div className="flex items-baseline gap-1.5">
                        <span className="text-2xl font-extrabold tracking-tight text-gray-100">{processed}</span>
                        <span className="text-xs text-gray-600">/ {totalTest}</span>
                    </div>
                </div>
            </div>

            {/* KPI 3: Alerts Triggered */}
            <div className="bg-[#111722] border border-white/5 hover:border-white/15 rounded-xl p-4 flex items-center gap-4 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-2xl hover:shadow-black/50">
                <div className="w-12 h-12 rounded-lg bg-red-500/5 border border-red-500/10 flex items-center justify-center text-red-400">
                    <AlertTriangle className="w-6 h-6" />
                </div>
                <div className="flex flex-col">
                    <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Alerts Triggered</span>
                    <span className="text-2xl font-extrabold tracking-tight text-red-400">{alertsGenerated}</span>
                </div>
            </div>

            {/* KPI 4: Confusion Matrix / Performance */}
            <div className="bg-[#111722] border border-white/5 hover:border-white/15 rounded-xl p-4 flex flex-col justify-between transition-all duration-300 hover:-translate-y-0.5 hover:shadow-2xl hover:shadow-black/50">
                <div className="flex justify-between items-center mb-1">
                    <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Detection Stats</span>
                    <span className="text-[9px] font-extrabold text-teal-400 bg-teal-400/5 border border-teal-400/10 px-1.5 py-0.5 rounded">REALTIME</span>
                </div>
                <div className="flex items-center justify-between gap-4">
                    <div className="flex flex-col">
                        <span className="text-[9px] font-bold text-gray-600 uppercase">F1 Score</span>
                        <span className="text-2xl font-extrabold bg-gradient-to-r from-cyan-400 to-indigo-500 bg-clip-text text-transparent">
                            {f1.toFixed(2)}
                        </span>
                    </div>
                    <div className="h-6 w-px bg-white/5"></div>
                    <div className="flex gap-4">
                        <div className="flex flex-col">
                            <span className="text-[9px] font-bold text-gray-600 uppercase">Prec</span>
                            <span className="text-sm font-extrabold text-gray-200">{precision.toFixed(2)}</span>
                        </div>
                        <div className="flex flex-col">
                            <span className="text-[9px] font-bold text-gray-600 uppercase">Recall</span>
                            <span className="text-sm font-extrabold text-gray-200">{recall.toFixed(2)}</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Confusion Matrix Detail row if needed, but we can render it inside a collapsible sub-row or render TP/FP inline */}
            <div className="md:col-span-4 bg-[#111722] border border-white/5 rounded-xl p-3 flex flex-wrap items-center justify-between gap-4 text-xs">
                <span className="text-gray-500 font-semibold uppercase tracking-wider text-[10px]">Confusion Matrix Audit:</span>
                <div className="flex items-center gap-6">
                    <div className="flex items-center gap-2" title="True Positives (Correct Threat Detections)">
                        <span className="w-2 h-2 rounded-full bg-teal-400"></span>
                        <span className="text-gray-400">True Positives (TP):</span>
                        <strong className="text-teal-400 font-bold">{tp}</strong>
                    </div>
                    <div className="flex items-center gap-2" title="False Positives (False Alarms Fired)">
                        <span className="w-2 h-2 rounded-full bg-red-400"></span>
                        <span className="text-gray-400">False Positives (FP):</span>
                        <strong className="text-red-400 font-bold">{fp}</strong>
                    </div>
                    <div className="flex items-center gap-2" title="False Negatives (Missed Threats)">
                        <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                        <span className="text-gray-400">False Negatives (FN):</span>
                        <strong className="text-amber-400 font-bold">{fn}</strong>
                    </div>
                    <div className="flex items-center gap-2" title="True Negatives (Correct Silence on Normal Activity)">
                        <span className="w-2 h-2 rounded-full bg-gray-500"></span>
                        <span className="text-gray-400">True Negatives (TN):</span>
                        <strong className="text-gray-200 font-bold">{tn}</strong>
                    </div>
                </div>
            </div>
        </section>
    );
}
