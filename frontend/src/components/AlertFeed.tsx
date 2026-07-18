'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertCircle, ShieldAlert, Shield } from 'lucide-react';
import { Alert } from '@/lib/api';

interface AlertFeedProps {
    alerts: Alert[];
    selectedAlertId: number | null;
    onSelectAlert: (alertId: number) => void;
}

export default function AlertFeed({ alerts, selectedAlertId, onSelectAlert }: AlertFeedProps) {
    const [severityFilter, setSeverityFilter] = useState<string>('all');

    const filteredAlerts = alerts.filter(alert => {
        if (severityFilter === 'all') return true;
        return alert.severity.toLowerCase() === severityFilter.toLowerCase();
    });

    const getSeverityStyles = (severity: string) => {
        switch (severity.toLowerCase()) {
            case 'critical':
                return {
                    border: 'border-red-500/10 hover:border-red-500/30',
                    bg: 'bg-red-500/5',
                    badge: 'bg-red-500/10 text-red-400 border-red-500/25',
                    icon: ShieldAlert,
                    text: 'text-red-400'
                };
            case 'high':
                return {
                    border: 'border-orange-500/10 hover:border-orange-500/30',
                    bg: 'bg-orange-500/5',
                    badge: 'bg-orange-500/10 text-orange-400 border-orange-500/25',
                    icon: AlertCircle,
                    text: 'text-orange-400'
                };
            case 'medium':
                return {
                    border: 'border-amber-500/10 hover:border-amber-500/30',
                    bg: 'bg-amber-500/5',
                    badge: 'bg-amber-500/10 text-amber-400 border-amber-500/25',
                    icon: AlertCircle,
                    text: 'text-amber-400'
                };
            default:
                return {
                    border: 'border-cyan-500/10 hover:border-cyan-500/30',
                    bg: 'bg-cyan-500/5',
                    badge: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/25',
                    icon: Shield,
                    text: 'text-cyan-400'
                };
        }
    };

    return (
        <div className="flex flex-col gap-4 h-full">
            {/* Filter controls */}
            <div className="flex items-center justify-between">
                <div className="flex flex-col">
                    <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Alert Feed Inbox</span>
                    <span className="text-xs text-gray-400 font-medium">{filteredAlerts.length} Active Incidents</span>
                </div>
                <select
                    value={severityFilter}
                    onChange={(e) => setSeverityFilter(e.target.value)}
                    className="bg-[#171E2B] border border-white/5 rounded px-2.5 py-1 text-xs text-gray-300 font-semibold focus:outline-none focus:border-cyan-500/30 cursor-pointer"
                >
                    <option value="all">All Severities</option>
                    <option value="critical">Critical Only</option>
                    <option value="high">High Only</option>
                    <option value="medium">Medium Only</option>
                    <option value="low">Low Only</option>
                </select>
            </div>

            {/* List container */}
            <div className="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar min-h-[400px] max-h-[680px]">
                <AnimatePresence initial={false}>
                    {filteredAlerts.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-16 text-center text-gray-500 gap-2">
                            <Shield className="w-8 h-8 opacity-20" />
                            <span className="text-xs">No alerts match filters.</span>
                        </div>
                    ) : (
                        filteredAlerts.map((alert) => {
                            const styles = getSeverityStyles(alert.severity);
                            const Icon = styles.icon;
                            const isSelected = selectedAlertId === alert.alert_id;
                            
                            // Parse compact sequence preview
                            let seqPreview = "Behavior sequence";
                            try {
                                const exp = typeof alert.explanation === 'string' 
                                    ? JSON.parse(alert.explanation) 
                                    : alert.explanation;
                                const compact = exp?.timeline?.timeline_compact;
                                if (compact && Array.isArray(compact) && compact.length > 0) {
                                    seqPreview = compact.join(' → ');
                                }
                            } catch {}

                            const formattedTime = new Date(alert.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

                            return (
                                <motion.div
                                    key={alert.alert_id}
                                    initial={{ opacity: 0, y: 12 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, scale: 0.95 }}
                                    transition={{ duration: 0.2, ease: 'easeOut' }}
                                    onClick={() => onSelectAlert(alert.alert_id)}
                                    className={`p-3 rounded-lg border cursor-pointer transition-all duration-200 select-none ${styles.bg} ${
                                        isSelected 
                                            ? 'border-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.15)] ring-1 ring-cyan-400/20' 
                                            : `border-white/5 hover:bg-[#171E2B]/50 ${styles.border}`
                                    }`}
                                >
                                    <div className="flex justify-between items-start mb-1.5">
                                        <span className="text-[10px] font-extrabold text-gray-400 uppercase tracking-widest">ALT-{alert.alert_id}</span>
                                        <span className="text-[9px] text-gray-600 font-medium">{formattedTime}</span>
                                    </div>
                                    <div className="flex justify-between items-center mb-2">
                                        <div className="flex items-center gap-1.5">
                                            <Icon className={`w-3.5 h-3.5 ${styles.text}`} />
                                            <span className="text-xs font-bold text-gray-200">{alert.user_id}</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className={`text-[8px] font-extrabold px-1.5 py-0.5 rounded border uppercase tracking-wider ${styles.badge}`}>
                                                {alert.severity}
                                            </span>
                                            <span className="text-xs font-black text-gray-300 bg-black/20 px-1.5 py-0.5 rounded border border-white/5" title="Risk Score">
                                                {Math.round(alert.risk_score)}
                                            </span>
                                        </div>
                                    </div>
                                    <p className="text-[10px] text-gray-500 truncate whitespace-nowrap" title={seqPreview}>
                                        {seqPreview}
                                    </p>
                                </motion.div>
                            );
                        })
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}
