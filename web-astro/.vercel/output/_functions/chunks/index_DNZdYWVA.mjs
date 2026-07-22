import { c as createComponent } from "./astro-component_CBpBdRmF.mjs";
import "piccolore";
import { I as renderTemplate, u as maybeRenderHead } from "./sequence_DVNL_MTV.mjs";
import { r as renderComponent } from "./entrypoint_DiKPQF1W.mjs";
import { $ as $$Layout } from "./Layout_CxVI5k03.mjs";
import { jsx, jsxs } from "react/jsx-runtime";
import { useState, useEffect } from "react";
import { u as useAuth, b as getTacticsFrequency } from "./api_BrLtL2v5.mjs";
import { ResponsiveContainer, BarChart, XAxis, YAxis, Tooltip, Bar, Cell } from "recharts";
const MOCK_STATS = [
  { label: "Organizations", value: "12", sub: "across 3 tiers" },
  { label: "Active Sessions", value: "24", sub: "14 in last hour" },
  { label: "Violations (today)", value: "7", sub: "3 critical" },
  { label: "Avg Trust Score", value: "71", sub: "+5 vs yesterday" }
];
function AdminStats() {
  return /* @__PURE__ */ jsx("div", { class: "grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4", children: MOCK_STATS.map((s) => /* @__PURE__ */ jsxs("div", { class: "rounded-card border border-border bg-surface-800 px-card py-card", children: [
    /* @__PURE__ */ jsx("p", { class: "text-[10px] font-medium uppercase tracking-widest text-text-muted", children: s.label }),
    /* @__PURE__ */ jsx("p", { class: "mt-1.5 font-mono text-2xl font-bold text-text-primary", children: s.value }),
    /* @__PURE__ */ jsx("p", { class: "mt-0.5 text-xs text-text-secondary", children: s.sub })
  ] }, s.label)) });
}
const SEV_DOT = {
  critical: "bg-dot-flagged",
  high: "bg-dot-flagged",
  medium: "bg-dot-active",
  low: "bg-dot-completed"
};
const MOCK$1 = [
  { id: "v-001", org: "Acme Corp", session: "sess-001", detector: "PolicyDeviationFlagger", type: "Budget Override", severity: "critical", turn: 4, description: "Offer exceeded buyer budget cap of $500 by $120.", timestamp: "2026-07-18T10:32:00Z" },
  { id: "v-002", org: "Beta Supplies", session: "sess-002", detector: "ManipulationDetector", type: "Fabricated Scarcity", severity: "high", turn: 3, description: "Seller claimed competing buyers to pressure acceptance.", timestamp: "2026-07-18T09:18:00Z" },
  { id: "v-003", org: "Gamma Materials", session: "sess-003", detector: "CommitmentConsistencyChecker", type: "Bait & Switch", severity: "medium", turn: 5, description: "Delivery terms changed from 10 to 30 days at acceptance.", timestamp: "2026-07-17T17:02:00Z" },
  { id: "v-004", org: "Delta Parts", session: "sess-004", detector: "ManipulationDetector", type: "Authority Fabrication", severity: "high", turn: 1, description: "Buyer cited non-existent board resolution to cap price.", timestamp: "2026-07-17T14:25:00Z" },
  { id: "v-005", org: "Epsilon Trade", session: "sess-005", detector: "PolicyDeviationFlagger", type: "Quantity Trick", severity: "low", turn: 2, description: "Volume discount requested at 10000 units (100x standard).", timestamp: "2026-07-16T11:05:00Z" }
];
function AdminViolations() {
  return /* @__PURE__ */ jsxs("div", { class: "rounded-card border border-border bg-surface-800 px-card py-card", children: [
    /* @__PURE__ */ jsx("h2", { class: "mb-4 text-sm font-semibold text-text-primary tracking-wide", children: "Recent Violations" }),
    /* @__PURE__ */ jsx("div", { class: "overflow-x-auto", children: /* @__PURE__ */ jsxs("table", { class: "w-full text-left text-sm", children: [
      /* @__PURE__ */ jsx("thead", { children: /* @__PURE__ */ jsxs("tr", { class: "border-b border-border text-[10px] font-medium uppercase tracking-widest text-text-muted", children: [
        /* @__PURE__ */ jsx("th", { class: "pb-2 pr-4", children: "Org" }),
        /* @__PURE__ */ jsx("th", { class: "pb-2 pr-4", children: "Detector" }),
        /* @__PURE__ */ jsx("th", { class: "pb-2 pr-4", children: "Type" }),
        /* @__PURE__ */ jsx("th", { class: "pb-2 pr-4", children: "Sev" }),
        /* @__PURE__ */ jsx("th", { class: "pb-2 pr-4", children: "Description" }),
        /* @__PURE__ */ jsx("th", { class: "pb-2 text-right", children: "Time" })
      ] }) }),
      /* @__PURE__ */ jsx("tbody", { children: MOCK$1.map((v) => /* @__PURE__ */ jsxs("tr", { class: "border-b border-border/50 last:border-0 transition-colors duration-150 hover:bg-surface-750", children: [
        /* @__PURE__ */ jsxs("td", { class: "py-2.5 pr-4", children: [
          /* @__PURE__ */ jsx("span", { class: "text-sm text-text-primary", children: v.org }),
          /* @__PURE__ */ jsx("p", { class: "text-[10px] font-mono text-text-muted", children: v.session })
        ] }),
        /* @__PURE__ */ jsx("td", { class: "py-2.5 pr-4 text-xs text-text-secondary", children: v.detector }),
        /* @__PURE__ */ jsx("td", { class: "py-2.5 pr-4 text-xs text-text-primary", children: v.type }),
        /* @__PURE__ */ jsx("td", { class: "py-2.5 pr-4", children: /* @__PURE__ */ jsxs("span", { class: "flex items-center gap-1.5 text-xs text-text-secondary", children: [
          /* @__PURE__ */ jsx("span", { class: `h-1.5 w-1.5 rounded-full ${SEV_DOT[v.severity]}` }),
          v.severity
        ] }) }),
        /* @__PURE__ */ jsx("td", { class: "py-2.5 pr-4 text-xs text-text-secondary max-w-[240px] truncate", children: v.description }),
        /* @__PURE__ */ jsx("td", { class: "py-2.5 text-right font-mono text-[11px] text-text-muted whitespace-nowrap", children: v.timestamp.slice(11, 16) })
      ] }, v.id)) })
    ] }) })
  ] });
}
function AdminTacticsChart() {
  const { getToken, isLoaded } = useAuth();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!isLoaded) return;
    let cancelled = false;
    async function fetchFreq() {
      try {
        const token = await getToken() || "mock_token";
        if (token) {
          const res = await getTacticsFrequency(token);
          if (!cancelled) setData(res.sort((a, b) => b.frequency - a.frequency));
        }
      } catch (err) {
        console.error(err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchFreq();
    return () => {
      cancelled = true;
    };
  }, [isLoaded, getToken]);
  if (loading) {
    return /* @__PURE__ */ jsx("div", { className: "rounded-card border border-border bg-surface-800 px-card py-card h-[320px] flex items-center justify-center", children: /* @__PURE__ */ jsx("p", { className: "text-sm text-text-muted animate-pulse", children: "Loading tactics data..." }) });
  }
  if (data.length === 0) {
    return /* @__PURE__ */ jsxs("div", { className: "rounded-card border border-border bg-surface-800 px-card py-card h-[320px] flex flex-col items-center justify-center", children: [
      /* @__PURE__ */ jsx("h2", { className: "mb-2 text-sm font-semibold text-text-primary tracking-wide", children: "Tactic Frequency" }),
      /* @__PURE__ */ jsx("p", { className: "text-sm text-text-muted", children: "No manipulation tactics detected yet." })
    ] });
  }
  return /* @__PURE__ */ jsxs("div", { className: "rounded-card border border-border bg-surface-800 px-card py-card h-[320px] flex flex-col", children: [
    /* @__PURE__ */ jsx("h2", { className: "mb-4 text-sm font-semibold text-text-primary tracking-wide", children: "Tactic Frequency" }),
    /* @__PURE__ */ jsx("div", { className: "flex-1 min-h-0 w-full text-xs", children: /* @__PURE__ */ jsx(ResponsiveContainer, { width: "100%", height: "100%", children: /* @__PURE__ */ jsxs(BarChart, { data, layout: "vertical", margin: { top: 0, right: 30, left: 10, bottom: 0 }, children: [
      /* @__PURE__ */ jsx(XAxis, { type: "number", hide: true }),
      /* @__PURE__ */ jsx(
        YAxis,
        {
          dataKey: "tactic_name",
          type: "category",
          axisLine: false,
          tickLine: false,
          tick: { fill: "#8b8d98", fontSize: 11 },
          width: 160
        }
      ),
      /* @__PURE__ */ jsx(
        Tooltip,
        {
          cursor: { fill: "rgba(255,255,255,0.02)" },
          contentStyle: { backgroundColor: "#18181b", borderColor: "#27272a", borderRadius: "8px", fontSize: "12px", color: "#e4e4e7" },
          itemStyle: { color: "#d3b773", fontWeight: 600 },
          labelStyle: { color: "#8b8d98", marginBottom: "4px" }
        }
      ),
      /* @__PURE__ */ jsx(Bar, { dataKey: "frequency", radius: [0, 4, 4, 0], barSize: 24, children: data.map((entry, index) => /* @__PURE__ */ jsx(Cell, { fill: index === 0 ? "#d3b773" : "#3f3f46" }, `cell-${index}`)) })
    ] }) }) })
  ] });
}
const MOCK = [
  { org: "Acme Corp", score: 88, trend: "up", sessions: 6 },
  { org: "Gamma Materials", score: 95, trend: "up", sessions: 4 },
  { org: "Delta Parts", score: 73, trend: "stable", sessions: 3 },
  { org: "Beta Supplies", score: 42, trend: "down", sessions: 5 },
  { org: "Epsilon Trade", score: 31, trend: "down", sessions: 2 },
  { org: "Zeta Industries", score: 67, trend: "stable", sessions: 1 }
];
function scoreColor(s) {
  if (s >= 80) return "text-gold";
  if (s >= 60) return "text-text-primary";
  return "text-text-muted";
}
function barColor(s) {
  if (s >= 80) return "bg-gold";
  if (s >= 60) return "bg-surface-700";
  return "bg-surface-700/50";
}
function trendIcon(t) {
  switch (t) {
    case "up":
      return "↑";
    case "down":
      return "↓";
    default:
      return "→";
  }
}
function trendColor(t) {
  switch (t) {
    case "up":
      return "text-dot-active";
    case "down":
      return "text-dot-flagged";
    default:
      return "text-text-muted";
  }
}
function AdminTrustPanel() {
  return /* @__PURE__ */ jsxs("div", { class: "rounded-card border border-border bg-surface-800 px-card py-card", children: [
    /* @__PURE__ */ jsx("h2", { class: "mb-4 text-sm font-semibold text-text-primary tracking-wide", children: "Trust Scores by Organization" }),
    /* @__PURE__ */ jsx("div", { class: "space-y-3", children: MOCK.map((o) => /* @__PURE__ */ jsxs("div", { class: "flex items-center gap-4", children: [
      /* @__PURE__ */ jsx("div", { class: "w-28 shrink-0", children: /* @__PURE__ */ jsx("p", { class: "text-xs text-text-primary truncate", children: o.org }) }),
      /* @__PURE__ */ jsx("div", { class: "flex-1 h-2 rounded-full bg-surface-700/30 overflow-hidden", children: /* @__PURE__ */ jsx(
        "div",
        {
          class: `h-full rounded-full transition-all duration-500 ${barColor(o.score)}`,
          style: { width: `${o.score}%` }
        }
      ) }),
      /* @__PURE__ */ jsx("div", { class: "w-16 text-right", children: /* @__PURE__ */ jsx("span", { class: `font-mono text-sm font-semibold ${scoreColor(o.score)}`, children: o.score }) }),
      /* @__PURE__ */ jsx("div", { class: `w-6 text-center text-xs font-mono ${trendColor(o.trend)}`, children: trendIcon(o.trend) })
    ] }, o.org)) })
  ] });
}
function truncate(h, n = 10) {
  if (!h) return "—";
  return h.length > n ? h.slice(0, n) + "…" : h;
}
const MOCK_ENTRIES = [
  { seq: 1, sender: "buyer-agent-001", hash: "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0", sig: "sig_a1b2c3d4e5f6a7b8c9d0e1f2a3b" },
  { seq: 2, sender: "seller-agent-001", hash: "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1", sig: "sig_b2c3d4e5f6a7b8c9d0e1f2a3b4c" },
  { seq: 3, sender: "buyer-agent-001", hash: "c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2", sig: "sig_c3d4e5f6a7b8c9d0e1f2a3b4c5d", broken: true },
  { seq: 4, sender: "seller-agent-001", hash: "d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3", sig: "sig_d4e5f6a7b8c9d0e1f2a3b4c5d6e" }
];
function AdminLedger() {
  return /* @__PURE__ */ jsxs("div", { class: "rounded-card border border-border bg-surface-800 px-card py-card", children: [
    /* @__PURE__ */ jsxs("div", { class: "mb-4 flex items-center justify-between", children: [
      /* @__PURE__ */ jsx("h2", { class: "text-sm font-semibold text-text-primary tracking-wide", children: "Cryptographic Ledger" }),
      /* @__PURE__ */ jsxs("span", { class: "inline-flex items-center gap-1.5 rounded-full border border-dot-flagged/30 bg-dot-flagged/10 px-2.5 py-0.5 text-[10px] font-medium text-dot-flagged", children: [
        /* @__PURE__ */ jsx("span", { class: "h-1.5 w-1.5 rounded-full bg-dot-flagged" }),
        "Chain Broken"
      ] })
    ] }),
    /* @__PURE__ */ jsx("div", { class: "space-y-1", children: MOCK_ENTRIES.map((e) => /* @__PURE__ */ jsxs(
      "div",
      {
        class: `grid grid-cols-[auto_1fr_auto] gap-x-2 gap-y-0.5 items-center rounded-card px-3 py-2.5 text-xs transition-colors duration-150 sm:flex sm:flex-wrap sm:items-center sm:gap-3 ${e.broken ? "bg-dot-flagged/10 border border-dot-flagged/30" : "hover:bg-surface-750"} ${!e.broken && e.seq < MOCK_ENTRIES.length ? "border-b border-border/50" : ""}`,
        children: [
          /* @__PURE__ */ jsx("span", { class: `flex h-6 w-6 items-center justify-center rounded-card font-mono text-[10px] font-bold sm:shrink-0 ${e.broken ? "bg-dot-flagged/20 text-dot-flagged" : "bg-surface-700 text-text-secondary"}`, children: e.seq }),
          /* @__PURE__ */ jsx("span", { class: `text-[10px] font-medium sm:shrink-0 ${e.sender.includes("buyer") ? "text-text-secondary" : "text-text-muted"}`, children: e.sender }),
          /* @__PURE__ */ jsxs("span", { class: "col-span-2 row-start-2 font-mono text-[10px] text-text-muted sm:col-auto sm:row-auto sm:shrink-0", children: [
            /* @__PURE__ */ jsx("span", { class: "sm:hidden", children: truncate(e.hash, 20) }),
            /* @__PURE__ */ jsx("span", { class: "hidden sm:inline", children: truncate(e.hash) })
          ] }),
          /* @__PURE__ */ jsx("span", { class: "ml-auto font-mono text-[10px] text-text-muted sm:ml-0", children: truncate(e.sig, 12) }),
          e.broken && /* @__PURE__ */ jsx("span", { class: "col-span-3 mt-0.5 rounded bg-dot-flagged/15 px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wider text-dot-flagged sm:col-auto sm:mt-0", children: "broken" })
        ]
      },
      e.seq
    )) })
  ] });
}
const $$Index = createComponent(($$result, $$props, $$slots) => {
  return renderTemplate`${renderComponent($$result, "Layout", $$Layout, { "title": "Admin Dashboard" }, { "default": ($$result2) => renderTemplate` ${maybeRenderHead()}<main class="mx-auto max-w-5xl px-6 py-page"> <header class="mb-6"> <h1 class="text-xl font-semibold tracking-tight text-text-primary">Admin</h1> <p class="mt-1 text-xs text-text-secondary">Cross-organization oversight</p> </header> <section class="mb-6"> ${renderComponent($$result2, "AdminStats", AdminStats, { "client:load": true, "client:component-hydration": "load", "client:component-path": "D:/TrustMesh/TrustMesh/web-astro/src/components/AdminStats", "client:component-export": "default" })} </section> <div class="grid grid-cols-1 gap-6 lg:grid-cols-3 mb-6"> <div class="lg:col-span-2 space-y-6"> ${renderComponent($$result2, "AdminTacticsChart", AdminTacticsChart, { "client:load": true, "client:component-hydration": "load", "client:component-path": "D:/TrustMesh/TrustMesh/web-astro/src/components/AdminTacticsChart", "client:component-export": "default" })} ${renderComponent($$result2, "AdminViolations", AdminViolations, { "client:load": true, "client:component-hydration": "load", "client:component-path": "D:/TrustMesh/TrustMesh/web-astro/src/components/AdminViolations", "client:component-export": "default" })} </div> <div class="space-y-6"> ${renderComponent($$result2, "AdminTrustPanel", AdminTrustPanel, { "client:load": true, "client:component-hydration": "load", "client:component-path": "D:/TrustMesh/TrustMesh/web-astro/src/components/AdminTrustPanel", "client:component-export": "default" })} ${renderComponent($$result2, "AdminLedger", AdminLedger, { "client:load": true, "client:component-hydration": "load", "client:component-path": "D:/TrustMesh/TrustMesh/web-astro/src/components/AdminLedger", "client:component-export": "default" })} </div> </div> </main> ` })}`;
}, "D:/TrustMesh/TrustMesh/web-astro/src/pages/admin/index.astro", void 0);
const $$file = "D:/TrustMesh/TrustMesh/web-astro/src/pages/admin/index.astro";
const $$url = "/admin";
const _page = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: $$Index,
  file: $$file,
  url: $$url
}, Symbol.toStringTag, { value: "Module" }));
const page = () => _page;
export {
  page
};
