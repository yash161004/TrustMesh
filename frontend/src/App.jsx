import { useState, useEffect } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

// ── Placeholder chart data (Phase 0 scaffold) ────────────────────────────────
const mockNegotiationData = [
  { turn: 1, offer: 220, counter: null,  trust: 95 },
  { turn: 2, offer: 220, counter: 195,   trust: 88 },
  { turn: 3, offer: 210, counter: 195,   trust: 91 },
  { turn: 4, offer: 210, counter: 200,   trust: 85 },
  { turn: 5, offer: 205, counter: 200,   trust: 92 },
  { turn: 6, offer: 202, counter: 202,   trust: 98 },
];

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
    { num: 2, name: "Trust Engine",           status: "pending", desc: "Manipulation & policy violation detection" },
    { num: 3, name: "Cryptographic Ledger",   status: "pending", desc: "Ed25519 signing, tamper-evident chain" },
    { num: 4, name: "WebSocket Live Stream",  status: "pending", desc: "Real-time dashboard feed" },
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

function NegotiationChart() {
  return (
    <div id="negotiation-chart" className="glass rounded-2xl p-6 border-glow">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-lg font-semibold text-white/90">Price Negotiation (Demo)</h2>
        <span className="badge-pending">Placeholder — Phase 1</span>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={mockNegotiationData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
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

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [apiStatus, setApiStatus] = useState("checking");
  const [apiData,   setApiData]   = useState(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/v1/health")
      .then((r) => r.json())
      .then((d) => { setApiData(d); setApiStatus("ok"); })
      .catch(() => setApiStatus("error"));
  }, []);

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
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-trust-500 hover:bg-trust-600 text-white text-sm font-semibold transition-all duration-200 shadow-glow-blue hover:shadow-glow-blue hover:scale-[1.03]"
            >
              View API Docs →
            </a>
            <a
              id="btn-health"
              href="http://localhost:8000/api/v1/health"
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
          <StatCard id="stat-trust"    label="Trust Engine"  value="Phase 2"     sub="Coming soon"         color="amber"  delay={240} />
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
            <NegotiationChart />
          </div>
          <div>
            <PhaseRoadmap />
          </div>
        </div>
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
