'use client';

import React, { useEffect, useState } from 'react';
import { 
    ResponsiveContainer, 
    AreaChart, 
    Area, 
    XAxis, 
    YAxis, 
    Tooltip, 
    CartesianGrid,
    BarChart,
    Bar,
    Cell
} from 'recharts';
import { ChartMetricsResponse } from '@/lib/api';

interface ChartsPanelProps {
    data: ChartMetricsResponse | null;
}

export default function ChartsPanel({ data }: ChartsPanelProps) {
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    if (!mounted || !data) {
        return (
            <div className="bg-[#111722] border border-white/5 rounded-xl p-6 h-[340px] flex items-center justify-center text-xs text-gray-500">
                Loading analytics visualizers...
            </div>
        );
    }

    const threatTrend = data.threat_trend;
    const riskDistribution = data.risk_distribution;


    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
            {/* Chart 1: Threat Trend (Time Series Area Chart) */}
            <div className="bg-[#111722] border border-white/5 rounded-xl p-4 flex flex-col gap-3">
                <div className="flex flex-col">
                    <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Threat Incident Trend</span>
                    <span className="text-xs text-gray-400">Total alerts triggered over time</span>
                </div>
                <div className="h-[200px] w-full text-[10px] text-gray-400">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={threatTrend} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
                            <defs>
                                <linearGradient id="trendGlow" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.2}/>
                                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0}/>
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                            <XAxis dataKey="date" stroke="rgba(255,255,255,0.2)" tickLine={false} axisLine={false} />
                            <YAxis stroke="rgba(255,255,255,0.2)" tickLine={false} axisLine={false} allowDecimals={false} />
                            <Tooltip 
                                contentStyle={{ backgroundColor: '#171E2B', borderColor: 'rgba(255,255,255,0.05)', borderRadius: '8px' }}
                                labelStyle={{ color: '#9ca3af', fontWeight: 'bold' }}
                                itemStyle={{ color: '#06b6d4' }}
                            />
                            <Area type="monotone" dataKey="count" name="Alerts" stroke="#06b6d4" strokeWidth={2} fillOpacity={1} fill="url(#trendGlow)" />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Chart 2: User Risk Distribution (Histogram Bar Chart) */}
            <div className="bg-[#111722] border border-white/5 rounded-xl p-4 flex flex-col gap-3">
                <div className="flex flex-col">
                    <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">User Risk Distribution</span>
                    <span className="text-xs text-gray-400">User counts mapped across score brackets</span>
                </div>
                <div className="h-[200px] w-full text-[10px] text-gray-400">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={riskDistribution} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                            <XAxis dataKey="range" stroke="rgba(255,255,255,0.2)" tickLine={false} axisLine={false} />
                            <YAxis stroke="rgba(255,255,255,0.2)" tickLine={false} axisLine={false} allowDecimals={false} />
                            <Tooltip 
                                contentStyle={{ backgroundColor: '#171E2B', borderColor: 'rgba(255,255,255,0.05)', borderRadius: '8px' }}
                                itemStyle={{ color: '#a855f7' }}
                            />
                            <Bar dataKey="count" name="Users" radius={[4, 4, 0, 0]}>
                                {riskDistribution.map((entry, index) => {
                                    // Highlight highest risk bracket in red/orange, low in cyan
                                    let fill = '#06b6d4';
                                    if (entry.range === '81-100') fill = '#ef4444';
                                    else if (entry.range === '61-80') fill = '#f97316';
                                    else if (entry.range === '41-60') fill = '#f59e0b';
                                    else if (entry.range === '21-40') fill = '#6366f1';
                                    return <Cell key={`cell-${index}`} fill={fill} fillOpacity={0.7} strokeWidth={1} />;
                                })}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
}
