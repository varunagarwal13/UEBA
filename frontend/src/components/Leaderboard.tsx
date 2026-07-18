'use client';

import React from 'react';
import { UserMinus, ShieldAlert } from 'lucide-react';
import { RiskProfile } from '@/lib/api';

interface LeaderboardProps {
    profiles: RiskProfile[];
}

export default function Leaderboard({ profiles }: LeaderboardProps) {
    const getSeverityColor = (severity: string) => {
        switch (severity.toLowerCase()) {
            case 'critical':
                return 'text-red-400 bg-red-500/10 border-red-500/25';
            case 'high':
                return 'text-orange-400 bg-orange-500/10 border-orange-500/25';
            case 'medium':
                return 'text-amber-400 bg-amber-500/10 border-amber-500/25';
            default:
                return 'text-cyan-400 bg-cyan-500/10 border-cyan-500/25';
        }
    };

    return (
        <div className="bg-[#111722] border border-white/5 rounded-xl p-4 flex flex-col gap-3">
            <div className="flex flex-col">
                <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Top Risky Users</span>
                <span className="text-xs text-gray-400">Ranked by behavioral anomaly scores</span>
            </div>

            <div className="space-y-1.5 max-h-[220px] overflow-y-auto custom-scrollbar">
                {profiles.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-6 text-center text-gray-600 gap-1">
                        <UserMinus className="w-6 h-6 opacity-30" />
                        <span className="text-[10px]">No risk profiles active.</span>
                    </div>
                ) : (
                    profiles.map((profile, idx) => {
                        const score = Math.round(profile.latest_risk_score);
                        const isHighRisk = score >= 50;

                        return (
                            <div 
                                key={profile.user_id} 
                                className="flex items-center justify-between p-2 rounded bg-black/10 border border-white/5 hover:border-white/10 transition-colors"
                            >
                                <div className="flex items-center gap-2">
                                    <span className="text-[10px] font-black text-gray-600 w-4">#{idx + 1}</span>
                                    <div className="flex flex-col">
                                        <span className="text-xs font-bold text-gray-200 flex items-center gap-1">
                                            {profile.user_id}
                                            {isHighRisk && <ShieldAlert className="w-3 h-3 text-orange-400" />}
                                        </span>
                                        <span className="text-[8px] font-semibold text-gray-500 uppercase tracking-wider">
                                            {profile.open_alerts} Open Incidents
                                        </span>
                                    </div>
                                </div>
                                
                                <div className="flex items-center gap-2">
                                    <span className={`text-[8px] font-extrabold px-1.5 py-0.5 rounded border uppercase tracking-wider ${getSeverityColor(profile.severity)}`}>
                                        {profile.severity}
                                    </span>
                                    <span className="text-xs font-extrabold text-gray-100 bg-white/5 px-2 py-0.5 rounded border border-white/5 min-w-[32px] text-center">
                                        {score}
                                    </span>
                                </div>
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
