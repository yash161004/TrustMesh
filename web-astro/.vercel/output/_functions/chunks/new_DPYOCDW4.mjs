import { c as createComponent } from "./astro-component_CBpBdRmF.mjs";
import "piccolore";
import { I as renderTemplate, u as maybeRenderHead } from "./sequence_DVNL_MTV.mjs";
import { r as renderComponent } from "./entrypoint_DiKPQF1W.mjs";
import { $ as $$Layout } from "./Layout_CxVI5k03.mjs";
import { jsxs, jsx } from "react/jsx-runtime";
import { useState } from "react";
import { u as useAuth, c as createSession } from "./api_BrLtL2v5.mjs";
function FormIcon({ type }) {
  const icons = {
    building: /* @__PURE__ */ jsx("path", { "stroke-linecap": "round", "stroke-linejoin": "round", d: "M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21" }),
    cube: /* @__PURE__ */ jsx("path", { "stroke-linecap": "round", "stroke-linejoin": "round", d: "M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" }),
    currency: /* @__PURE__ */ jsx("path", { "stroke-linecap": "round", "stroke-linejoin": "round", d: "M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" }),
    hashtag: /* @__PURE__ */ jsx("path", { "stroke-linecap": "round", "stroke-linejoin": "round", d: "M5.25 8.25h15m-16.5 7.5h15m-1.8-13.5l-3.9 19.5m-2.1-19.5l-3.9 19.5" })
  };
  return /* @__PURE__ */ jsx("svg", { class: "h-4 w-4 text-text-muted absolute left-3.5 top-1/2 -translate-y-1/2", fill: "none", viewBox: "0 0 24 24", stroke: "currentColor", "stroke-width": "1.5", children: icons[type] });
}
function LaunchForm({ clerkBypass } = {}) {
  const { getToken } = useAuth();
  const [fields, setFields] = useState({
    counterparty: "Acme Corp",
    product: "Industrial Valves",
    budgetCap: "500.00",
    quantity: "100"
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [touched, setTouched] = useState({});
  function update(k, v) {
    setFields((prev) => ({ ...prev, [k]: v }));
  }
  function handleBlur(field) {
    setTouched((prev) => ({ ...prev, [field]: true }));
  }
  const isInvalid = (field) => touched[field] && !fields[field];
  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const token = clerkBypass ? "mock_token" : await getToken() || "mock_token";
      const result = await createSession(token, {
        buyer_agent_id: "buyer-agent-001",
        seller_agent_id: "seller-agent-001",
        provider: "mock",
        scenario: {
          product_name: fields.product || "Office chairs",
          quantity: parseInt(fields.quantity, 10) || 100,
          market_reference_price: parseFloat(fields.budgetCap) || 500,
          buyer_budget_cap: parseFloat(fields.budgetCap) || 500,
          buyer_target_price: (parseFloat(fields.budgetCap) || 500) * 0.88,
          seller_floor_price: (parseFloat(fields.budgetCap) || 500) * 0.84,
          seller_asking_price: (parseFloat(fields.budgetCap) || 500) * 1.1,
          delivery_preference_days: 14,
          standard_delivery_days: 21
        }
      });
      window.location.href = `/dashboard/sessions/${result.session_id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create session");
      setSubmitting(false);
    }
  }
  if (submitting) {
    return /* @__PURE__ */ jsxs("div", { class: "rounded-card border border-border bg-surface-800 px-card py-16 text-center", children: [
      /* @__PURE__ */ jsx("div", { class: "mb-3 mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-surface-750", children: /* @__PURE__ */ jsxs("svg", { class: "h-6 w-6 animate-spin text-gold", fill: "none", viewBox: "0 0 24 24", children: [
        /* @__PURE__ */ jsx("circle", { class: "opacity-25", cx: "12", cy: "12", r: "10", stroke: "currentColor", "stroke-width": "4" }),
        /* @__PURE__ */ jsx("path", { class: "opacity-75", fill: "currentColor", d: "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" })
      ] }) }),
      /* @__PURE__ */ jsx("p", { class: "text-base font-medium text-text-primary", children: "Creating session…" }),
      /* @__PURE__ */ jsx("p", { class: "mt-1 text-sm text-text-secondary", children: "Connecting to backend" })
    ] });
  }
  return /* @__PURE__ */ jsxs("div", { class: "grid grid-cols-1 lg:grid-cols-3 gap-6 items-start", children: [
    /* @__PURE__ */ jsxs("form", { onSubmit: handleSubmit, class: "space-y-5 lg:col-span-2", children: [
      error && /* @__PURE__ */ jsxs("div", { class: "rounded-card border border-dot-flagged/30 bg-dot-flagged/10 px-4 py-3 text-sm text-dot-flagged flex items-center gap-2", children: [
        /* @__PURE__ */ jsx("svg", { class: "h-4 w-4", fill: "none", viewBox: "0 0 24 24", stroke: "currentColor", "stroke-width": "2", children: /* @__PURE__ */ jsx("path", { "stroke-linecap": "round", "stroke-linejoin": "round", d: "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" }) }),
        error
      ] }),
      /* @__PURE__ */ jsxs("div", { children: [
        /* @__PURE__ */ jsx("label", { htmlFor: "field-counterparty", class: "mb-1.5 block text-[13px] font-semibold text-text-primary tracking-wide", children: "Counterparty" }),
        /* @__PURE__ */ jsxs("div", { class: "relative", children: [
          /* @__PURE__ */ jsx(FormIcon, { type: "building" }),
          /* @__PURE__ */ jsx(
            "input",
            {
              id: "field-counterparty",
              value: fields.counterparty,
              onBlur: () => handleBlur("counterparty"),
              onChange: (e) => update("counterparty", e.target.value),
              placeholder: "e.g. Acme Corp",
              class: `w-full rounded-card border bg-surface-800 pl-10 pr-4 py-2.5 text-sm text-text-primary placeholder:text-text-muted transition-colors duration-150 focus:outline-none focus-visible:ring-2 ${isInvalid("counterparty") ? "border-dot-flagged focus-visible:ring-dot-flagged/30" : "border-border focus:border-border-hover focus-visible:ring-gold/50"}`
            }
          )
        ] }),
        isInvalid("counterparty") && /* @__PURE__ */ jsx("p", { class: "mt-1 text-[11px] text-dot-flagged", children: "Counterparty is required." })
      ] }),
      /* @__PURE__ */ jsxs("div", { children: [
        /* @__PURE__ */ jsx("label", { htmlFor: "field-product", class: "mb-1.5 block text-[13px] font-semibold text-text-primary tracking-wide", children: "Product" }),
        /* @__PURE__ */ jsxs("div", { class: "relative", children: [
          /* @__PURE__ */ jsx(FormIcon, { type: "cube" }),
          /* @__PURE__ */ jsx(
            "input",
            {
              id: "field-product",
              value: fields.product,
              onBlur: () => handleBlur("product"),
              onChange: (e) => update("product", e.target.value),
              placeholder: "e.g. Industrial Valves",
              class: `w-full rounded-card border bg-surface-800 pl-10 pr-4 py-2.5 text-sm text-text-primary placeholder:text-text-muted transition-colors duration-150 focus:outline-none focus-visible:ring-2 ${isInvalid("product") ? "border-dot-flagged focus-visible:ring-dot-flagged/30" : "border-border focus:border-border-hover focus-visible:ring-gold/50"}`
            }
          )
        ] }),
        isInvalid("product") && /* @__PURE__ */ jsx("p", { class: "mt-1 text-[11px] text-dot-flagged", children: "Product is required." })
      ] }),
      /* @__PURE__ */ jsxs("div", { class: "grid grid-cols-1 gap-5 sm:grid-cols-2", children: [
        /* @__PURE__ */ jsxs("div", { children: [
          /* @__PURE__ */ jsx("label", { htmlFor: "field-budget", class: "mb-1.5 block text-[13px] font-semibold text-text-primary tracking-wide", children: "Budget Cap ($)" }),
          /* @__PURE__ */ jsxs("div", { class: "relative", children: [
            /* @__PURE__ */ jsx(FormIcon, { type: "currency" }),
            /* @__PURE__ */ jsx(
              "input",
              {
                id: "field-budget",
                type: "number",
                step: "0.01",
                value: fields.budgetCap,
                onBlur: () => handleBlur("budgetCap"),
                onChange: (e) => update("budgetCap", e.target.value),
                class: `w-full rounded-card border bg-surface-800 pl-10 pr-4 py-2.5 text-sm text-text-primary font-mono transition-colors duration-150 focus:outline-none focus-visible:ring-2 ${isInvalid("budgetCap") || parseFloat(fields.budgetCap) <= 0 ? "border-dot-flagged focus-visible:ring-dot-flagged/30" : "border-border focus:border-border-hover focus-visible:ring-gold/50"}`
              }
            )
          ] }),
          (isInvalid("budgetCap") || parseFloat(fields.budgetCap) <= 0) && touched.budgetCap && /* @__PURE__ */ jsx("p", { class: "mt-1 text-[11px] text-dot-flagged", children: "Enter a valid budget." })
        ] }),
        /* @__PURE__ */ jsxs("div", { children: [
          /* @__PURE__ */ jsx("label", { htmlFor: "field-quantity", class: "mb-1.5 block text-[13px] font-semibold text-text-primary tracking-wide", children: "Quantity" }),
          /* @__PURE__ */ jsxs("div", { class: "relative", children: [
            /* @__PURE__ */ jsx(FormIcon, { type: "hashtag" }),
            /* @__PURE__ */ jsx(
              "input",
              {
                id: "field-quantity",
                type: "number",
                value: fields.quantity,
                onBlur: () => handleBlur("quantity"),
                onChange: (e) => update("quantity", e.target.value),
                class: `w-full rounded-card border bg-surface-800 pl-10 pr-4 py-2.5 text-sm text-text-primary font-mono transition-colors duration-150 focus:outline-none focus-visible:ring-2 ${isInvalid("quantity") || parseInt(fields.quantity, 10) < 1 ? "border-dot-flagged focus-visible:ring-dot-flagged/30" : "border-border focus:border-border-hover focus-visible:ring-gold/50"}`
              }
            )
          ] }),
          (isInvalid("quantity") || parseInt(fields.quantity, 10) < 1) && touched.quantity && /* @__PURE__ */ jsx("p", { class: "mt-1 text-[11px] text-dot-flagged", children: "Quantity must be at least 1." })
        ] })
      ] }),
      /* @__PURE__ */ jsx(
        "button",
        {
          type: "submit",
          disabled: submitting,
          class: "rounded-card bg-gold px-5 py-2.5 text-sm font-medium text-surface-900 transition-all duration-150 hover:bg-gold-hover hover:shadow-lg hover:shadow-gold/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/50 disabled:opacity-50",
          children: "Launch Session"
        }
      )
    ] }),
    /* @__PURE__ */ jsxs("div", { class: "rounded-card border border-border bg-surface-800 p-5 hidden lg:block", children: [
      /* @__PURE__ */ jsx("h3", { class: "mb-4 text-xs font-semibold uppercase tracking-widest text-text-muted", children: "Negotiation Envelope" }),
      /* @__PURE__ */ jsxs("dl", { class: "space-y-3 text-sm", children: [
        /* @__PURE__ */ jsxs("div", { class: "flex justify-between items-center pb-3 border-b border-border/50", children: [
          /* @__PURE__ */ jsx("dt", { class: "text-text-secondary text-xs", children: "Total Target Value" }),
          /* @__PURE__ */ jsxs("dd", { class: "font-mono text-gold font-medium", children: [
            "$",
            (parseFloat(fields.budgetCap || "0") * parseInt(fields.quantity || "0", 10)).toLocaleString()
          ] })
        ] }),
        /* @__PURE__ */ jsxs("div", { class: "flex justify-between items-center", children: [
          /* @__PURE__ */ jsx("dt", { class: "text-text-secondary text-xs", children: "Buyer Target Price" }),
          /* @__PURE__ */ jsxs("dd", { class: "font-mono text-text-primary", children: [
            "$",
            (parseFloat(fields.budgetCap || "0") * 0.88).toFixed(2)
          ] })
        ] }),
        /* @__PURE__ */ jsxs("div", { class: "flex justify-between items-center", children: [
          /* @__PURE__ */ jsx("dt", { class: "text-text-secondary text-xs", children: "Seller Floor Price" }),
          /* @__PURE__ */ jsxs("dd", { class: "font-mono text-text-muted", children: [
            "$",
            (parseFloat(fields.budgetCap || "0") * 0.84).toFixed(2)
          ] })
        ] }),
        /* @__PURE__ */ jsxs("div", { class: "flex justify-between items-center", children: [
          /* @__PURE__ */ jsx("dt", { class: "text-text-secondary text-xs", children: "Seller Ask Price" }),
          /* @__PURE__ */ jsxs("dd", { class: "font-mono text-text-muted", children: [
            "$",
            (parseFloat(fields.budgetCap || "0") * 1.1).toFixed(2)
          ] })
        ] })
      ] })
    ] })
  ] });
}
const $$New = createComponent(($$result, $$props, $$slots) => {
  const clerkBypass = process.env.CLERK_BYPASS === "true";
  return renderTemplate`${renderComponent($$result, "Layout", $$Layout, { "title": "New Session" }, { "default": ($$result2) => renderTemplate` ${maybeRenderHead()}<main class="mx-auto max-w-2xl px-6 py-page"> <a href="/dashboard" class="mb-6 inline-block text-sm text-text-secondary transition-colors duration-150 hover:text-text-primary">
&larr; Back to Sessions
</a> <h1 class="mb-8 text-xl font-semibold tracking-tight text-text-primary">Launch Negotiation</h1> ${renderComponent($$result2, "LaunchForm", LaunchForm, { "client:load": true, "clerkBypass": clerkBypass, "client:component-hydration": "load", "client:component-path": "D:/TrustMesh/TrustMesh/web-astro/src/components/LaunchForm", "client:component-export": "default" })} </main> ` })}`;
}, "D:/TrustMesh/TrustMesh/web-astro/src/pages/dashboard/new.astro", void 0);
const $$file = "D:/TrustMesh/TrustMesh/web-astro/src/pages/dashboard/new.astro";
const $$url = "/dashboard/new";
const _page = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: $$New,
  file: $$file,
  url: $$url
}, Symbol.toStringTag, { value: "Module" }));
const page = () => _page;
export {
  page
};
