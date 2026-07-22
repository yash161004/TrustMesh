import { c as createComponent } from "./astro-component_CBpBdRmF.mjs";
import "piccolore";
import { J as createRenderInstruction, I as renderTemplate, u as maybeRenderHead, bk as renderSlot, _ as addAttribute, bl as renderHead } from "./sequence_DVNL_MTV.mjs";
import { r as renderComponent, m as mergeSlots } from "./entrypoint_DiKPQF1W.mjs";
import "clsx";
async function renderScript(result, id) {
  const inlined = result.inlinedScripts.get(id);
  let content = "";
  if (inlined != null) {
    if (inlined) {
      content = `<script type="module">${inlined}<\/script>`;
    }
  } else {
    const resolved = await result.resolve(id);
    content = `<script type="module" src="${result.userAssetsBase ? (result.base === "/" ? "" : result.base) + result.userAssetsBase : ""}${resolved}"><\/script>`;
  }
  return createRenderInstruction({ type: "script", id, content });
}
const $$ShowCSR = createComponent(($$result, $$props, $$slots) => {
  const Astro2 = $$result.createAstro($$props, $$slots);
  Astro2.self = $$ShowCSR;
  const { when, class: className } = Astro2.props;
  const isStringWhen = typeof when === "string";
  const whenCondition = isStringWhen ? when : null;
  const role = !isStringWhen && typeof when === "object" ? when.role : void 0;
  const permission = !isStringWhen && typeof when === "object" ? when.permission : void 0;
  const feature = !isStringWhen && typeof when === "object" ? when.feature : void 0;
  const plan = !isStringWhen && typeof when === "object" ? when.plan : void 0;
  return renderTemplate`${renderComponent($$result, "clerk-show", "clerk-show", { "data-when": whenCondition, "data-role": role, "data-permission": permission, "data-feature": feature, "data-plan": plan, "class": className }, { "default": () => renderTemplate` ${maybeRenderHead()}<div hidden data-clerk-control-slot-default> ${renderSlot($$result, $$slots["default"])} </div> <div hidden data-clerk-control-slot-fallback> ${renderSlot($$result, $$slots["fallback"])} </div> ` })} ${renderScript($$result, "D:/TrustMesh/TrustMesh/web-astro/node_modules/@clerk/astro/components/control/ShowCSR.astro?astro&type=script&index=0&lang.ts")}`;
}, "D:/TrustMesh/TrustMesh/web-astro/node_modules/@clerk/astro/components/control/ShowCSR.astro", void 0);
const $$ShowSSR = createComponent(($$result, $$props, $$slots) => {
  const Astro2 = $$result.createAstro($$props, $$slots);
  Astro2.self = $$ShowSSR;
  const { has, userId } = Astro2.locals.auth();
  const { when } = Astro2.props;
  const showContent = (() => {
    if (when === "signed-in") return !!userId;
    if (when === "signed-out") return !userId;
    if (typeof when === "function") return !!userId && when(has);
    if (typeof when === "object" && when !== null) {
      if (!userId) return false;
      return has(when);
    }
    return !!userId;
  })();
  const hasShowFallback = Astro2.slots.has("show-fallback");
  return renderTemplate`${showContent ? renderTemplate`${renderSlot($$result, $$slots["default"])}` : hasShowFallback ? renderTemplate`${renderSlot($$result, $$slots["show-fallback"])}` : renderTemplate`${renderSlot($$result, $$slots["fallback"])}`}`;
}, "D:/TrustMesh/TrustMesh/web-astro/node_modules/@clerk/astro/components/control/ShowSSR.astro", void 0);
const configOutput = "server";
function isStaticOutput(forceStatic) {
  if (forceStatic !== void 0) {
    return forceStatic;
  }
  return configOutput === "static";
}
const $$Show = createComponent(($$result, $$props, $$slots) => {
  const Astro2 = $$result.createAstro($$props, $$slots);
  Astro2.self = $$Show;
  const { isStatic, when, ...rest } = Astro2.props;
  if (typeof when === "undefined") {
    throw new Error("@clerk/astro: <Show /> requires a `when` prop.");
  }
  const props = { ...rest, when };
  const shouldUseCSR = isStatic !== void 0 ? isStaticOutput(isStatic) : !Astro2.locals?.auth;
  const ShowComponent = shouldUseCSR ? $$ShowCSR : $$ShowSSR;
  const hasShowFallback = Astro2.slots.has("show-fallback");
  return renderTemplate`${renderComponent($$result, "ShowComponent", ShowComponent, { ...props }, mergeSlots({ "default": ($$result2) => renderTemplate` ${renderSlot($$result2, $$slots["default"])} ` }, hasShowFallback ? { "show-fallback": () => renderTemplate`${renderSlot($$result, $$slots["show-fallback"])}` } : { "fallback": () => renderTemplate`${renderSlot($$result, $$slots["fallback"])}` }))}`;
}, "D:/TrustMesh/TrustMesh/web-astro/node_modules/@clerk/astro/components/control/Show.astro", void 0);
const $$Header = createComponent(($$result, $$props, $$slots) => {
  return renderTemplate`${maybeRenderHead()}<header class="flex items-center justify-between border-b border-border bg-surface-900 px-6 py-3"> <a href="/" class="text-lg font-bold text-gold no-underline tracking-tight">
TrustMesh
</a> <nav aria-label="Main" class="flex items-center gap-5"> ${renderComponent($$result, "Show", $$Show, { "when": "signed-in" }, { "default": ($$result2) => renderTemplate` <a href="/dashboard" class="text-sm text-text-secondary transition-colors duration-150 hover:text-text-primary">
Dashboard
</a> <a href="/dashboard/agents" class="text-sm text-text-secondary transition-colors duration-150 hover:text-text-primary">
Agent Directory
</a> <a href="/admin/analytics" class="text-sm text-text-secondary transition-colors duration-150 hover:text-text-primary">
Analytics
</a> <a href="/sign-out" class="text-sm text-text-secondary transition-colors duration-150 hover:text-text-primary">
Sign out
</a> ` })} ${renderComponent($$result, "Show", $$Show, { "when": "signed-out" }, { "default": ($$result2) => renderTemplate` <a href="/sign-in" class="text-sm text-text-secondary transition-colors duration-150 hover:text-text-primary">
Sign in
</a> <a href="/sign-up" class="rounded-card bg-gold px-3 py-1.5 text-sm font-medium text-surface-900 transition-colors duration-150 hover:bg-gold-hover">
Sign up
</a> ` })} </nav> </header>`;
}, "D:/TrustMesh/TrustMesh/web-astro/src/components/Header.astro", void 0);
const $$Layout = createComponent(($$result, $$props, $$slots) => {
  const Astro2 = $$result.createAstro($$props, $$slots);
  Astro2.self = $$Layout;
  const { title } = Astro2.props;
  return renderTemplate`<html lang="en" class="bg-surface-900 text-text-primary"> <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><link rel="icon" href="/favicon.ico"><meta name="generator"${addAttribute(Astro2.generator, "content")}><title>${title ? `${title} · TrustMesh` : "TrustMesh"}</title>${renderHead()}</head> <body class="min-h-screen"> ${renderComponent($$result, "Header", $$Header, {})} ${renderSlot($$result, $$slots["default"])} </body></html>`;
}, "D:/TrustMesh/TrustMesh/web-astro/src/layouts/Layout.astro", void 0);
export {
  $$Layout as $,
  renderScript as r
};
