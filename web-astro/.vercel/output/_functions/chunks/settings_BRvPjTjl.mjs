import { c as createComponent } from "./astro-component_CBpBdRmF.mjs";
import "piccolore";
import { I as renderTemplate, u as maybeRenderHead } from "./sequence_DVNL_MTV.mjs";
import { r as renderComponent } from "./entrypoint_DiKPQF1W.mjs";
import { $ as $$Layout } from "./Layout_CxVI5k03.mjs";
import { jsxs, jsx } from "react/jsx-runtime";
const MOCK_ORG = {
  name: "Acme Corp",
  slug: "acme-corp",
  plan: "Enterprise",
  created: "2025-11-01",
  members: [
    { role: "Admin", email: "alice@acme.dev", name: "Alice Chen", avatar: "AC" },
    { role: "Admin", email: "bob@acme.dev", name: "Bob Gupta", avatar: "BG" },
    { role: "Member", email: "carol@acme.dev", name: "Carol Davis", avatar: "CD" },
    { role: "Viewer", email: "dan@acme.dev", name: "Dan Kim", avatar: "DK" }
  ]
};
function Avatar({ children }) {
  return /* @__PURE__ */ jsx("span", { class: "flex h-7 w-7 shrink-0 items-center justify-center rounded-card bg-surface-700 font-mono text-[10px] font-bold text-text-secondary", children });
}
function OrgSettings() {
  return /* @__PURE__ */ jsxs("div", { class: "mx-auto max-w-3xl space-y-6", children: [
    /* @__PURE__ */ jsxs("section", { class: "rounded-card border border-border bg-surface-800 px-card py-card", children: [
      /* @__PURE__ */ jsx("h2", { class: "mb-4 text-sm font-semibold text-text-primary tracking-wide", children: "Organization" }),
      /* @__PURE__ */ jsxs("dl", { class: "space-y-3 text-sm", children: [
        /* @__PURE__ */ jsxs("div", { class: "flex items-center justify-between border-b border-border/50 pb-3", children: [
          /* @__PURE__ */ jsx("dt", { class: "text-[10px] font-medium uppercase tracking-widest text-text-muted", children: "Name" }),
          /* @__PURE__ */ jsx("dd", { class: "font-mono text-text-primary", children: MOCK_ORG.name })
        ] }),
        /* @__PURE__ */ jsxs("div", { class: "flex items-center justify-between border-b border-border/50 pb-3", children: [
          /* @__PURE__ */ jsx("dt", { class: "text-[10px] font-medium uppercase tracking-widest text-text-muted", children: "Slug" }),
          /* @__PURE__ */ jsx("dd", { class: "font-mono text-text-secondary", children: MOCK_ORG.slug })
        ] }),
        /* @__PURE__ */ jsxs("div", { class: "flex items-center justify-between border-b border-border/50 pb-3", children: [
          /* @__PURE__ */ jsx("dt", { class: "text-[10px] font-medium uppercase tracking-widest text-text-muted", children: "Plan" }),
          /* @__PURE__ */ jsx("dd", { children: /* @__PURE__ */ jsxs("span", { class: "inline-flex items-center gap-1.5 rounded-full border border-gold/30 bg-gold/5 px-2.5 py-0.5 text-[10px] font-medium text-gold", children: [
            /* @__PURE__ */ jsx("span", { class: "h-1.5 w-1.5 rounded-full bg-gold" }),
            MOCK_ORG.plan
          ] }) })
        ] }),
        /* @__PURE__ */ jsxs("div", { class: "flex items-center justify-between", children: [
          /* @__PURE__ */ jsx("dt", { class: "text-[10px] font-medium uppercase tracking-widest text-text-muted", children: "Created" }),
          /* @__PURE__ */ jsx("dd", { class: "font-mono text-xs text-text-secondary", children: MOCK_ORG.created })
        ] })
      ] })
    ] }),
    /* @__PURE__ */ jsxs("section", { class: "rounded-card border border-border bg-surface-800 px-card py-card", children: [
      /* @__PURE__ */ jsx("h2", { class: "mb-4 text-sm font-semibold text-text-primary tracking-wide", children: "Members" }),
      /* @__PURE__ */ jsx("div", { class: "space-y-2", children: MOCK_ORG.members.map((m) => /* @__PURE__ */ jsxs("div", { class: "flex items-center gap-3 rounded-card px-2 py-2 transition-colors duration-150 hover:bg-surface-750", children: [
        /* @__PURE__ */ jsx(Avatar, { children: m.avatar }),
        /* @__PURE__ */ jsxs("div", { class: "min-w-0 flex-1", children: [
          /* @__PURE__ */ jsx("p", { class: "text-sm text-text-primary truncate", children: m.name }),
          /* @__PURE__ */ jsx("p", { class: "text-[10px] text-text-muted truncate", children: m.email })
        ] }),
        /* @__PURE__ */ jsx("span", { class: "shrink-0 rounded-full border border-border bg-surface-700/50 px-2 py-0.5 text-[10px] font-medium text-text-secondary", children: m.role })
      ] }, m.email)) })
    ] })
  ] });
}
const $$Settings = createComponent(($$result, $$props, $$slots) => {
  return renderTemplate`${renderComponent($$result, "Layout", $$Layout, { "title": "Settings" }, { "default": ($$result2) => renderTemplate` ${maybeRenderHead()}<main class="mx-auto px-6 py-page"> <header class="mb-6 text-center"> <h1 class="text-xl font-semibold tracking-tight text-text-primary">Settings</h1> <p class="mt-1 text-xs text-text-secondary">Organization and account</p> </header> ${renderComponent($$result2, "OrgSettings", OrgSettings, { "client:load": true, "client:component-hydration": "load", "client:component-path": "D:/TrustMesh/TrustMesh/web-astro/src/components/OrgSettings", "client:component-export": "default" })} </main> ` })}`;
}, "D:/TrustMesh/TrustMesh/web-astro/src/pages/settings.astro", void 0);
const $$file = "D:/TrustMesh/TrustMesh/web-astro/src/pages/settings.astro";
const $$url = "/settings";
const _page = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: $$Settings,
  file: $$file,
  url: $$url
}, Symbol.toStringTag, { value: "Module" }));
const page = () => _page;
export {
  page
};
