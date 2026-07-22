import { c as createComponent } from "./astro-component_CBpBdRmF.mjs";
import "piccolore";
import { I as renderTemplate, u as maybeRenderHead } from "./sequence_DVNL_MTV.mjs";
import { r as renderComponent } from "./entrypoint_DiKPQF1W.mjs";
import { $ as $$Layout } from "./Layout_CxVI5k03.mjs";
import { jsx, jsxs } from "react/jsx-runtime";
import { useState, useEffect } from "react";
import { u as useAuth, g as getAverageTrust, a as getSessionsPerOrg, b as getTacticsFrequency } from "./api_BrLtL2v5.mjs";
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, BarChart, XAxis, YAxis, Bar } from "recharts";
function AdminAnalyticsWidgets() {
  const { getToken, isLoaded } = useAuth();
  const [avgTrust, setAvgTrust] = useState(null);
  const [orgData, setOrgData] = useState([]);
  const [tacticData, setTacticData] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!isLoaded) return;
    let cancelled = false;
    async function loadData() {
      try {
        const token = await getToken() || "mock_token";
        if (!token) ;
        const [trust, orgs, tactics] = await Promise.all([
          getAverageTrust(token),
          getSessionsPerOrg(token),
          getTacticsFrequency(token)
        ]);
        if (!cancelled) {
          setAvgTrust(trust.average_trust_score);
          const cleanOrgs = orgs.map((o) => ({
            ...o,
            org_id: o.org_id === "None" || o.org_id === "unassigned" ? "Unassigned" : o.org_id
          }));
          setOrgData(cleanOrgs.sort((a, b) => b.session_count - a.session_count));
          setTacticData(tactics.sort((a, b) => b.frequency - a.frequency));
          setLoading(false);
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) setLoading(false);
      }
    }
    loadData();
    return () => {
      cancelled = true;
    };
  }, [isLoaded, getToken]);
  if (loading) {
    return /* @__PURE__ */ jsx("div", { className: "flex h-64 items-center justify-center rounded-card border border-border bg-surface-800", children: /* @__PURE__ */ jsx("p", { className: "text-sm text-text-muted animate-pulse", children: "Loading analytics..." }) });
  }
  const PIE_COLORS = ["#d3b773", "#e4e4e7", "#8b8d98", "#3f3f46", "#27272a"];
  return /* @__PURE__ */ jsxs("div", { className: "grid grid-cols-1 md:grid-cols-3 gap-6", children: [
    /* @__PURE__ */ jsxs("div", { className: "rounded-card border border-border bg-surface-800 p-card flex flex-col justify-center items-center text-center h-[320px]", children: [
      /* @__PURE__ */ jsx("h3", { className: "text-sm font-semibold text-text-secondary tracking-wide uppercase mb-6", children: "Global Trust Score" }),
      /* @__PURE__ */ jsxs("div", { className: "relative", children: [
        /* @__PURE__ */ jsxs("svg", { className: "absolute inset-0 h-full w-full -rotate-90 transform", viewBox: "0 0 100 100", children: [
          /* @__PURE__ */ jsx("circle", { cx: "50", cy: "50", r: "45", fill: "none", stroke: "#27272a", strokeWidth: "8" }),
          /* @__PURE__ */ jsx(
            "circle",
            {
              cx: "50",
              cy: "50",
              r: "45",
              fill: "none",
              stroke: "#d3b773",
              strokeWidth: "8",
              strokeDasharray: `${(avgTrust || 0) * 2.83} 283`,
              className: "transition-all duration-1000 ease-out"
            }
          )
        ] }),
        /* @__PURE__ */ jsx("div", { className: "flex h-40 w-40 items-center justify-center rounded-full", children: /* @__PURE__ */ jsx("span", { className: "text-5xl font-bold font-mono text-text-primary", children: avgTrust !== null ? Math.round(avgTrust * 100) : "--" }) })
      ] }),
      /* @__PURE__ */ jsx("p", { className: "mt-6 text-xs text-text-muted", children: "Average across all platform sessions" })
    ] }),
    /* @__PURE__ */ jsxs("div", { className: "rounded-card border border-border bg-surface-800 p-card h-[320px] flex flex-col", children: [
      /* @__PURE__ */ jsx("h3", { className: "text-sm font-semibold text-text-primary tracking-wide mb-2", children: "Sessions by Organization" }),
      /* @__PURE__ */ jsx("div", { className: "flex-1 w-full min-h-0", children: /* @__PURE__ */ jsx(ResponsiveContainer, { width: "100%", height: "100%", children: /* @__PURE__ */ jsxs(PieChart, { children: [
        /* @__PURE__ */ jsx(
          Pie,
          {
            data: orgData,
            dataKey: "session_count",
            nameKey: "org_id",
            cx: "50%",
            cy: "50%",
            innerRadius: 60,
            outerRadius: 80,
            stroke: "none",
            children: orgData.map((entry, index) => /* @__PURE__ */ jsx(Cell, { fill: PIE_COLORS[index % PIE_COLORS.length] }, `cell-${index}`))
          }
        ),
        /* @__PURE__ */ jsx(
          Tooltip,
          {
            contentStyle: { backgroundColor: "#18181b", borderColor: "#27272a", borderRadius: "8px", fontSize: "12px", color: "#e4e4e7" },
            itemStyle: { color: "#d3b773", fontWeight: 600 }
          }
        )
      ] }) }) })
    ] }),
    /* @__PURE__ */ jsxs("div", { className: "rounded-card border border-border bg-surface-800 p-card h-[320px] flex flex-col", children: [
      /* @__PURE__ */ jsx("h3", { className: "text-sm font-semibold text-text-primary tracking-wide mb-4", children: "Tactic Frequency" }),
      /* @__PURE__ */ jsx("div", { className: "flex-1 w-full min-h-0 text-xs", children: /* @__PURE__ */ jsx(ResponsiveContainer, { width: "100%", height: "100%", children: /* @__PURE__ */ jsxs(BarChart, { data: tacticData, layout: "vertical", margin: { top: 0, right: 20, left: 0, bottom: 0 }, children: [
        /* @__PURE__ */ jsx(XAxis, { type: "number", hide: true }),
        /* @__PURE__ */ jsx(
          YAxis,
          {
            dataKey: "tactic_name",
            type: "category",
            axisLine: false,
            tickLine: false,
            tick: { fill: "#8b8d98", fontSize: 11 },
            width: 100
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
        /* @__PURE__ */ jsx(Bar, { dataKey: "frequency", radius: [0, 4, 4, 0], barSize: 20, children: tacticData.map((entry, index) => /* @__PURE__ */ jsx(Cell, { fill: index === 0 ? "#d3b773" : "#3f3f46" }, `cell-${index}`)) })
      ] }) }) })
    ] })
  ] });
}
const $$Analytics = createComponent(($$result, $$props, $$slots) => {
  return renderTemplate`${renderComponent($$result, "Layout", $$Layout, { "title": "Analytics Dashboard" }, { "default": ($$result2) => renderTemplate` ${maybeRenderHead()}<main class="mx-auto max-w-5xl px-6 py-page"> <header class="mb-6 flex items-center justify-between"> <div> <h1 class="text-xl font-semibold tracking-tight text-text-primary">Analytics Insights</h1> <p class="mt-1 text-xs text-text-secondary">Platform-wide metrics and tactical trends</p> </div> <a href="/admin" class="text-sm font-medium text-gold hover:text-gold-hover transition-colors">
&larr; Back to Admin
</a> </header> <section class="mb-6"> ${renderComponent($$result2, "AdminAnalyticsWidgets", AdminAnalyticsWidgets, { "client:load": true, "client:component-hydration": "load", "client:component-path": "D:/TrustMesh/TrustMesh/web-astro/src/components/AdminAnalyticsWidgets", "client:component-export": "default" })} </section> </main> ` })}`;
}, "D:/TrustMesh/TrustMesh/web-astro/src/pages/admin/analytics.astro", void 0);
const $$file = "D:/TrustMesh/TrustMesh/web-astro/src/pages/admin/analytics.astro";
const $$url = "/admin/analytics";
const _page = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: $$Analytics,
  file: $$file,
  url: $$url
}, Symbol.toStringTag, { value: "Module" }));
const page = () => _page;
export {
  page
};
