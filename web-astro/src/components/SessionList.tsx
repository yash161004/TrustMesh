import { useEffect, useState } from 'react';
import { useAuth } from '@clerk/astro/react';
import { listSessions, loadDemoData, type SessionResponse } from '../lib/api';

const STATUS_DOT: Record<string, string> = {
  PENDING: 'bg-dot-flagged',
  ACTIVE: 'bg-dot-active',
  COMPLETED: 'bg-dot-completed',
  FAILED: 'bg-dot-flagged',
};

function formatStatus(status: string) {
  return status.charAt(0) + status.slice(1).toLowerCase();
}

interface Props {
  clerkBypass?: boolean;
}

export default function SessionList({ clerkBypass }: Props = {}) {
  const auth = useAuth();
  const { getToken, isLoaded } = auth;
  const [sessions, setSessions] = useState<SessionResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [loadingDemo, setLoadingDemo] = useState(false);

  useEffect(() => {
    if (!isLoaded && !clerkBypass) return;

    let cancelled = false;

    async function load() {
      try {
        const token = clerkBypass ? "mock_token" : (await getToken() || "mock_token");
        
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
  }, [isLoaded, getToken, clerkBypass]);

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

  const handleLoadDemo = async () => {
    setLoadingDemo(true);
    try {
      const token = (await getToken() || "mock_token");
      if (token) {
        await loadDemoData(token);
        window.location.reload();
      }
    } catch (err) {
      console.error(err);
      setLoadingDemo(false);
    }
  };

  if (sessions.length === 0) {
    return (
      <div class="flex flex-col items-center justify-center rounded-card border border-border bg-surface-800 px-card py-20 text-center">
        <div class="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-surface-750">
          <svg class="h-6 w-6 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 0 1-.825-.242m9.345-8.334a2.126 2.126 0 0 0-.476-.095 48.64 48.64 0 0 0-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0 0 11.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
          </svg>
        </div>
        <h3 class="text-base font-semibold text-text-primary">No sessions yet</h3>
        <p class="mt-1 mb-6 text-sm text-text-secondary max-w-sm">
          TrustMesh is empty. You can either start a new negotiation from scratch or load historical demo data to explore the ledger and manipulation detector instantly.
        </p>
        <div class="flex flex-col sm:flex-row gap-3">
          <a
            href="/dashboard/new"
            class="inline-flex items-center justify-center rounded-card bg-gold px-5 py-2.5 text-sm font-medium text-surface-900 transition-colors hover:bg-gold-hover"
          >
            Create your first negotiation
          </a>
          <button
            onClick={handleLoadDemo}
            disabled={loadingDemo}
            class="inline-flex items-center justify-center rounded-card border border-border bg-surface-800 px-5 py-2.5 text-sm font-medium text-text-primary transition-colors hover:bg-surface-750 disabled:opacity-50"
          >
            {loadingDemo ? 'Loading...' : 'Load demo data'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
      {sessions.map((s) => (
        <a
          key={s.session_id}
          href={`/dashboard/sessions/${s.session_id}`}
          class="flex flex-col justify-between overflow-hidden rounded-card border border-border bg-surface-800 transition-all duration-200 hover:border-border-hover hover:bg-surface-750 hover:shadow-xl hover:shadow-black/20 group"
        >
          <div class="p-card pb-0">
            <div class="flex items-center justify-between mb-4">
              <span class={`inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-[10px] font-medium tracking-wide ${
                s.status === 'ACTIVE' ? 'bg-dot-active/10 text-dot-active border border-dot-active/20' :
                s.status === 'COMPLETED' ? 'bg-dot-completed/10 text-dot-completed border border-dot-completed/20' :
                s.status === 'FAILED' ? 'bg-dot-flagged/10 text-dot-flagged border border-dot-flagged/20' :
                'bg-surface-750 text-text-muted border border-border'
              }`}>
                <span class={`h-1.5 w-1.5 rounded-full ${STATUS_DOT[s.status] ?? 'bg-text-muted'}`} />
                {formatStatus(s.status)}
              </span>
              <span class="text-[10px] font-mono text-text-muted uppercase tracking-wider">
                {new Date(s.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
              </span>
            </div>

            <div class="mb-4">
              <h3 class="text-sm font-semibold text-text-primary tracking-wide truncate">{s.buyer_agent_id}</h3>
              <p class="text-[13px] text-text-secondary mt-0.5 truncate flex items-center gap-2">
                <span class="text-text-muted italic text-[11px]">vs</span> {s.seller_agent_id}
              </p>
            </div>

            <div class="flex items-center gap-4 text-[11px] font-mono text-text-muted">
              <div class="flex items-center gap-1.5 bg-surface-900/50 px-2 py-1 rounded">
                <svg class="h-3 w-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                {s.message_count}
              </div>
              <div class="bg-surface-900/50 px-2 py-1 rounded">ID: {s.session_id.slice(0, 8)}</div>
            </div>
          </div>
        </a>
      ))}
    </div>
  );
}
