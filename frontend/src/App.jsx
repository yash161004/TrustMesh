import { useState, useEffect, useRef, useCallback } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

// (Mock data removed for Phase A)

// ── Sub-components ────────────────────────────────────────────────────────────

function ShieldIcon({ className = "" }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      strokeWidth={1.5}
      stroke="currentColor"
      className={className}
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z"
      />
    </svg>
  );
}

function StatCard({ id, label, value, sub, color = "blue", delay = 0 }) {
  const colorMap = {
    blue:   "text-neon-blue  shadow-glow-blue",
    green:  "text-neon-green shadow-glow-green",
    purple: "text-neon-purple shadow-glow-purple",
    amber:  "text-amber-400",
  };
  return (
    <div
      id={id}
      className="glass card-hover rounded-2xl p-6 border-glow animate-slide-up"
      style={{ animationDelay: `${delay}ms`, animationFillMode: "both" }}
    >
      <p className="text-sm text-white/50 font-medium uppercase tracking-widest mb-2">{label}</p>
      <p className={`text-3xl font-bold mb-1 ${colorMap[color]}`}>{value}</p>
      {sub && <p className="text-xs text-white/35">{sub}</p>}
    </div>
  );
}

function PhaseRoadmap() {
  const phases = [
    { num: 0, name: "Foundation",            status: "done",  desc: "Project scaffolding, models, health-check" },
    { num: 1, name: "Agent Logic",            status: "active", desc: "Buyer & Seller LLM agents (Gemini / Groq)" },
    { num: 2, name: "Trust Engine",           status: "active", desc: "Manipulation & policy violation detection" },
    { num: 3, name: "Cryptographic Ledger",   status: "active", desc: "Ed25519 signing, tamper-evident chain" },
    { num: 4, name: "WebSocket Live Stream",  status: "active", desc: "Real-time dashboard feed" },
    { num: 5, name: "Advanced Analysis",      status: "pending", desc: "Scoring, reports, export" },
  ];

  return (
    <div id="phase-roadmap" className="glass rounded-2xl p-6 border-glow">
      <h2 className="text-lg font-semibold text-white/90 mb-5">Phase Roadmap</h2>
      <ol className="relative border-l border-white/10 ml-3 space-y-6">
        {phases.map((p) => (
          <li key={p.num} className="ml-6">
            <span
              className={`absolute -left-3 flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ring-4 ring-[hsl(240,70%,6%)] $            {p.status === "active"
                  ? "bg-trust-500 text-white"
                  : p.status === "done"
                  ? "bg-emerald-500/80 text-white"
                  : "bg-white/10 text-white/40"
              }`}
            >
              {p.num}
            </span>
            <div className="flex items-center gap-2 mb-0.5">
              <h3 className={`text-sm font-semibold ${p.status === "active" ? "text-trust-300" : "text-white/60"}`}>
                {p.name}
              </h3>
              {p.status === "active" && <span className="badge-active">Current</span>}
              {p.status === "done" && <span className="text-emerald-400 text-xs font-medium">✓ Done</span>}
            </div>
            <p className="text-xs text-white/35">{p.desc}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}

function NegotiationChart({ data }) {
  return (
    <div id="negotiation-chart" className="glass rounded-2xl p-6 border-glow">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-lg font-semibold text-white/90">Price Negotiation (Real-time)</h2>
        <span className="badge-active">Live Data</span>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data || []} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="offerGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#3b5bff" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#3b5bff" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="counterGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#00ff88" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#00ff88" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis dataKey="turn" tick={{ fill: "rgba(255,255,255,0.35)", fontSize: 11 }} label={{ value: "Turn", position: "insideBottom", offset: -2, fill: "rgba(255,255,255,0.3)", fontSize: 11 }} />
          <YAxis tick={{ fill: "rgba(255,255,255,0.35)", fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: "hsl(240,40%,10%)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#fff" }}
            labelStyle={{ color: "rgba(255,255,255,0.6)" }}
          />
          <Area type="monotone" dataKey="offer"   stroke="#3b5bff" fill="url(#offerGrad)"   strokeWidth={2} name="Buyer Offer ($)" dot={{ fill: "#3b5bff", r: 3 }} />
          <Area type="monotone" dataKey="counter" stroke="#00ff88" fill="url(#counterGrad)" strokeWidth={2} name="Seller Counter ($)" dot={{ fill: "#00ff88", r: 3 }} connectNulls />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function HealthBadge({ status }) {
  if (status === "checking") {
    return <span className="badge-pending animate-pulse-slow">Checking…</span>;
  }
  if (status === "ok") {
    return <span className="badge-active">API ✓ Connected</span>;
  }
  return <span className="badge-failed">API ✗ Offline</span>;
}

// ── Trust Engine components (Phase 2 UI) ──────────────────────────────────────

const SEVERITY_STYLES = {
  LOW:      "bg-white/8 text-white/50 border-white/10",
  MEDIUM:   "bg-amber-500/12 text-amber-400 border-amber-500/20",
  HIGH:     "bg-orange-500/12 text-orange-400 border-orange-500/20",
  CRITICAL: "bg-red-500/12 text-red-400 border-red-500/20",
};

const TREND_ICONS = { improving: "↗", declining: "↘", stable: "→" };
const TREND_COLORS = { improving: "text-emerald-400", declining: "text-red-400", stable: "text-white/40" };

function TrustScoreGauge({ label, score, trend, agentId, reputationScore, sessionCount }) {
  const pct = score != null ? Math.round(score) : null;
  const color =
    pct == null ? "bg-white/10" :
    pct >= 80 ? "bg-emerald-500" :
    pct >= 50 ? "bg-amber-500" : "bg-red-500";

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-white/50 uppercase tracking-wider">{label}</span>
        {trend && (
          <span className={`text-xs font-mono ${TREND_COLORS[trend] || "text-white/40"}`}>
            {TREND_ICONS[trend] || "→"} {trend}
          </span>
        )}
      </div>
      <div className="flex items-center gap-3">
        <div className="flex-1 h-2 rounded-full bg-white/5 overflow-hidden">
          {pct != null ? (
            <div className={`h-full rounded-full ${color} transition-all duration-700`} style={{ width: `${pct}%` }} />
          ) : (
            <div className="h-full rounded-full bg-white/5 shimmer" />
          )}
        </div>
        <span className={`text-sm font-bold tabular-nums ${pct != null ? "text-white/80" : "text-white/30"}`}>
          {pct != null ? `${pct}/100` : "—"}
        </span>
      </div>
      {agentId && (
        <div className="flex items-center justify-between mt-1">
          <span className="text-[10px] text-white/25 font-mono truncate">{agentId}</span>
          {reputationScore != null && (
            <span className="text-[10px] text-white/40">
              Reputation: <span className="font-bold text-white/60">{Math.round(reputationScore)}</span> ({sessionCount} sessions)
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function TrustScorePanel({ trustData, loading, session, identities }) {
  if (loading && !trustData) {
    return (
      <div className="glass rounded-2xl p-5 border-glow h-full flex flex-col items-center justify-center gap-3 min-h-[160px]">
        <div className="h-5 w-5 border-2 border-trust-400 border-t-transparent rounded-full animate-spin" />
        <span className="text-xs text-white/40">Evaluating trust…</span>
      </div>
    );
  }

  if (!trustData) {
    return (
      <div className="glass rounded-2xl p-5 border-glow h-full flex flex-col items-center justify-center gap-2 min-h-[160px]">
        <span className="text-2xl opacity-40">🛡️</span>
        <span className="text-xs text-white/35">Trust scores pending — run a negotiation to evaluate</span>
      </div>
    );
  }

  const buyer = trustData.buyer_score;
  const seller = trustData.seller_score;

  const buyerIdentity = session?.buyer_identity_id ? identities[session.buyer_identity_id] : null;
  const sellerIdentity = session?.seller_identity_id ? identities[session.seller_identity_id] : null;

  return (
    <div className="glass rounded-2xl p-5 border-glow">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white/90">Trust Scores</h2>
        <span className="badge-active">Evaluated</span>
      </div>
      <div className="space-y-4">
        <TrustScoreGauge 
          label="Buyer" 
          score={buyer?.overall_score} 
          trend={buyer?.recent_trend} 
          agentId={buyer?.agent_id} 
          reputationScore={buyerIdentity?.reputation_score}
          sessionCount={buyerIdentity?.session_count}
        />
        <TrustScoreGauge 
          label="Seller" 
          score={seller?.overall_score} 
          trend={seller?.recent_trend} 
          agentId={seller?.agent_id} 
          reputationScore={sellerIdentity?.reputation_score}
          sessionCount={sellerIdentity?.session_count}
        />
      </div>
      {trustData.summary && (
        <p className="mt-3 text-xs text-white/35 leading-relaxed border-t border-white/5 pt-3">{trustData.summary}</p>
      )}
    </div>
  );
}

function ViolationRow({ v }) {
  const sev = SEVERITY_STYLES[v.severity] || SEVERITY_STYLES.LOW;
  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-white/5 last:border-0">
      <span className={`shrink-0 mt-0.5 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${sev}`}>
        {v.severity}
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-xs font-semibold text-white/70">{v.violation_type.replace(/_/g, " ")}</span>
          <span className="text-[10px] text-white/25 font-mono">turn {v.message_turn}</span>
          {v.status === "DISPUTED" && (
            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-widest bg-amber-500/20 text-amber-500 border border-amber-500/40 ml-1">
              DISPUTED
            </span>
          )}
        </div>
        <p className="text-xs text-white/40 leading-relaxed">{v.description}</p>
        {v.agent_id && <span className="text-[10px] text-white/20 font-mono mt-0.5 block">{v.agent_id}</span>}
      </div>
    </div>
  );
}

function ViolationsList({ violations, loading }) {
  if (loading && (!violations || violations.length === 0)) {
    return (
      <div className="glass rounded-2xl p-5 border-glow h-full flex flex-col items-center justify-center gap-3 min-h-[160px]">
        <div className="h-5 w-5 border-2 border-trust-400 border-t-transparent rounded-full animate-spin" />
        <span className="text-xs text-white/40">Scanning for violations…</span>
      </div>
    );
  }

  if (!violations || violations.length === 0) {
    return (
      <div className="glass rounded-2xl p-5 border-glow h-full">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white/90">Violations</h2>
          <span className="badge-pending">Pending</span>
        </div>
        <div className="flex flex-col items-center justify-center py-8 gap-2">
          <span className="text-2xl opacity-40">✓</span>
          <span className="text-xs text-white/35">No violations detected — or detectors not yet implemented</span>
        </div>
      </div>
    );
  }

  return (
    <div className="glass rounded-2xl p-5 border-glow h-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white/90">Violations</h2>
        <div className="flex items-center gap-2">
          {violations.some(v => v.status === "DISPUTED") && (
            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/15 text-amber-500 border border-amber-500/25">
              {violations.filter(v => v.status === "DISPUTED").length} disputed
            </span>
          )}
          <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-500/15 text-red-400 border border-red-500/25">
            {violations.filter(v => v.status !== "DISPUTED").length} flagged
          </span>
        </div>
      </div>
      <div className="max-h-[320px] overflow-y-auto pr-1 -mr-1">
        {violations.map((v, i) => (
          <ViolationRow key={i} v={v} />
        ))}
      </div>
    </div>
  );
}

// ── Cryptographic Ledger components (Phase 3 UI) ──────────────────────────────

function truncateHash(h, len = 10) {
  if (!h) return "—";
  return h.length > len ? h.slice(0, len) + "…" : h;
}

function LedgerEntryRow({ entry, isBroken, isLast }) {
  let sender = "unknown";
  try {
    const msg = JSON.parse(entry.message_json);
    sender = msg.sender || "unknown";
  } catch { /* keep default */ }

  const role = sender.includes("buyer") ? "buyer" : sender.includes("seller") ? "seller" : "unknown";
  const roleColor = role === "buyer" ? "text-neon-blue" : role === "seller" ? "text-neon-green" : "text-white/40";

  return (
    <div className={`flex items-center gap-3 py-2.5 px-3 rounded-lg transition-colors ${
      isBroken
        ? "bg-red-500/10 border border-red-500/30"
        : "hover:bg-white/[0.02]"
    } ${!isLast ? "border-b border-white/5" : ""}`}>
      {/* Sequence / turn number */}
      <span className={`shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${
        isBroken ? "bg-red-500/20 text-red-400" : "bg-trust-500/15 text-trust-300"
      }`}>
        {entry.sequence}
      </span>

      {/* Sender */}
      <span className={`shrink-0 text-xs font-medium ${roleColor}`}>
        {sender}
      </span>

      {/* Hash */}
      <div className="flex-1 min-w-0 flex items-center gap-1.5">
        <span className="text-[10px] text-white/25 uppercase tracking-wider shrink-0">hash</span>
        <code className="text-[11px] font-mono text-white/45 truncate">{truncateHash(entry.entry_hash)}</code>
      </div>

      {/* Signature */}
      <div className="shrink-0 flex items-center gap-1.5">
        <span className="text-[10px] text-white/25 uppercase tracking-wider shrink-0">sig</span>
        <code className="text-[11px] font-mono text-white/35 truncate max-w-[100px]">{truncateHash(entry.signature, 12)}</code>
      </div>

      {/* Broken indicator */}
      {isBroken && (
        <span className="shrink-0 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-red-500/20 text-red-400 border border-red-500/30">
          broken
        </span>
      )}
    </div>
  );
}

function LedgerPanel({ ledgerData, loading }) {
  if (loading && !ledgerData) {
    return (
      <div className="glass rounded-2xl p-5 border-glow h-full flex flex-col items-center justify-center gap-3 min-h-[200px]">
        <div className="h-5 w-5 border-2 border-trust-400 border-t-transparent rounded-full animate-spin" />
        <span className="text-xs text-white/40">Loading ledger…</span>
      </div>
    );
  }

  if (!ledgerData) {
    return (
      <div className="glass rounded-2xl p-5 border-glow h-full flex flex-col items-center justify-center gap-2 min-h-[200px]">
        <span className="text-2xl opacity-40">🔐</span>
        <span className="text-xs text-white/35">Ledger pending — run a negotiation to generate entries</span>
      </div>
    );
  }

  const { entries, chain_valid, broken_at } = ledgerData;
  const brokenSeq = chain_valid ? null : broken_at;

  return (
    <div className="glass rounded-2xl p-5 border-glow">
      {/* Header with chain status */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white/90">Cryptographic Ledger</h2>
        {chain_valid ? (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/25">
            <svg viewBox="0 0 16 16" fill="currentColor" className="w-3.5 h-3.5" aria-hidden="true">
              <path fillRule="evenodd" d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z" clipRule="evenodd" />
            </svg>
            Chain Verified
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-red-500/15 text-red-400 border border-red-500/30 animate-pulse">
            <svg viewBox="0 0 16 16" fill="currentColor" className="w-3.5 h-3.5" aria-hidden="true">
              <path fillRule="evenodd" d="M8 15A7 7 0 1 0 8 1a7 7 0 0 0 0 14ZM8 4a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 8 4Zm0 8a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z" clipRule="evenodd" />
            </svg>
            Chain Broken
          </span>
        )}
      </div>

      {/* Broken chain alert */}
      {!chain_valid && broken_at != null && (
        <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/25">
          <div className="flex items-center gap-2 mb-1">
            <svg viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4 text-red-400 shrink-0" aria-hidden="true">
              <path fillRule="evenodd" d="M8 15A7 7 0 1 0 8 1a7 7 0 0 0 0 14ZM8 4a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 8 4Zm0 8a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z" clipRule="evenodd" />
            </svg>
            <span className="text-xs font-bold text-red-400 uppercase tracking-wider">Tamper Detected</span>
          </div>
          <p className="text-xs text-red-300/70">
            Entry #{broken_at} has been modified or reordered — hash mismatch with previous entry in chain.
          </p>
        </div>
      )}

      {/* Entry count */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs text-white/30">{entries.length} entries</span>
        <div className="flex-1 h-px bg-white/5" />
      </div>

      {/* Entry list */}
      {entries.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 gap-2">
          <span className="text-xs text-white/30">No ledger entries yet</span>
        </div>
      ) : (
        <div className="max-h-[360px] overflow-y-auto pr-1 -mr-1">
          {entries.map((entry, i) => (
            <LedgerEntryRow
              key={entry.id}
              entry={entry}
              isBroken={brokenSeq != null && entry.sequence === brokenSeq}
              isLast={i === entries.length - 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [apiStatus, setApiStatus] = useState("checking");
  const [apiData,   setApiData]   = useState(null);
  const [sessions, setSessions] = useState([]);
  const [identities, setIdentities] = useState({});
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [trustData, setTrustData] = useState(null);
  const [trustLoading, setTrustLoading] = useState(false);
  const [ledgerData, setLedgerData] = useState(null);
  const [ledgerLoading, setLedgerLoading] = useState(false);
  const wsRef = useRef(null);
  const chartDataRef = useRef([]);
  const trustTimerRef = useRef(null);
  const ledgerTimerRef = useRef(null);

  // Helper: messages → chart data (shared by WS and REST)
  const messagesToChartData = useCallback((messages) => {
    const turns = {};
    messages.forEach(msg => {
      if (!turns[msg.turn_number]) turns[msg.turn_number] = {};
      if (msg.sender.includes("buyer")) turns[msg.turn_number].offer = msg.price;
      if (msg.sender.includes("seller")) turns[msg.turn_number].counter = msg.price;
    });
    const formatted = [];
    let currentOffer = null;
    let currentCounter = null;
    Object.keys(turns).sort((a, b) => Number(a) - Number(b)).forEach(tNum => {
      if (turns[tNum].offer !== undefined) currentOffer = turns[tNum].offer;
      if (turns[tNum].counter !== undefined) currentCounter = turns[tNum].counter;
      formatted.push({ turn: Number(tNum), offer: currentOffer, counter: currentCounter });
    });
    return formatted;
  }, []);

  // Helper: apply a single new message to existing chart data
  const applyNewMessage = useCallback((msg) => {
    const data = [...chartDataRef.current];
    const existing = data.find(d => d.turn === msg.turn_number);
    if (existing) {
      if (msg.sender.includes("buyer")) existing.offer = msg.price;
      if (msg.sender.includes("seller")) existing.counter = msg.price;
    } else {
      const point = { turn: msg.turn_number, offer: null, counter: null };
      if (msg.sender.includes("buyer")) point.offer = msg.price;
      if (msg.sender.includes("seller")) point.counter = msg.price;
      data.push(point);
    }
    chartDataRef.current = data;
    setChartData([...data]);
  }, []);

  // Helper: fetch trust data for a session (debounced when triggered by WS)
  const fetchTrust = useCallback((sessionId, debounce = false) => {
    if (debounce) {
      if (trustTimerRef.current) clearTimeout(trustTimerRef.current);
      trustTimerRef.current = setTimeout(() => {
        fetchTrust(sessionId, false);
      }, 800);
      return;
    }
    if (!sessionId) return;
    setTrustLoading(true);
    const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    fetch(`${apiBase}/api/v1/sessions/${sessionId}/trust`)
      .then(r => {
        if (!r.ok) throw new Error(r.status);
        return r.json();
      })
      .then(data => { setTrustData(data); setTrustLoading(false); })
      .catch(() => { setTrustData(null); setTrustLoading(false); });
  }, []);

  // Helper: fetch ledger data for a session (debounced when triggered by WS)
  const fetchLedger = useCallback((sessionId, debounce = false) => {
    if (debounce) {
      if (ledgerTimerRef.current) clearTimeout(ledgerTimerRef.current);
      ledgerTimerRef.current = setTimeout(() => {
        fetchLedger(sessionId, false);
      }, 800);
      return;
    }
    if (!sessionId) return;
    setLedgerLoading(true);
    const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    fetch(`${apiBase}/api/v1/sessions/${sessionId}/ledger`)
      .then(r => {
        if (!r.ok) throw new Error(r.status);
        return r.json();
      })
      .then(data => { setLedgerData(data); setLedgerLoading(false); })
      .catch(() => { setLedgerData(null); setLedgerLoading(false); });
  }, []);

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/health`)
      .then((r) => r.json())
      .then((d) => { setApiData(d); setApiStatus("ok"); })
      .catch(() => setApiStatus("error"));
      
    fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/sessions`)
      .then(r => r.json())
      .then(data => {
        setSessions(data);
        if (data.length > 0) {
          setSelectedSessionId(data[0].session_id);
        }
      })
      .catch(e => console.error("Failed to fetch sessions", e));

    // Fetch identities
    fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/identities`)
      .then(r => r.json())
      .then(data => {
        const idMap = {};
        data.forEach(id => idMap[id.id] = id);
        setIdentities(idMap);
      })
      .catch(e => console.error("Failed to fetch identities", e));
  }, []);

  // WebSocket connection with REST fallback (Phase 4)
  useEffect(() => {
    if (!selectedSessionId) return;

    // Clean up previous WS
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const wsUrl = apiBase.replace(/^http/, "ws") + `/api/v1/sessions/${selectedSessionId}/ws`;

    let wsFailed = false;

    const connectWs = () => {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("[WS] Connected to session", selectedSessionId);
        fetchTrust(selectedSessionId, false);
        fetchLedger(selectedSessionId, false);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "history") {
            chartDataRef.current = messagesToChartData(data.messages);
            setChartData([...chartDataRef.current]);
          } else if (data.type === "new_message") {
            applyNewMessage(data.message);
            fetchTrust(selectedSessionId, true);
            fetchLedger(selectedSessionId, true);
          }
        } catch (e) {
          console.error("[WS] Failed to parse message:", e);
        }
      };

      ws.onerror = () => {
        console.warn("[WS] Connection failed — falling back to REST");
        wsFailed = true;
        ws.close();
      };

      ws.onclose = () => {
        if (wsFailed && wsRef.current === ws) {
          // Fall back to REST fetch
          fetch(`${apiBase}/api/v1/sessions/${selectedSessionId}/messages`)
            .then(r => r.json())
            .then(messages => {
              chartDataRef.current = messagesToChartData(messages);
              setChartData([...chartDataRef.current]);
            })
            .catch(e => console.error("REST fallback failed:", e));
          fetchTrust(selectedSessionId, false);
          fetchLedger(selectedSessionId, false);
        }
        wsRef.current = null;
      };
    };

    connectWs();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      if (trustTimerRef.current) {
        clearTimeout(trustTimerRef.current);
        trustTimerRef.current = null;
      }
      if (ledgerTimerRef.current) {
        clearTimeout(ledgerTimerRef.current);
        ledgerTimerRef.current = null;
      }
      setTrustData(null);
      setLedgerData(null);
    };
  }, [selectedSessionId, messagesToChartData, applyNewMessage]);

  return (
    <div className="min-h-dvh bg-hero-gradient">
      {/* ── Ambient glow blobs ── */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden="true">
        <div className="absolute -top-32 left-1/4 w-[600px] h-[600px] rounded-full bg-trust-600/10 blur-[120px]" />
        <div className="absolute top-1/2 -right-32 w-[400px] h-[400px] rounded-full bg-neon-green/5 blur-[100px]" />
        <div className="absolute bottom-0 left-0 w-[300px] h-[300px] rounded-full bg-neon-purple/5 blur-[80px]" />
      </div>

      {/* ── Nav ── */}
      <header id="main-header" className="relative z-10 glass border-b border-white/5">
        <nav className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ShieldIcon className="h-7 w-7 text-trust-400 animate-float" />
            <span className="text-lg font-bold text-white tracking-tight">
              Trust<span className="text-trust-400">Mesh</span>
            </span>
            <span className="badge-phase ml-1">Phase {apiData?.phase?.charAt(0) || '1'}</span>
          </div>
          <HealthBadge status={apiStatus} />
        </nav>
      </header>

      {/* ── Hero ── */}
      <section id="hero" className="relative z-10 max-w-7xl mx-auto px-6 pt-20 pb-12 text-center">
        <div className="animate-fade-in">
          <div className="inline-flex items-center gap-2 glass rounded-full px-4 py-1.5 mb-6 text-xs text-trust-300 font-medium border border-trust-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-trust-400 animate-pulse-slow" />
            Phase 1 Active · AI Agents Negotiating
          </div>
          <h1 className="text-5xl sm:text-6xl font-extrabold text-white leading-tight mb-4">
            AI&nbsp;
            <span className="bg-gradient-to-r from-trust-400 via-neon-blue to-neon-green bg-clip-text text-transparent">
              Negotiation Agents
            </span>
          </h1>
          <p className="text-lg text-white/55 max-w-2xl mx-auto leading-relaxed mb-8">
            Buyer &amp; Seller LLM agents negotiate B2B deals in real time using
            Gemini or Groq — with trust monitoring, commitment verification,
            and cryptographic sealing coming in later phases.
          </p>
          <div className="flex items-center justify-center gap-3 flex-wrap">
            <a
              id="btn-docs"
              href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-trust-500 hover:bg-trust-600 text-white text-sm font-semibold transition-all duration-200 shadow-glow-blue hover:shadow-glow-blue hover:scale-[1.03]"
            >
              View API Docs →
            </a>
            <a
              id="btn-health"
              href={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/health`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl glass border border-white/10 hover:border-trust-500/40 text-white/80 hover:text-white text-sm font-semibold transition-all duration-200"
            >
              Health Check
            </a>
          </div>
        </div>
      </section>

      {/* ── Stats row ── */}
      <section id="stats" className="relative z-10 max-w-7xl mx-auto px-6 mb-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard id="stat-phase"    label="Current Phase" value={apiData?.phase?.charAt(0) || '1'} sub={apiData?.phase?.slice(5) || 'Agent Logic'} color="blue"   delay={0} />
          <StatCard id="stat-agents"   label="LLM Agents"    value="2"           sub="Buyer + Seller"      color="green"  delay={80} />
          <StatCard id="stat-models"   label="AI Backends"   value="2"           sub="Gemini · Groq"       color="purple" delay={160} />
          <StatCard id="stat-trust"    label="Trust Engine"  value={trustData ? `${trustData.violations?.length || 0} flags` : "Pending"} sub={trustData ? "Phase 2 Active" : "Run a negotiation to evaluate"} color="amber"  delay={240} />
        </div>
      </section>

      {/* ── Backend status card ── */}
      {apiData && (
        <section id="backend-status" className="relative z-10 max-w-7xl mx-auto px-6 mb-8">
          <div className="glass rounded-2xl p-5 border-glow flex items-center gap-4 animate-slide-up">
            <div className="flex-shrink-0 h-10 w-10 rounded-xl bg-emerald-500/15 flex items-center justify-center">
              <svg viewBox="0 0 24 24" fill="none" strokeWidth={2} stroke="#00ff88" className="h-5 w-5" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white">{apiData.service} · {apiData.version}</p>
              <p className="text-xs text-white/40 font-mono truncate">
                {apiData.timestamp} · {apiData.phase}
              </p>
            </div>
            <span className="badge-active flex-shrink-0">Live</span>
          </div>
        </section>
      )}

      {/* ── Charts + roadmap grid ── */}
      <section id="main-grid" className="relative z-10 max-w-7xl mx-auto px-6 mb-8">
        <div className="grid md:grid-cols-3 gap-6">
          <div className="md:col-span-2">
            <NegotiationChart data={chartData} />
          </div>
          <div>
            <PhaseRoadmap />
          </div>
        </div>
      </section>

      {/* ── Trust Engine panel ── */}
      <section id="trust-panel" className="relative z-10 max-w-7xl mx-auto px-6 mb-8">
        <div className="grid md:grid-cols-2 gap-6">
          <TrustScorePanel 
            trustData={trustData} 
            loading={trustLoading} 
            session={sessions.find(s => s.session_id === selectedSessionId)}
            identities={identities}
          />
          <ViolationsList violations={trustData?.violations} loading={trustLoading} />
        </div>
      </section>

      {/* ── Cryptographic Ledger panel ── */}
      <section id="ledger-panel" className="relative z-10 max-w-7xl mx-auto px-6 mb-8">
        <LedgerPanel ledgerData={ledgerData} loading={ledgerLoading} />
      </section>

      {/* ── Architecture callouts ── */}
      <section id="architecture" className="relative z-10 max-w-7xl mx-auto px-6 pb-20">
        <h2 className="text-xl font-bold text-white/80 mb-5">System Architecture</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { id: "arch-trust-engine",   icon: "🛡️", title: "Trust Engine",        desc: "Monitors negotiations for manipulation, broken commitments & policy violations.",  phase: "2" },
            { id: "arch-crypto-ledger",  icon: "🔐", title: "Cryptographic Ledger", desc: "Ed25519-signed, SHA-256 chained tamper-evident record of every message.",          phase: "3" },
            { id: "arch-gemini-agent",   icon: "🤖", title: "Gemini 2.5 Flash",     desc: "Primary LLM powering Buyer & Seller negotiation agents via Google AI Studio.",     phase: "1" },
            { id: "arch-groq-fallback",  icon: "⚡", title: "Groq Fallback",        desc: "Ultra-fast LLM inference as a fallback when Gemini is unavailable.",              phase: "1" },
          ].map((item, i) => (
            <div
              key={item.id}
              id={item.id}
              className="glass card-hover rounded-2xl p-5 border-glow animate-slide-up"
              style={{ animationDelay: `${i * 80}ms`, animationFillMode: "both" }}
            >
              <div className="text-2xl mb-3">{item.icon}</div>
              <h3 className="text-sm font-semibold text-white mb-1">{item.title}</h3>
              <p className="text-xs text-white/40 leading-relaxed mb-3">{item.desc}</p>
              <span className="badge-pending">Phase {item.phase}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── Footer ── */}
      <footer id="footer" className="relative z-10 glass border-t border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-12 flex items-center justify-between text-xs text-white/30">
          <span>TrustMesh © 2026 · Phase 1 — Agent Logic</span>
          <span>FastAPI · React · Gemini · Groq</span>
        </div>
      </footer>
    </div>
  );
}
