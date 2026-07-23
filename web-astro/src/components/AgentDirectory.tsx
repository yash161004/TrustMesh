import { useEffect, useState } from 'react';
import { useAuth } from '@clerk/astro/react';
import { listAgentCards, getAgentReputation, type AgentCardResponse, type AgentReputationResponse } from '../lib/api';

export default function AgentDirectory() {
  const { getToken, isLoaded } = useAuth();
  const [agents, setAgents] = useState<AgentCardResponse[]>([]);
  const [reputations, setReputations] = useState<Record<string, AgentReputationResponse>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const token = (await getToken() || "mock_token");
        if (!token) return;
        const data = await listAgentCards(token);
        setAgents(data);

        const repMap: Record<string, AgentReputationResponse> = {};
        await Promise.all(
          data.map(async (agent) => {
            try {
              const rep = await getAgentReputation(token, agent.agent_id);
              repMap[agent.agent_id] = rep;
            } catch {
              // Ignore reputation fetch failure per individual agent card
            }
          })
        );
        setReputations(repMap);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load agent cards');
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

  return (
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {agents.map(agent => (
        <div key={agent.agent_id} class="rounded-card border border-border bg-surface-800 flex flex-col h-full overflow-hidden">
          <div class="p-5 border-b border-border/50 bg-surface-800 flex justify-between items-start">
            <div>
              <h3 class="text-lg font-semibold text-text-primary tracking-tight">{agent.display_name}</h3>
              <p class="text-xs text-text-muted mt-1 font-mono uppercase tracking-wider">{agent.role} AGENT</p>
            </div>
            {agent.is_verified ? (
              <span class="inline-flex items-center gap-1 rounded-full bg-dot-completed/10 px-2 py-1 text-[10px] font-medium text-dot-completed border border-dot-completed/20">
                <svg class="w-3 h-3" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clipRule="evenodd" />
                </svg>
                VERIFIED
              </span>
            ) : (
              <span class="inline-flex items-center gap-1 rounded-full bg-dot-flagged/10 px-2 py-1 text-[10px] font-medium text-dot-flagged border border-dot-flagged/20">
                <svg class="w-3 h-3" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd" />
                </svg>
                TAMPERED
              </span>
            )}
          </div>
          
          <div class="p-5 flex-grow flex flex-col gap-4 bg-surface-900/30">
            <div>
              <p class="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2">Capabilities</p>
              <div class="flex flex-wrap gap-2">
                {agent.capabilities.map(cap => (
                  <span key={cap} class="inline-flex items-center rounded bg-surface-700/50 px-2 py-1 text-[11px] font-medium text-text-primary border border-border/50">
                    {cap.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
            
            <div class="mt-auto pt-4 border-t border-border/30">
              <p class="text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-1">Public Key (Ed25519)</p>
              <p class="text-[10px] font-mono text-text-secondary truncate bg-surface-900 p-1.5 rounded border border-border/50">
                {agent.public_key}
              </p>
            </div>
            
            <div>
              <p class="text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-1">Agent ID</p>
              <p class="text-[10px] font-mono text-text-secondary truncate">
                {agent.agent_id}
              </p>
            </div>

            {reputations[agent.agent_id] && (
              <div class="pt-3 border-t border-border/30">
                <p class="text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-1.5">Cross-Session Reputation</p>
                <div class="flex items-center justify-between text-xs bg-surface-900 p-2 rounded border border-border/50">
                  <div class="flex items-center gap-1.5">
                    <span class="font-bold text-text-primary">
                      {(reputations[agent.agent_id].trust_score * 100).toFixed(0)}%
                    </span>
                    <span class="text-[10px] text-text-muted">Trust</span>
                  </div>
                  <div class="flex gap-3 text-[10px] text-text-muted">
                    <span>{reputations[agent.agent_id].total_sessions} session{reputations[agent.agent_id].total_sessions === 1 ? '' : 's'}</span>
                    <span>{reputations[agent.agent_id].violations_count} violation{reputations[agent.agent_id].violations_count === 1 ? '' : 's'}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      ))}
      
      {agents.length === 0 && (
        <div class="col-span-full py-12 text-center border border-dashed border-border rounded-card bg-surface-800/50">
          <p class="text-sm text-text-muted">No AgentCards found in the directory.</p>
        </div>
      )}
    </div>
  );
}
