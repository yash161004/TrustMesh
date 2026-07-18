import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuth } from '@clerk/astro/react';
import {
  getSession,
  getSessionMessages,
  getTrustReport,
  getWebSocketUrl,
  type SessionResponse,
  type NegotiationMessage,
  type TrustReport,
} from '../lib/api';

function getSessionIdFromUrl(): string | null {
  const match = window.location.pathname.match(/\/dashboard\/sessions\/([^/]+)/);
  return match?.[1] ?? null;
}

function severityClass(severity: string) {
  switch (severity) {
    case 'high': return 'border-l-dot-flagged';
    case 'medium': return 'border-l-dot-active';
    default: return 'border-l-border';
  }
}

function messageText(msg: NegotiationMessage): string {
  if (msg.notes) return msg.notes;
  if (msg.delivery_terms) return msg.delivery_terms;
  return msg.message_type.replace(/_/g, ' ').toLowerCase();
}

interface Props {
  sessionId?: string;
}

export default function SessionView({ sessionId: propSessionId }: Props = {}) {
  const { getToken, isLoaded } = useAuth();
  const [sessionId] = useState<string | null>(() => propSessionId ?? getSessionIdFromUrl());

  const [session, setSession] = useState<SessionResponse | null>(null);
  const [messages, setMessages] = useState<NegotiationMessage[]>([]);
  const [trust, setTrust] = useState<TrustReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'forbidden' | 'closed'>('disconnected');

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmountedRef = useRef(false);
  const sessionRef = useRef<SessionResponse | null>(null);

  const isTerminal = (status: string) => status === 'COMPLETED' || status === 'FAILED';

  const connectWs = useCallback(async () => {
    if (unmountedRef.current || !sessionId) return;

    const sess = sessionRef.current;
    if (sess && isTerminal(sess.status)) {
      if (!unmountedRef.current) setWsStatus('closed');
      return;
    }

    try {
      const token = await getToken();
      if (!token || unmountedRef.current) return;

      setWsStatus('connecting');
      const url = getWebSocketUrl(sessionId, token);
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!unmountedRef.current) setWsStatus('connected');
      };

      ws.onmessage = (event) => {
        if (unmountedRef.current) return;
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'history' && Array.isArray(data.messages)) {
            setMessages(data.messages);
          } else if (data.type === 'new_message' && data.message) {
            setMessages((prev) => [...prev, data.message]);
          }
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = (event) => {
        if (unmountedRef.current) return;
        wsRef.current = null;

        if (event.code === 4003) {
          setWsStatus('forbidden');
          return;
        }

        const sess = sessionRef.current;
        if (sess && isTerminal(sess.status)) {
          setWsStatus('closed');
          return;
        }

        setWsStatus('disconnected');
        reconnectTimer.current = setTimeout(connectWs, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      if (!unmountedRef.current) setWsStatus('disconnected');
    }
  }, [getToken, sessionId]);

  useEffect(() => {
    unmountedRef.current = false;

    async function load() {
      if (!sessionId) {
        setError('Invalid session URL');
        setLoading(false);
        return;
      }

      try {
        const token = await getToken();
        if (!token || unmountedRef.current) return;

        const [sess, msgs, trustReport] = await Promise.all([
          getSession(token, sessionId),
          getSessionMessages(token, sessionId).catch(() => []),
          getTrustReport(token, sessionId).catch(() => null),
        ]);

        if (unmountedRef.current) return;
        setSession(sess);
        sessionRef.current = sess;
        setMessages(msgs);
        setTrust(trustReport);
      } catch (err) {
        if (!unmountedRef.current) {
          setError(err instanceof Error ? err.message : 'Failed to load session');
        }
      } finally {
        if (!unmountedRef.current) setLoading(false);
      }
    }

    if (isLoaded) load();
    return () => { unmountedRef.current = true; };
  }, [isLoaded, getToken, sessionId]);

  // WebSocket connection
  useEffect(() => {
    if (!loading && session && !error) {
      connectWs();
    }
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [loading, session, error, connectWs]);

  if (loading) {
    return (
      <div class="flex items-center justify-center py-20">
        <svg class="h-6 w-6 animate-spin text-text-muted" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <span class="ml-3 text-sm text-text-secondary">Loading session…</span>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div class="rounded-card border border-dot-flagged/30 bg-dot-flagged/10 px-card py-16 text-center">
        <p class="text-sm text-dot-flagged">{error ?? 'Session not found'}</p>
        <a href="/dashboard" class="mt-4 inline-block text-sm text-text-secondary hover:text-text-primary transition-colors">
          Back to Sessions
        </a>
      </div>
    );
  }

  const wsBadge = {
    connecting: 'bg-dot-active/20 text-dot-active',
    connected: 'bg-dot-completed/20 text-dot-completed',
    disconnected: 'bg-surface-750 text-text-muted',
    forbidden: 'bg-dot-flagged/20 text-dot-flagged',
    closed: 'bg-surface-750 text-text-muted',
  }[wsStatus];

  const wsLabel = {
    connecting: 'Connecting',
    connected: 'Live',
    disconnected: 'Disconnected',
    forbidden: 'Forbidden',
    closed: 'Session ended',
  }[wsStatus];

  return (
    <div class="grid grid-cols-1 gap-5 lg:grid-cols-3">
      {/* Transcript */}
      <div class="lg:col-span-2 space-y-4">
        <div class="rounded-card border border-border bg-surface-800 px-card py-card">
          <div class="mb-4 flex items-center justify-between">
            <h2 class="text-sm font-semibold text-text-primary tracking-wide">Transcript</h2>
            <span class={`rounded px-1.5 py-0.5 text-[10px] font-medium ${wsBadge}`}>
              {wsLabel}
            </span>
          </div>
          <div class="space-y-2">
            {messages.length === 0 && (
              <p class="text-sm text-text-muted text-center py-8">No messages yet. Start the session to begin negotiation.</p>
            )}
            {messages.map((msg) => (
              <div
                key={msg.turn_number}
                class={`rounded-card border border-border p-3 transition-colors duration-150 ${
                  msg.sender.includes('seller') ? 'bg-surface-750' : 'bg-surface-800'
                }`}
              >
                <div class="mb-1 flex items-center justify-between">
                  <span class="text-[11px] font-medium uppercase tracking-widest text-text-muted">
                    {msg.sender.includes('buyer') ? 'Buyer' : 'Seller'} &middot; Turn {msg.turn_number}
                  </span>
                  <span class="font-mono text-xs text-text-secondary">${msg.price}/unit</span>
                </div>
                <p class="text-sm text-text-primary">{messageText(msg)}</p>
                {msg.notes && msg.notes !== messageText(msg) && (
                  <p class="mt-1 text-xs text-text-muted italic">{msg.notes}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Sidebar */}
      <div class="space-y-3">
        {/* Trust score */}
        <div class="rounded-card border border-border bg-surface-800 px-card py-card text-center">
          <p class="text-[10px] font-medium uppercase tracking-widest text-text-muted">Trust Score</p>
          <p class={`mt-2 font-mono text-3xl font-bold ${
            (trust?.buyer_score?.overall_score ?? 0) >= 60 ? 'text-gold' : 'text-text-muted'
          }`}>
            {trust?.buyer_score?.overall_score?.toFixed(0) ?? '—'}
          </p>
          {trust?.seller_score && (
            <p class="mt-1 text-xs text-text-muted">
              Seller: {trust.seller_score.overall_score?.toFixed(0) ?? '—'}
            </p>
          )}
        </div>

        {/* Details */}
        <div class="rounded-card border border-border bg-surface-800 px-card py-card">
          <h3 class="mb-3 text-xs font-semibold text-text-primary tracking-wide">Details</h3>
          <dl class="space-y-2 text-sm">
            <div class="flex justify-between">
              <dt class="text-text-muted text-xs">Session</dt>
              <dd class="font-mono text-xs text-text-primary">{session.session_id.slice(0, 12)}…</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-text-muted text-xs">Status</dt>
              <dd class="text-text-primary">
                <span class={`inline-block rounded px-1.5 py-0.5 text-[10px] font-medium ${
                  session.status === 'ACTIVE' ? 'bg-dot-active/20 text-dot-active' :
                  session.status === 'COMPLETED' ? 'bg-dot-completed/20 text-dot-completed' :
                  session.status === 'FAILED' ? 'bg-dot-flagged/20 text-dot-flagged' :
                  'bg-surface-750 text-text-muted'
                }`}>
                  {session.status}
                </span>
              </dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-text-muted text-xs">Buyer</dt>
              <dd class="text-text-primary">{session.buyer_agent_id}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-text-muted text-xs">Seller</dt>
              <dd class="text-text-primary">{session.seller_agent_id}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-text-muted text-xs">Messages</dt>
              <dd class="font-mono text-text-primary">{session.message_count}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-text-muted text-xs">Created</dt>
              <dd class="text-text-primary">{new Date(session.created_at).toLocaleString()}</dd>
            </div>
          </dl>
        </div>

        {/* Violations */}
        {trust && trust.violations.length > 0 && (
          <div class="rounded-card border border-border bg-surface-800 px-card py-card">
            <h3 class="mb-3 text-xs font-semibold text-text-primary tracking-wide">Violations</h3>
            <div class="space-y-2">
              {trust.violations.map((v, i) => (
                <div key={i} class={`rounded-card border-l-4 bg-surface-750 px-3 py-2.5 ${severityClass(v.severity)}`}>
                  <p class="text-[11px] font-medium text-text-muted">{v.violation_type}</p>
                  <p class="mt-0.5 text-sm text-text-primary">{v.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {trust && trust.violations.length === 0 && (
          <div class="rounded-card border border-border bg-surface-800 px-card py-card text-center">
            <p class="text-xs text-text-secondary">No violations detected</p>
          </div>
        )}
      </div>
    </div>
  );
}
