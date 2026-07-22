import { c as createComponent } from "./astro-component_CBpBdRmF.mjs";
import "piccolore";
import { I as renderTemplate, u as maybeRenderHead } from "./sequence_DVNL_MTV.mjs";
import { r as renderComponent } from "./entrypoint_DiKPQF1W.mjs";
import { $ as $$Layout } from "./Layout_CxVI5k03.mjs";
import { jsx, jsxs } from "react/jsx-runtime";
import { useState, useEffect } from "react";
import { u as useAuth, l as listAgentCards } from "./api_BrLtL2v5.mjs";
function AgentDirectory() {
  const { getToken, isLoaded } = useAuth();
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  useEffect(() => {
    async function load() {
      try {
        const token = await getToken() || "mock_token";
        if (!token) ;
        const data = await listAgentCards(token);
        setAgents(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load agent cards");
      } finally {
        setLoading(false);
      }
    }
    if (isLoaded) load();
  }, [isLoaded, getToken]);
  if (loading) {
    return /* @__PURE__ */ jsx("div", { class: "flex items-center justify-center py-20", children: /* @__PURE__ */ jsxs("svg", { class: "h-6 w-6 animate-spin text-text-muted", fill: "none", viewBox: "0 0 24 24", children: [
      /* @__PURE__ */ jsx("circle", { class: "opacity-25", cx: "12", cy: "12", r: "10", stroke: "currentColor", "stroke-width": "4" }),
      /* @__PURE__ */ jsx("path", { class: "opacity-75", fill: "currentColor", d: "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" })
    ] }) });
  }
  if (error) {
    return /* @__PURE__ */ jsx("div", { class: "rounded-card border border-dot-flagged/30 bg-dot-flagged/10 px-card py-16 text-center", children: /* @__PURE__ */ jsx("p", { class: "text-sm text-dot-flagged", children: error }) });
  }
  return /* @__PURE__ */ jsxs("div", { class: "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6", children: [
    agents.map((agent) => /* @__PURE__ */ jsxs("div", { class: "rounded-card border border-border bg-surface-800 flex flex-col h-full overflow-hidden", children: [
      /* @__PURE__ */ jsxs("div", { class: "p-5 border-b border-border/50 bg-surface-800 flex justify-between items-start", children: [
        /* @__PURE__ */ jsxs("div", { children: [
          /* @__PURE__ */ jsx("h3", { class: "text-lg font-semibold text-text-primary tracking-tight", children: agent.display_name }),
          /* @__PURE__ */ jsxs("p", { class: "text-xs text-text-muted mt-1 font-mono uppercase tracking-wider", children: [
            agent.role,
            " AGENT"
          ] })
        ] }),
        agent.is_verified ? /* @__PURE__ */ jsxs("span", { class: "inline-flex items-center gap-1 rounded-full bg-dot-completed/10 px-2 py-1 text-[10px] font-medium text-dot-completed border border-dot-completed/20", children: [
          /* @__PURE__ */ jsx("svg", { class: "w-3 h-3", viewBox: "0 0 20 20", fill: "currentColor", children: /* @__PURE__ */ jsx("path", { fillRule: "evenodd", d: "M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z", clipRule: "evenodd" }) }),
          "VERIFIED"
        ] }) : /* @__PURE__ */ jsxs("span", { class: "inline-flex items-center gap-1 rounded-full bg-dot-flagged/10 px-2 py-1 text-[10px] font-medium text-dot-flagged border border-dot-flagged/20", children: [
          /* @__PURE__ */ jsx("svg", { class: "w-3 h-3", viewBox: "0 0 20 20", fill: "currentColor", children: /* @__PURE__ */ jsx("path", { fillRule: "evenodd", d: "M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z", clipRule: "evenodd" }) }),
          "TAMPERED"
        ] })
      ] }),
      /* @__PURE__ */ jsxs("div", { class: "p-5 flex-grow flex flex-col gap-4 bg-surface-900/30", children: [
        /* @__PURE__ */ jsxs("div", { children: [
          /* @__PURE__ */ jsx("p", { class: "text-xs font-semibold text-text-secondary uppercase tracking-wider mb-2", children: "Capabilities" }),
          /* @__PURE__ */ jsx("div", { class: "flex flex-wrap gap-2", children: agent.capabilities.map((cap) => /* @__PURE__ */ jsx("span", { class: "inline-flex items-center rounded bg-surface-700/50 px-2 py-1 text-[11px] font-medium text-text-primary border border-border/50", children: cap.replace(/_/g, " ") }, cap)) })
        ] }),
        /* @__PURE__ */ jsxs("div", { class: "mt-auto pt-4 border-t border-border/30", children: [
          /* @__PURE__ */ jsx("p", { class: "text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-1", children: "Public Key (Ed25519)" }),
          /* @__PURE__ */ jsx("p", { class: "text-[10px] font-mono text-text-secondary truncate bg-surface-900 p-1.5 rounded border border-border/50", children: agent.public_key })
        ] }),
        /* @__PURE__ */ jsxs("div", { children: [
          /* @__PURE__ */ jsx("p", { class: "text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-1", children: "Agent ID" }),
          /* @__PURE__ */ jsx("p", { class: "text-[10px] font-mono text-text-secondary truncate", children: agent.agent_id })
        ] })
      ] })
    ] }, agent.agent_id)),
    agents.length === 0 && /* @__PURE__ */ jsx("div", { class: "col-span-full py-12 text-center border border-dashed border-border rounded-card bg-surface-800/50", children: /* @__PURE__ */ jsx("p", { class: "text-sm text-text-muted", children: "No AgentCards found in the directory." }) })
  ] });
}
const $$Agents = createComponent(($$result, $$props, $$slots) => {
  return renderTemplate`${renderComponent($$result, "Layout", $$Layout, { "title": "Agent Directory" }, { "default": ($$result2) => renderTemplate` ${maybeRenderHead()}<main class="mx-auto max-w-5xl px-6 py-page"> <header class="mb-6 flex flex-col gap-1"> <h1 class="text-xl font-semibold tracking-tight text-text-primary">Agent Directory</h1> <p class="text-xs text-text-secondary">
Cryptographically signed ERC-8004 identity descriptors (AgentCards) for system agents. 
        Each card binds a public key to verifiable capabilities.
</p> </header> <section class="mb-6"> ${renderComponent($$result2, "AgentDirectory", AgentDirectory, { "client:load": true, "client:component-hydration": "load", "client:component-path": "D:/TrustMesh/TrustMesh/web-astro/src/components/AgentDirectory", "client:component-export": "default" })} </section> </main> ` })}`;
}, "D:/TrustMesh/TrustMesh/web-astro/src/pages/dashboard/agents.astro", void 0);
const $$file = "D:/TrustMesh/TrustMesh/web-astro/src/pages/dashboard/agents.astro";
const $$url = "/dashboard/agents";
const _page = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: $$Agents,
  file: $$file,
  url: $$url
}, Symbol.toStringTag, { value: "Module" }));
const page = () => _page;
export {
  page
};
