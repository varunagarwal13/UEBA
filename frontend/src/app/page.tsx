'use client';

import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Header from '@/components/Header';
import MetricBanner from '@/components/MetricBanner';
import Topology from '@/components/Topology';
import AlertFeed from '@/components/AlertFeed';
import Leaderboard from '@/components/Leaderboard';
import ChartsPanel from '@/components/ChartsPanel';
import InvestigationConsole from '@/components/InvestigationConsole';
import { 
    fetchSimulatorStatus, 
    stepSimulation, 
    resetSimulation, 
    toggleAutoRun, 
    fetchAlerts, 
    fetchRiskProfiles, 
    fetchDashboardCharts,
    SimulationStepResponse
} from '@/lib/api';

export default function SOCDashboard() {
    const queryClient = useQueryClient();
    const [selectedAlertId, setSelectedAlertId] = useState<number | null>(null);
    const [latestStepResult, setLatestStepResult] = useState<SimulationStepResponse | null>(null);

    // ── DATA QUERIES ──
    const { data: stats } = useQuery({
        queryKey: ['simulatorStatus'],
        queryFn: fetchSimulatorStatus,
        refetchInterval: 5000, // Background status sync
    });

    const { data: alerts = [] } = useQuery({
        queryKey: ['alerts'],
        queryFn: () => fetchAlerts(),
        refetchInterval: 4000,
    });

    const { data: riskProfiles = [] } = useQuery({
        queryKey: ['riskProfiles'],
        queryFn: fetchRiskProfiles,
        refetchInterval: 5000,
    });

    const { data: chartsData = null } = useQuery({
        queryKey: ['dashboardCharts'],
        queryFn: fetchDashboardCharts,
        refetchInterval: 5000,
    });

    // ── MUTATIONS ──
    const stepMutation = useMutation({
        mutationFn: stepSimulation,
        onSuccess: (data) => {
            if (data.status === 'completed') {
                // If simulator finished the split, toggle off auto run if active
                if (stats?.auto_run) {
                    toggleAutoRunMutation.mutate();
                }
                alert("All sessions in the test split have been processed!");
                return;
            }

            // Capture pipeline trace to trigger topology animation
            if (data.pipeline_trace) {
                setLatestStepResult(data);
                
                // If a new alert was fired, auto-select it in console
                if (data.alert_triggered && data.pipeline_trace.alert_id) {
                    setSelectedAlertId(data.pipeline_trace.alert_id as unknown as number);
                }
            }

            // Force reload data queries
            queryClient.invalidateQueries({ queryKey: ['simulatorStatus'] });
            queryClient.invalidateQueries({ queryKey: ['alerts'] });
            queryClient.invalidateQueries({ queryKey: ['riskProfiles'] });
            queryClient.invalidateQueries({ queryKey: ['dashboardCharts'] });
        },
        onError: (err) => {
            console.error("Step simulation failed:", err);
        }
    });

    const toggleAutoRunMutation = useMutation({
        mutationFn: toggleAutoRun,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['simulatorStatus'] });
        }
    });

    const resetMutation = useMutation({
        mutationFn: resetSimulation,
        onSuccess: () => {
            setSelectedAlertId(null);
            setLatestStepResult(null);
            queryClient.invalidateQueries({ queryKey: ['simulatorStatus'] });
            queryClient.invalidateQueries({ queryKey: ['alerts'] });
            queryClient.invalidateQueries({ queryKey: ['riskProfiles'] });
            queryClient.invalidateQueries({ queryKey: ['dashboardCharts'] });
            alert("Simulator and database reset successfully.");
        }
    });

    // ── AUTO-RUN INTERVAL LOOP ──
    useEffect(() => {
        let intervalId: NodeJS.Timeout | null = null;

        if (stats?.auto_run) {
            // Trigger a step immediately when toggled on
            stepMutation.mutate();

            intervalId = setInterval(() => {
                // Only step if previous step is not loading
                if (!stepMutation.isPending) {
                    stepMutation.mutate();
                }
            }, 1800);
        }

        return () => {
            if (intervalId) clearInterval(intervalId);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [stats?.auto_run]);

    const handleSelectAlert = (alertId: number) => {
        setSelectedAlertId(alertId);
    };

    const handleAlertStatusUpdated = () => {
        queryClient.invalidateQueries({ queryKey: ['alerts'] });
    };

    const handleResetConfirm = () => {
        if (confirm("Are you sure you want to reset the simulator? This deletes all generated alerts, resets stats, and truncates the database.")) {
            resetMutation.mutate();
        }
    };

    const uniqueUsersCount = riskProfiles.length;

    return (
        <div className="flex flex-col gap-6 p-6 max-w-[1600px] mx-auto w-full">
            {/* Header controls & status */}
            <Header 
                stats={stats || null}
                onStep={() => stepMutation.mutate()}
                onToggleAutoRun={() => toggleAutoRunMutation.mutate()}
                onReset={handleResetConfirm}
                isStepLoading={stepMutation.isPending}
                isResetLoading={resetMutation.isPending}
                isAutoRunLoading={toggleAutoRunMutation.isPending}
            />

            {/* Top KPI statistics */}
            <MetricBanner 
                stats={stats || null}
                totalUsers={uniqueUsersCount}
            />

            {/* Live pipeline topology stream */}
            <Topology 
                trace={latestStepResult?.pipeline_trace || null}
                isSimulating={stepMutation.isPending || (stats?.auto_run ?? false)}
            />

            {/* Main workspace layout split */}
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 w-full items-start">
                
                {/* Left Section: Alert feed + Leaderboard */}
                <div className="xl:col-span-4 flex flex-col gap-6">
                    <div className="bg-[#111722] border border-white/5 rounded-xl p-4">
                        <AlertFeed 
                            alerts={alerts}
                            selectedAlertId={selectedAlertId}
                            onSelectAlert={handleSelectAlert}
                        />
                    </div>

                    <Leaderboard profiles={riskProfiles} />
                </div>

                {/* Center Section: Charts and Analytics Trend logs */}
                <div className="xl:col-span-4 flex flex-col gap-6">
                    <ChartsPanel data={chartsData} />
                    
                    {/* Simulator context metadata */}
                    <div className="bg-[#111722] border border-white/5 rounded-xl p-4 text-xs flex flex-col gap-2">
                        <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">System Log Baseline</span>
                        <div className="space-y-1.5 font-mono text-[10px] text-gray-400">
                            <div>[INFO] Model Baseline transitions built on 80% split</div>
                            <div>[INFO] Continuous Markov chain parameters loaded</div>
                            <div>[INFO] Policy checking: 13 heuristics rules initialized</div>
                            {latestStepResult && (
                                <div className="text-cyan-400">
                                    [STREAM] User {latestStepResult.user_id} session {latestStepResult.session_id.substring(0,8)} processed. Alert status: {latestStepResult.alert_triggered ? 'FIRED' : 'NORMAL'}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Right Section: Investigation panel */}
                <div className="xl:col-span-4 h-full">
                    <InvestigationConsole 
                        alertId={selectedAlertId}
                        onAlertStatusUpdated={handleAlertStatusUpdated}
                    />
                </div>

            </div>
        </div>
    );
}

