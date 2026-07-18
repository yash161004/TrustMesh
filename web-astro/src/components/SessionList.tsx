import { useEffect, useState } from 'react';
import { useAuth } from '@clerk/astro/react';
import { listSessions, type SessionResponse } from '../lib/api';

const STATUS_DOT: Record<string, string> = {
  PENDING: 'bg-dot-flagged',
  ACTIVE: 'bg-dot-active',
  COMPLETED: 'bg-dot-completed',
  FAILED: 'bg-dot-flagged',
};

function formatStatus(status: string) {
  return status.charAt(0) + status.slice(1).toLowerCase();
}

export default function SessionList() {
  const { getToken, isLoaded } = useAuth();
  const [sessions, setSessions] = useState<SessionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded) return;

    let cancelled = false;

    async function load() {
      try {
        const token = await getToken();
        if (!token) throw new Error('Not authenticated');
        const data = await listSessions(token);
        if (!cancelled) setSessions(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load sessions');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [isLoaded, getToken]);

  if (loading) {
    return (
      <div class="flex flex-col items-center justify-center rounded-card border border-border bg-surface-800 px-card py-20">
        <svg class="h-6 w-6 animate-spin text-text-muted" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <p class="mt-3 text-sm text-text-secondary">Loading sessions…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div class="flex flex-col items-center justify-center rounded-card border border-dot-flagged/30 bg-dot-flagged/10 px-card py-20">
        <p class="text-sm text-dot-flagged">{error}</p>
        <button
          onClick={() => window.location.reload()}
          class="mt-3 text-sm text-text-secondary hover:text-text-primary transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div class="flex flex-col items-center justify-center rounded-card border border-border bg-surface-800 px-card py-20">
        <div class="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-surface-750">
          <svg class="h-6 w-6 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 0 1-.825-.242m9.345-8.334a2.126 2.126 0 0 0-.476-.095 48.64 48.64 0 0 0-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0 0 11.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
          </svg>
        </div>
        <h3 class="text-base font-semibold text-text-primary">No sessions yet</h3>
        <p class="mt-1 text-sm text-text-secondary">
          Launch your first negotiation to get started.
        </p>
      </div>
    );
  }

  return (
    <div class="space-y-2">
      {sessions.map((s) => (
        <a
          key={s.session_id}
          href={`/dashboard/sessions/${s.session_id}`}
          class="flex flex-wrap items-center gap-2 rounded-card border border-border bg-surface-800 px-card py-3.5 transition-colors duration-150 hover:border-border-hover hover:bg-surface-750 sm:flex-nowrap sm:justify-between"
        >
          <div class="flex items-center gap-3 min-w-0">
            <span class={`h-2 w-2 shrink-0 rounded-full ${STATUS_DOT[s.status] ?? 'bg-text-muted'}`} />
            <div class="min-w-0">
              <h3 class="truncate text-sm font-medium text-text-primary">{s.buyer_agent_id} → {s.seller_agent_id}</h3>
              <p class="mt-px text-xs text-text-muted font-mono">{s.session_id.slice(0, 12)}…</p>
            </div>
          </div>

          <div class="flex w-full items-center justify-between gap-3 sm:w-auto sm:gap-6">
            <div class="text-xs text-text-secondary">
              <span class={`inline-block rounded px-1.5 py-0.5 text-[10px] font-medium ${
                s.status === 'ACTIVE' ? 'bg-dot-active/20 text-dot-active' :
                s.status === 'COMPLETED' ? 'bg-dot-completed/20 text-dot-completed' :
                s.status === 'FAILED' ? 'bg-dot-flagged/20 text-dot-flagged' :
                'bg-surface-750 text-text-muted'
              }`}>
                {formatStatus(s.status)}
              </span>
              <span class="ml-2 text-text-muted">{s.message_count} msg{s.message_count !== 1 ? 's' : ''}</span>
            </div>
            <div class="shrink-0 text-right font-mono text-[10px] text-text-muted">
              {new Date(s.created_at).toLocaleDateString()}
            </div>
          </div>
        </a>
      ))}
    </div>
  );
}
