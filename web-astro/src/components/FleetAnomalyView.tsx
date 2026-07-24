import { useEffect, useState } from 'react';
import { useAuth } from '@clerk/astro/react';
import { getFleetAnomalies, type FleetAnomalyResponse } from '../lib/api';

export default function FleetAnomalyView() {
  const { getToken, isLoaded } = useAuth();
  const [data, setData] = useState<FleetAnomalyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const token = (await getToken()) || 'mock_token';
        if (!token) return;
        const res = await getFleetAnomalies(token);
        setData(res);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load fleet anomaly data');
      } finally {
        setLoading(false);
      }
    }
    if (isLoaded) load();
  }, [isLoaded, getToken]);

  if (loading) {
    return (
      <div class="flex items-center justify-center py-20">
        <svg class="h-6 w-6 animate-spin text-text-muted" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
    );
  }

  if (error) {
    return (
      <div class="rounded-card border border-dot-flagged/30 bg-dot-flagged/10 px-card py-16 text-center">
        <p class="text-sm text-dot-flagged">{error}</p>
      </div>
    );
  }

  const agents = data?.agents || [];

  return (
    <div class="flex flex-col gap-6">
      {data?.note && (
        <div class="rounded-card border border-gold-dim/40 bg-gold-dim/10 p-4 text-xs text-gold">
          <div class="flex items-center gap-2">
            <svg class="h-4 w-4 shrink-0 text-gold" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{data.note}</span>
          </div>
        </div>
      )}

      {agents.length === 0 ? (
        <div class="rounded-card border border-border bg-surface-800 p-12 text-center">
          <div class="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-surface-700/50 text-text-muted">
            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h3 class="text-sm font-semibold text-text-primary">No Agents Recorded</h3>
          <p class="mt-1 text-xs text-text-secondary">No negotiation sessions have been recorded in your organization yet.</p>
        </div>
      ) : (
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {agents.map((agent) => {
            const isAnomalous = agent.is_anomalous === true;
            return (
              <div
                key={agent.agent_id}
                class={`rounded-card border flex flex-col h-full overflow-hidden transition-colors ${
                  isAnomalous
                    ? 'border-dot-flagged bg-dot-flagged/10 shadow-lg shadow-dot-flagged/10'
                    : 'border-border bg-surface-800'
                }`}
              >
                <div class="p-5 border-b border-border/50 flex justify-between items-start">
                  <div>
                    <h3 class="text-sm font-bold text-text-primary font-mono tracking-tight">{agent.agent_id}</h3>
                    <p class="text-[11px] text-text-muted mt-0.5">Fleet Agent</p>
                  </div>
                  {isAnomalous ? (
                    <span class="inline-flex items-center gap-1 rounded-full bg-dot-flagged/20 px-2 py-0.5 text-[10px] font-bold text-dot-flagged border border-dot-flagged/40 uppercase tracking-wider">
                      <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      ANOMALOUS
                    </span>
                  ) : agent.is_anomalous === false ? (
                    <span class="inline-flex items-center gap-1 rounded-full bg-dot-active/10 px-2 py-0.5 text-[10px] font-medium text-dot-active border border-dot-active/20 uppercase tracking-wider">
                      <svg class="w-3 h-3" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clipRule="evenodd" />
                      </svg>
                      NORMAL
                    </span>
                  ) : (
                    <span class="inline-flex items-center gap-1 rounded-full bg-surface-700/50 px-2 py-0.5 text-[10px] font-medium text-text-muted border border-border/50 uppercase tracking-wider">
                      NORMAL
                    </span>
                  )}
                </div>

                <div class="p-5 flex-grow grid grid-cols-2 gap-4 bg-surface-900/30">
                  <div>
                    <p class="text-[10px] font-semibold text-text-muted uppercase tracking-wider">Total Sessions</p>
                    <p class="text-sm font-semibold text-text-primary mt-1">{agent.total_sessions}</p>
                  </div>

                  <div>
                    <p class="text-[10px] font-semibold text-text-muted uppercase tracking-wider">Violations</p>
                    <p class={`text-sm font-semibold mt-1 ${agent.violations_count > 0 ? 'text-dot-flagged' : 'text-text-primary'}`}>
                      {agent.violations_count}
                    </p>
                  </div>

                  <div>
                    <p class="text-[10px] font-semibold text-text-muted uppercase tracking-wider">Violation Rate</p>
                    <p class="text-sm font-semibold text-text-primary mt-1 font-mono">
                      {(agent.violation_rate * 100).toFixed(1)}%
                    </p>
                  </div>

                  <div>
                    <p class="text-[10px] font-semibold text-text-muted uppercase tracking-wider">Avg Trust Score</p>
                    <p class="text-sm font-semibold text-text-primary mt-1 font-mono">
                      {agent.average_trust_score !== null ? `${(agent.average_trust_score * 100).toFixed(0)}%` : 'N/A'}
                    </p>
                  </div>

                  <div class="col-span-2 pt-3 border-t border-border/30 flex justify-between items-center">
                    <span class="text-[10px] font-semibold text-text-muted uppercase tracking-wider">Z-Score</span>
                    <span class={`text-xs font-mono font-bold ${isAnomalous ? 'text-dot-flagged' : 'text-text-secondary'}`}>
                      {agent.z_score !== null ? agent.z_score.toFixed(2) : 'N/A'}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
