'use client';

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { 
    Clock, 
    CheckSquare, 
    User, 
    Activity, 
    AlertOctagon, 
    ExternalLink
} from 'lucide-react';
import { Alert, UserHistoryResponse, fetchUserHistory, updateAlertStatus } from '@/lib/api';

interface InvestigationConsoleProps {
    alertId: number | null;
    onAlertStatusUpdated: () => void;
}

export default function InvestigationConsole({ alertId, onAlertStatusUpdated }: InvestigationConsoleProps) {
    const [alert, setAlert] = useState<Alert | null>(null);
    const [userHistory, setUserHistory] = useState<UserHistoryResponse | null>(null);
    const [timelineMode, setTimelineMode] = useState<'compact' | 'full'>('compact');
    const [checklist, setChecklist] = useState<{ text: string; checked: boolean }[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [statusUpdating, setStatusUpdating] = useState<boolean>(false);

    useEffect(() => {
        if (!alertId) {
            setAlert(null);
            setUserHistory(null);
            setChecklist([]);
            return;
        }

        const loadDetails = async () => {
            setLoading(true);
            try {
                // Fetch alert detail
                const API_BASE = typeof window !== 'undefined' 
                    ? (window.location.port === '3000' ? 'http://localhost:8080' : '') 
                    : 'http://localhost:8080';
                
                const res = await fetch(`${API_BASE}/alerts/${alertId}`);
                if (!res.ok) throw new Error("Failed to load alert detail");
                const data = await res.json();
                setAlert(data);

                // Fetch user history
                const hist = await fetchUserHistory(data.user_id);
                setUserHistory(hist);

                // Build recommended checklist based on severity and rules
                buildChecklist(data);
            } catch (err) {
                console.error("Failed to load investigation details:", err);
            } finally {
                setLoading(false);
            }
        };

        loadDetails();
    }, [alertId]);

    const buildChecklist = (alertData: Alert) => {
        const severityActions: Record<string, string[]> = {
            'critical': [
                'Immediately terminate all active user sessions',
                'Quarantine target host system & restrict network credentials',
                'Notify SOC Director & escalate to CIRT team',
                'Preserve system audit logs & secure exfiltration dump records'
            ],
            'high': [
                'Suspend account credentials pending verification',
                'Conduct manager audit of activity profile',
                'Verify data staging destination security compliance'
            ],
            'medium': [
                'Review comprehensive logs in Full Timeline log view',
                'Examine past user profiles to identify repeating anomalies'
            ],
            'low': [
                'Log session for baseline comparison',
                'Monitor user profile for subsequent rule triggers'
            ]
        };

        const ruleActions: Record<string, string> = {
            'R30': 'Analyze staged paths on FTP/Cloud upload vectors.',
            'R29': 'Verify external email domain classification.',
            'R25': 'Audit command-line arguments executed under root/sudo privileges.',
            'R32': 'Confirm authorization for system folder discovery searches.',
            'R04': 'Map IP address geolocation for login anomalies.',
            'R37': 'Cross-reference user credentials against dark web leaks database.'
        };

        const severity = alertData.severity.toLowerCase();
        const actions = [...(severityActions[severity] || severityActions['low'])];

        // Parse triggered rules and add custom checklists
        if (alertData.rules_triggered) {
            const rules = alertData.rules_triggered.split('|');
            rules.forEach(r => {
                if (ruleActions[r]) {
                    actions.push(ruleActions[r]);
                }
            });
        }

        setChecklist(actions.map(a => ({ text: a, checked: false })));
    };

    const handleToggleChecklist = (index: number) => {
        setChecklist(prev => prev.map((item, idx) => 
            idx === index ? { ...item, checked: !item.checked } : item
        ));
    };

    const handleUpdateStatus = async (newStatus: string) => {
        if (!alertId) return;
        setStatusUpdating(true);
        try {
            await updateAlertStatus(alertId, newStatus);
            setAlert(prev => prev ? { ...prev, status: newStatus } : null);
            onAlertStatusUpdated();
        } catch (err) {
            console.error("Failed to update status:", err);
        } finally {
            setStatusUpdating(false);
        }
    };

    // MITRE ATT&CK mapping database based on rules
    const getMitreMapping = (rulesStr: string | null) => {
        if (!rulesStr) return [];
        const mappings: Record<string, { id: string; name: string; phase: string }> = {
            'R30': { id: 'T1048', name: 'Exfiltration Over Alternative Protocol', phase: 'Exfiltration' },
            'R29': { id: 'T1567', name: 'Exfiltration Over Web Service', phase: 'Exfiltration' },
            'R25': { id: 'T1548.001', name: 'Abuse Elevation Control Mechanism: Sudo', phase: 'Privilege Escalation' },
            'R32': { id: 'T1083', name: 'File and Directory Discovery', phase: 'Discovery' },
            'R04': { id: 'T1110', name: 'Brute Force Logins', phase: 'Credential Access' },
            'R37': { id: 'T1078', name: 'Valid Accounts Abuse', phase: 'Defense Evasion' }
        };

        const rules = rulesStr.split('|');
        const results: { id: string; name: string; phase: string }[] = [];
        rules.forEach(r => {
            if (mappings[r] && !results.some(existing => existing.id === mappings[r].id)) {
                results.push(mappings[r]);
            }
        });
        return results;
    };

    if (!alertId) {
        return (
            <div className="bg-[#111722] border border-white/5 rounded-xl p-6 h-full flex flex-col items-center justify-center text-center text-gray-500 gap-3 min-h-[500px]">
                <AlertOctagon className="w-10 h-10 opacity-15" />
                <div className="flex flex-col">
                    <span className="text-xs font-bold uppercase tracking-wider text-gray-400">Incident Console</span>
                    <span className="text-[10px] text-gray-600">Select an alert from the feed to begin SOC investigation.</span>
                </div>
            </div>
        );
    }

    if (loading || !alert) {
        return (
            <div className="bg-[#111722] border border-white/5 rounded-xl p-6 h-full flex items-center justify-center text-xs text-cyan-400 font-semibold min-h-[500px]">
                Assembling forensic details...
            </div>
        );
    }

    // Try parsing explanation if string, or keep object
    let expObj: Record<string, unknown> = {};
    try {
        expObj = typeof alert.explanation === 'string' 
            ? JSON.parse(alert.explanation) 
            : (alert.explanation as Record<string, unknown>);
    } catch {}

    const explanation = (expObj?.explanation as { summary?: string; reasons?: string[]; recommended_actions?: string[] }) || {};
    const model = (expObj?.model_breakdown as { ctmc_score?: number; rule_score?: number; rule_violations?: { rule_id: string; rule_name: string; severity: string }[] }) || { ctmc_score: 0.0, rule_score: 0.0, rule_violations: [] };
    const timeline = (expObj?.timeline as { timeline?: string[]; timeline_compact?: string[] }) || { timeline: [], timeline_compact: [] };
    
    const ctmcScore = model.ctmc_score ?? 0.0;
    const ruleScore = model.rule_score ?? 0.0;
    const confidence = ((expObj?.alert as { confidence?: number })?.confidence) ?? 0.85;

    const mitreTactics = getMitreMapping(alert.rules_triggered);
    const activeTimelineLogs = timelineMode === 'compact' ? timeline.timeline_compact : timeline.timeline;
    
    // Highlight risky terms in timeline logs
    const highlightRegex = /(sudo|failed|delete|modify|privilege|recon|upload|unauthorized)/i;

    return (
        <div className="bg-[#111722] border border-white/5 rounded-xl p-6 flex flex-col gap-6 h-full overflow-y-auto max-h-[1100px] custom-scrollbar">
            {/* Header info */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-white/5 pb-4">
                <div className="flex flex-col">
                    <div className="flex items-center gap-2">
                        <span className="text-[10px] font-black text-cyan-400 bg-cyan-400/5 border border-cyan-400/10 px-2 py-0.5 rounded tracking-widest uppercase">
                            Incident ALT-{alert.alert_id}
                        </span>
                        <span className={`text-[10px] font-black border px-2 py-0.5 rounded uppercase tracking-widest ${
                            alert.severity.toLowerCase() === 'critical' ? 'text-red-400 bg-red-400/5 border-red-500/25' :
                            alert.severity.toLowerCase() === 'high' ? 'text-orange-400 bg-orange-400/5 border-orange-500/25' :
                            'text-amber-400 bg-amber-400/5 border-amber-500/25'
                        }`}>
                            {alert.severity} Risk
                        </span>
                    </div>
                    <h2 className="text-lg font-bold text-gray-100 mt-2 flex items-center gap-1.5">
                        <User className="w-4 h-4 text-gray-500" />
                        {alert.user_id}
                    </h2>
                    <span className="text-[10px] text-gray-500 font-semibold mt-1">
                        Fired: {new Date(alert.created_at).toLocaleString()}
                    </span>
                </div>

                {/* Status action buttons */}
                <div className="flex gap-2">
                    <button
                        onClick={() => handleUpdateStatus('open')}
                        disabled={statusUpdating || alert.status === 'open'}
                        className={`text-[10px] font-bold uppercase tracking-wider px-3 py-1.5 rounded transition-all ${
                            alert.status === 'open' 
                                ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' 
                                : 'bg-[#171E2B] text-gray-400 border border-white/5 hover:text-gray-200'
                        }`}
                    >
                        Open
                    </button>
                    <button
                        onClick={() => handleUpdateStatus('reviewed')}
                        disabled={statusUpdating || alert.status === 'reviewed'}
                        className={`text-[10px] font-bold uppercase tracking-wider px-3 py-1.5 rounded transition-all ${
                            alert.status === 'reviewed' 
                                ? 'bg-teal-500/10 text-teal-400 border border-teal-500/20' 
                                : 'bg-[#171E2B] text-gray-400 border border-white/5 hover:text-gray-200'
                        }`}
                    >
                        Reviewed
                    </button>
                    <button
                        onClick={() => handleUpdateStatus('closed')}
                        disabled={statusUpdating || alert.status === 'closed'}
                        className={`text-[10px] font-bold uppercase tracking-wider px-3 py-1.5 rounded transition-all ${
                            alert.status === 'closed' 
                                ? 'bg-gray-500/20 text-gray-400 border border-white/10' 
                                : 'bg-[#171E2B] text-gray-400 border border-white/5 hover:text-gray-200'
                        }`}
                    >
                        Closed
                    </button>
                </div>
            </div>

            {/* Visual Dials Section */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Composite Risk Score dial */}
                <div className="bg-black/10 border border-white/5 rounded-lg p-4 flex flex-col items-center justify-center relative text-center">
                    <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wider mb-2">Composite Risk Score</span>
                    <div className="relative w-24 h-24 flex items-center justify-center">
                        <svg className="w-full h-full transform -rotate-90">
                            <circle cx="48" cy="48" r="40" stroke="rgba(255,255,255,0.03)" strokeWidth="8" fill="transparent" />
                            <motion.circle 
                                cx="48" 
                                cy="48" 
                                r="40" 
                                stroke={alert.severity.toLowerCase() === 'critical' ? '#ef4444' : '#f97316'} 
                                strokeWidth="8" 
                                fill="transparent" 
                                strokeDasharray={251.2}
                                initial={{ strokeDashoffset: 251.2 }}
                                animate={{ strokeDashoffset: 251.2 - (251.2 * alert.risk_score) / 100 }}
                                transition={{ duration: 0.6, ease: 'easeOut' }}
                                strokeLinecap="round"
                            />
                        </svg>
                        <span className="absolute text-2xl font-black text-gray-100">{Math.round(alert.risk_score)}</span>
                    </div>
                </div>

                {/* Score weights list */}
                <div className="bg-black/10 border border-white/5 rounded-lg p-4 flex flex-col justify-center gap-3">
                    <div className="flex flex-col">
                        <div className="flex justify-between text-[10px] text-gray-400 font-bold mb-1">
                            <span>CTMC ANOMALY SCORE</span>
                            <span className="text-cyan-400">{ctmcScore.toFixed(1)}</span>
                        </div>
                        <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                            <motion.div 
                                className="h-full bg-cyan-400"
                                initial={{ width: 0 }}
                                animate={{ width: `${Math.min(100, ctmcScore)}%` }}
                                transition={{ duration: 0.4 }}
                            />
                        </div>
                    </div>
                    <div className="flex flex-col">
                        <div className="flex justify-between text-[10px] text-gray-400 font-bold mb-1">
                            <span>POLICY RULE SCORE</span>
                            <span className="text-orange-400">{ruleScore.toFixed(1)}</span>
                        </div>
                        <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                            <motion.div 
                                className="h-full bg-orange-400"
                                initial={{ width: 0 }}
                                animate={{ width: `${Math.min(100, ruleScore)}%` }}
                                transition={{ duration: 0.4 }}
                            />
                        </div>
                    </div>
                </div>

                {/* Confidence indicator */}
                <div className="bg-black/10 border border-white/5 rounded-lg p-4 flex flex-col items-center justify-center text-center">
                    <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wider mb-2">Model Confidence</span>
                    <span className="text-3xl font-black bg-gradient-to-r from-teal-400 to-cyan-400 bg-clip-text text-transparent">
                        {Math.round(confidence * 100)}%
                    </span>
                    <span className="text-[9px] font-bold text-teal-400 uppercase tracking-widest mt-1">HIGH CERTAINTY</span>
                </div>
            </div>

            {/* Narrative Explanation */}
            {explanation.summary && (
                <div className="bg-black/15 border border-white/5 rounded-lg p-4 flex flex-col gap-3">
                    <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider flex items-center gap-1.5">
                        <Activity className="w-3.5 h-3.5" />
                        Analyst Narrative & Findings
                    </span>
                    <p className="text-xs text-gray-300 leading-relaxed font-medium">
                        {explanation.summary}
                    </p>
                    <ul className="list-disc pl-4 space-y-1.5 text-xs text-gray-400">
                        {explanation.reasons?.map((reason: string, idx: number) => (
                            <li key={idx} className="leading-snug">{reason}</li>
                        ))}
                    </ul>
                </div>
            )}

            {/* MITRE ATT&CK Mapping */}
            {mitreTactics.length > 0 && (
                <div className="bg-black/10 border border-white/5 rounded-lg p-4 flex flex-col gap-3">
                    <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">
                        MITRE ATT&CK® Techniques Mapped
                    </span>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {mitreTactics.map((t) => (
                            <div key={t.id} className="p-2.5 rounded bg-white/5 border border-white/5 flex flex-col gap-1">
                                <div className="flex justify-between items-center">
                                    <span className="text-[10px] font-bold text-gray-200">{t.name}</span>
                                    <span className="text-[9px] font-black text-cyan-400 flex items-center gap-0.5">
                                        {t.id}
                                        <ExternalLink className="w-2.5 h-2.5" />
                                    </span>
                                </div>
                                <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wider">
                                    Phase: {t.phase}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Timeline Logs Section */}
            <div className="flex flex-col gap-3">
                <div className="flex justify-between items-center border-b border-white/5 pb-2">
                    <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5" />
                        Behavior Timeline Logs
                    </span>
                    <div className="flex bg-[#171E2B] border border-white/5 rounded p-0.5 gap-0.5">
                        <button
                            onClick={() => setTimelineMode('compact')}
                            className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded transition-all ${
                                timelineMode === 'compact' ? 'bg-cyan-500/10 text-cyan-400' : 'text-gray-500 hover:text-gray-300'
                            }`}
                        >
                            Compact
                        </button>
                        <button
                            onClick={() => setTimelineMode('full')}
                            className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded transition-all ${
                                timelineMode === 'full' ? 'bg-cyan-500/10 text-cyan-400' : 'text-gray-500 hover:text-gray-300'
                            }`}
                        >
                            Full Log
                        </button>
                    </div>
                </div>

                <div className="max-h-[300px] overflow-y-auto border border-white/5 rounded bg-black/25 p-3 font-mono text-[10px] space-y-2 custom-scrollbar">
                    {activeTimelineLogs?.length === 0 ? (
                        <div className="text-gray-600 italic">No events recorded in this timeline.</div>
                    ) : (
                        activeTimelineLogs?.map((log: string, idx: number) => {
                            const isAnomaly = highlightRegex.test(log);
                            return (
                                <div key={idx} className={`flex items-start gap-2 ${isAnomaly ? 'text-red-400' : 'text-gray-400'}`}>
                                    <span className="text-[8px] text-gray-600 select-none">[{idx + 1}]</span>
                                    <span>{log}</span>
                                </div>
                            );
                        })
                    )}
                </div>
            </div>

            {/* Recommended Checklist */}
            <div className="bg-black/10 border border-white/5 rounded-lg p-4 flex flex-col gap-3">
                <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider flex items-center gap-1.5">
                    <CheckSquare className="w-3.5 h-3.5" />
                    Interactive Response Playbook
                </span>
                <div className="space-y-2">
                    {checklist.map((item, idx) => (
                        <label 
                            key={idx} 
                            className={`flex items-start gap-2.5 p-2 rounded bg-white/[0.02] border border-white/5 cursor-pointer select-none transition-colors ${
                                item.checked ? 'border-teal-500/20 bg-teal-500/[0.01]' : 'hover:bg-white/[0.04]'
                            }`}
                        >
                            <input 
                                type="checkbox" 
                                checked={item.checked} 
                                onChange={() => handleToggleChecklist(idx)}
                                className="mt-0.5 rounded border-white/10 bg-transparent text-teal-400 focus:ring-0 cursor-pointer"
                            />
                            <span className={`text-xs transition-all duration-200 ${
                                item.checked ? 'text-gray-500 line-through' : 'text-gray-300'
                            }`}>
                                {item.text}
                            </span>
                        </label>
                    ))}
                </div>
            </div>

            {/* User History Widget */}
            {userHistory && (
                <div className="bg-black/10 border border-white/5 rounded-lg p-4 flex flex-col gap-3">
                    <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">
                        User Investigation History
                    </span>
                    <div className="grid grid-cols-3 gap-2 text-center text-[10px] mb-2">
                        <div className="bg-white/5 border border-white/5 rounded p-2 flex flex-col">
                            <span className="text-gray-500 uppercase tracking-wider">Total Alerts</span>
                            <strong className="text-base font-black text-gray-200">{userHistory.alerts.length}</strong>
                        </div>
                        <div className="bg-white/5 border border-white/5 rounded p-2 flex flex-col">
                            <span className="text-gray-500 uppercase tracking-wider">Total Events</span>
                            <strong className="text-base font-black text-gray-200">{userHistory.total_events}</strong>
                        </div>
                        <div className="bg-white/5 border border-white/5 rounded p-2 flex flex-col">
                            <span className="text-gray-500 uppercase tracking-wider">Status</span>
                            <strong className="text-base font-black text-teal-400">ACTIVE</strong>
                        </div>
                    </div>
                    {userHistory.alerts.length > 1 && (
                        <div className="flex flex-col gap-1.5">
                            <span className="text-[9px] font-bold text-gray-500 uppercase tracking-wider">
                                Previous Alerts
                            </span>
                            <div className="space-y-1 max-h-[120px] overflow-y-auto custom-scrollbar">
                                {userHistory.alerts
                                    .filter(a => a.alert_id !== alertId)
                                    .map(a => (
                                        <div key={a.alert_id} className="flex justify-between items-center p-1.5 rounded bg-white/[0.02] border border-white/5 text-[9px]">
                                            <span className="text-gray-400 font-bold">ALT-{a.alert_id}</span>
                                            <span className="text-gray-500">{new Date(a.created_at).toLocaleDateString()}</span>
                                            <span className="text-orange-400 font-bold">Risk: {Math.round(a.risk_score)}</span>
                                        </div>
                                    ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
