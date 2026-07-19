import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuth } from '@clerk/astro/react';
import {
  getSession,
  getSessionMessages,
  getTrustReport,
  getWebSocketUrl,
  getLedger,
  exportSessionPdf,
  type SessionResponse,
  type NegotiationMessage,
  type TrustReport,
  type LedgerResponse,
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

function TrustGauge({ score, label }: { score: number; label: string }) {
  const radius = 36;
  const strokeWidth = 8;
  const circumference = radius * Math.PI; // Half-circle
  const dashoffset = circumference - (score / 100) * circumference;

  // Real threshold check based on typical DB scores:
  let color = 'text-dot-flagged'; // < 50
  if (score >= 75) color = 'text-gold';
  else if (score >= 50) color = 'text-dot-active';

  return (
    <div className="flex flex-col items-center">
      <p className="text-[10px] font-medium uppercase tracking-widest text-text-muted mb-2">{label}</p>
      <div className="relative flex items-end justify-center h-[40px]">
        <svg className="w-[80px] h-[40px]" viewBox="0 0 80 40">
          <path d="M 4 40 A 36 36 0 0 1 76 40" fill="none" stroke="currentColor" className="text-surface-750" strokeWidth={strokeWidth} strokeLinecap="round" />
          <path d="M 4 40 A 36 36 0 0 1 76 40" fill="none" stroke="currentColor" className={`${color} transition-all duration-1000 ease-out`} strokeWidth={strokeWidth} strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={dashoffset} />
        </svg>
        <span className="absolute bottom-0 text-xl font-bold font-mono text-text-primary leading-none">
          {score > 0 ? score.toFixed(0) : '—'}
        </span>
      </div>
    </div>
  );
}

interface Props {
  sessionId?: string;
  clerkBypass?: boolean;
}

export default function SessionView({ sessionId: propSessionId, clerkBypass }: Props = {}) {
  const { getToken, isLoaded } = useAuth();
  const [sessionId] = useState<string | null>(() => propSessionId ?? getSessionIdFromUrl());

  const [session, setSession] = useState<SessionResponse | null>(null);
  const [messages, setMessages] = useState<NegotiationMessage[]>([]);
  const [trust, setTrust] = useState<TrustReport | null>(null);
  const [ledger, setLedger] = useState<LedgerResponse | null>(null);
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
      const token = clerkBypass ? "mock_token" : (await getToken() || "mock_token");
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
  }, [getToken, sessionId, clerkBypass]);

  useEffect(() => {
    unmountedRef.current = false;

    async function load() {
      if (!sessionId) {
        setError('Invalid session URL');
        setLoading(false);
        return;
      }

      try {
        const token = clerkBypass ? "mock_token" : (await getToken() || "mock_token");
        if (!token || unmountedRef.current) return;

        const [sess, msgs, trustReport, ledgerReport] = await Promise.all([
          getSession(token, sessionId),
          getSessionMessages(token, sessionId).catch(() => []),
          getTrustReport(token, sessionId).catch(() => null),
          getLedger(token, sessionId).catch(() => null),
        ]);

        if (unmountedRef.current) return;
        setSession(sess);
        sessionRef.current = sess;
        setMessages(msgs);
        setTrust(trustReport);
        setLedger(ledgerReport);
      } catch (err) {
        if (!unmountedRef.current) {
          setError(err instanceof Error ? err.message : 'Failed to load session');
        }
      } finally {
        if (!unmountedRef.current) setLoading(false);
      }
    }

    if (isLoaded || clerkBypass) load();
    return () => { unmountedRef.current = true; };
  }, [isLoaded, getToken, sessionId, clerkBypass]);

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
      <div className="flex items-center justify-center py-20">
        <svg className="h-6 w-6 animate-spin text-text-muted" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <span className="ml-3 text-sm text-text-secondary">Loading session…</span>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="rounded-card border border-dot-flagged/30 bg-dot-flagged/10 px-card py-16 text-center">
        <p className="text-sm text-dot-flagged">{error ?? 'Session not found'}</p>
        <a href="/dashboard" className="mt-4 inline-block text-sm text-text-secondary hover:text-text-primary transition-colors">
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
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
      {/* Transcript */}
      <div className="lg:col-span-2 space-y-4">
        <div className="rounded-card border border-border bg-surface-800 flex flex-col h-[600px]">
          <div className="flex items-center justify-between border-b border-border px-card py-4">
            <div>
              <h1 className="text-sm font-semibold text-text-primary tracking-wide">Transcript</h1>
              <p className="mt-0.5 text-xs text-text-muted font-mono">{session.buyer_agent_id} vs {session.seller_agent_id}</p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={async () => {
                  if (!session?.session_id) return;
                  try {
                    const token = clerkBypass ? "mock_token" : (await getToken() || "mock_token");
                    if (!token) return;
                    const blob = await exportSessionPdf(token, session.session_id);
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `session_${session.session_id}.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    URL.revokeObjectURL(url);
                  } catch (err) {
                    console.error('Failed to download PDF', err);
                  }
                }}
                className="rounded bg-surface-700 px-3 py-1.5 text-[11px] font-medium text-text-primary hover:bg-surface-750 transition-colors border border-border"
              >
                Download Report
              </button>
              {ledger?.chain_valid && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-gold/10 px-2 py-1 text-xs font-medium text-gold border border-gold/20">
                  <svg className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clipRule="evenodd" />
                  </svg>
                  Ledger Verified
                </span>
              )}
              {ledger && !ledger.chain_valid && (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-dot-flagged/10 px-2 py-1 text-xs font-medium text-dot-flagged border border-dot-flagged/20">
                  <span className="h-1.5 w-1.5 rounded-full bg-dot-flagged" />
                  Chain Broken
                </span>
              )}
              <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${wsBadge}`}>
                {wsLabel}
              </span>
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto px-card py-card space-y-6" tabIndex={0}>
            {messages.length === 0 && (
              <p className="text-sm text-text-muted text-center py-8">No messages yet. Start the session to begin negotiation.</p>
            )}
            {messages.map((msg) => {
              // Note: In Phase 1, TrustMesh is a single-tenant simulation platform and sessions
              // do not map specific roles (Buyer/Seller) to distinct external organizations yet. 
              // We currently hardcode Buyer as right-aligned (the "viewing org" perspective) 
              // for demo purposes until full multi-org mapping is added to SessionRecord.
              const isCurrentUser = msg.sender.includes('buyer');
              
              return (
                <div key={msg.turn_number} className={`flex flex-col ${isCurrentUser ? 'items-end' : 'items-start'}`}>
                  <div className="mb-1 text-[11px] font-medium uppercase tracking-widest text-text-muted">
                    {isCurrentUser ? 'Buyer' : 'Seller'} &middot; Turn {msg.turn_number}
                  </div>
                  <div className={`relative max-w-[85%] rounded-2xl px-4 py-3 ${
                    isCurrentUser 
                      ? 'bg-public-brand text-surface-900 rounded-tr-sm shadow-sm' 
                      : 'bg-surface-750 text-text-primary rounded-tl-sm border border-border'
                  }`}>
                    <p className="text-sm leading-relaxed">{messageText(msg)}</p>
                    
                    {/* Metadata Ribbon */}
                    <div className={`mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 border-t pt-2 text-[11px] font-mono ${
                      isCurrentUser ? 'border-surface-900/20 text-surface-900/80' : 'border-border text-text-muted'
                    }`}>
                      <span className="font-semibold">${msg.price}/unit</span>
                      <span className="hidden sm:inline">&middot;</span>
                      <span>Qty: {msg.quantity}</span>
                    </div>

                    {msg.notes && msg.notes !== messageText(msg) && (
                      <div className={`mt-2 rounded p-2.5 text-[11px] italic leading-snug ${
                        isCurrentUser ? 'bg-surface-900/10 text-surface-900/90' : 'bg-surface-800 text-text-secondary'
                      }`}>
                        <span className="font-semibold not-italic block mb-0.5 uppercase tracking-wider text-[9px] opacity-80">Internal Thought</span>
                        {msg.notes}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Sidebar */}
      <div className="space-y-4">
        {/* Trust Gauge */}
        <div className="rounded-card border border-border bg-surface-800 px-card py-6">
          <div className="flex flex-col items-center gap-6 sm:flex-row sm:justify-around">
            <TrustGauge score={trust?.buyer_score?.overall_score ?? 0} label="Buyer Trust" />
            <div className="hidden h-10 w-px bg-border sm:block"></div>
            <TrustGauge score={trust?.seller_score?.overall_score ?? 0} label="Seller Trust" />
          </div>
          {trust?.violations && trust.violations.length > 0 && (
            <div className="mt-6 pt-5 border-t border-border">
              <h3 className="mb-3 text-xs font-semibold text-text-primary tracking-wide">Detected Violations</h3>
              <div className="space-y-2.5">
                {trust.violations.map((v, i) => (
                  <div key={i} className={`rounded border-l-4 bg-surface-750 px-3 py-2.5 shadow-sm ${severityClass(v.severity)}`}>
                    <p className="text-[11px] font-medium text-text-muted">{v.violation_type}</p>
                    <p className="mt-1 text-[13px] text-text-primary leading-snug">{v.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
          {trust && trust.violations.length === 0 && (
            <div className="mt-6 pt-5 border-t border-border text-center">
              <p className="text-xs text-text-secondary">No violations detected</p>
            </div>
          )}
        </div>

        {/* Details */}
        <div className="rounded-card border border-border bg-surface-800 px-card py-card">
          <h3 className="mb-3 text-xs font-semibold text-text-primary tracking-wide">Session Details</h3>
          <dl className="space-y-2.5 text-sm">
            <div className="flex justify-between">
              <dt className="text-text-muted text-xs">ID</dt>
              <dd className="font-mono text-xs text-text-primary">{session.session_id.slice(0, 12)}…</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-text-muted text-xs">Status</dt>
              <dd className="text-text-primary">
                <span className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-medium ${
                  session.status === 'ACTIVE' ? 'bg-dot-active/20 text-dot-active' :
                  session.status === 'COMPLETED' ? 'bg-dot-completed/20 text-dot-completed' :
                  session.status === 'FAILED' ? 'bg-dot-flagged/20 text-dot-flagged' :
                  'bg-surface-750 text-text-muted'
                }`}>
                  {session.status}
                </span>
              </dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-text-muted text-xs">Messages</dt>
              <dd className="font-mono text-text-primary">{session.message_count}</dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-text-muted text-xs">Created</dt>
              <dd className="text-text-primary text-xs">{new Date(session.created_at).toLocaleString()}</dd>
            </div>
          </dl>
        </div>

        {/* Ledger */}
        {ledger && (
          <div className="rounded-card border border-border bg-surface-800 px-card py-card">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-semibold text-text-primary tracking-wide">
                Ledger ({ledger.entries.length} entries)
              </h3>
              <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${
                ledger.chain_valid
                  ? 'bg-gold/10 text-gold border border-gold/20'
                  : 'bg-dot-flagged/10 text-dot-flagged border border-dot-flagged/30'
              }`}>
                {ledger.chain_valid ? 'Verified' : `Broken at entry #${ledger.broken_at ?? '?'}`}
              </span>
            </div>
            <div className="space-y-1 max-h-[260px] overflow-y-auto">
              {ledger.entries.map((e) => {
                const isBroken = ledger.broken_at != null && e.sequence >= ledger.broken_at;
                return (
                  <div key={e.sequence}
                    className={`flex items-center gap-2 rounded px-2 py-1.5 text-[10px] font-mono ${
                      isBroken ? 'bg-dot-flagged/10 border border-dot-flagged/30' : 'hover:bg-surface-750'
                    }`}
                  >
                    <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded text-[8px] font-bold ${
                      isBroken ? 'bg-dot-flagged/20 text-dot-flagged' : 'bg-surface-700 text-text-muted'
                    }`}>
                      {e.sequence}
                    </span>
                    <span className="text-text-muted truncate max-w-[100px]">
                      {JSON.parse(e.message_json).sender?.includes('buyer') ? 'Buyer' : 'Seller'}
                    </span>
                    <span className="text-text-muted/60 truncate flex-1">{e.entry_hash.slice(0, 12)}…</span>
                    {isBroken && (
                      <span className="shrink-0 rounded bg-dot-flagged/15 px-1 py-0.5 text-[8px] font-bold uppercase tracking-wider text-dot-flagged">
                        broken
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
