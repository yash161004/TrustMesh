import { $ as $clerk, a as $csrState, b as $clerkStore, c as $initialState } from "../external-DHTxQaok_Bm5cKQZz.mjs";
import { setClerkJSLoadingErrorPackageName, loadClerkJSScript, loadClerkUIScript } from "@clerk/shared/loadClerkJsScript";
import { isTruthy } from "@clerk/shared/underscore";
const invokeClerkAstroJSFunctions = () => {
  ["handleRedirectCallback"].forEach((fnName) => {
    document.querySelectorAll(`[data-clerk-function-id^="clerk-${fnName}"]`).forEach((el) => {
      const id = el.getAttribute("data-clerk-function-id");
      const props = window.__astro_clerk_function_props?.get(fnName)?.get(id) ?? {};
      $clerk.get()?.[fnName]?.(props);
    });
  });
};
const mountAllClerkAstroJSComponents = () => {
  Object.entries({
    "create-organization": "mountCreateOrganization",
    "organization-list": "mountOrganizationList",
    "organization-profile": "mountOrganizationProfile",
    "organization-switcher": "mountOrganizationSwitcher",
    "user-avatar": "mountUserAvatar",
    "user-button": "mountUserButton",
    "user-profile": "mountUserProfile",
    "sign-in": "mountSignIn",
    "sign-up": "mountSignUp",
    "google-one-tap": "openGoogleOneTap",
    waitlist: "mountWaitlist",
    "pricing-table": "mountPricingTable",
    "api-keys": "mountAPIKeys"
  }).forEach(([category, mountFn]) => {
    document.querySelectorAll(`[data-clerk-id^="clerk-${category}"]`).forEach((el) => {
      const clerkId = el.getAttribute("data-clerk-id");
      const props = window.__astro_clerk_component_props?.get(category)?.get(clerkId);
      if (el) $clerk.get()?.[mountFn](el, props);
    });
  });
};
const runOnce = (onFirst) => {
  let hasRun = false;
  return (params) => {
    if (hasRun) {
      const clerkJSInstance = window.Clerk;
      return new Promise((res) => {
        if (!clerkJSInstance) return res(false);
        if (clerkJSInstance.loaded) {
          mountAllClerkAstroJSComponents();
          invokeClerkAstroJSFunctions();
        }
        return res(clerkJSInstance.loaded);
      });
    }
    hasRun = true;
    return onFirst(params);
  };
};
setClerkJSLoadingErrorPackageName("@clerk/astro");
function createNavigationHandler(windowNav) {
  return (to, opts) => {
    if (opts?.__internal_metadata?.navigationType === "internal") windowNav(history.state, "", to);
    else opts?.windowNavigate(to);
  };
}
const createClerkInstance = runOnce(createClerkInstanceInternal);
async function createClerkInstanceInternal(options) {
  const clerkJsChunk = getClerkJsEntryChunk(options);
  const ClerkUI = getClerkUIEntryChunk(options);
  await clerkJsChunk;
  if (!window.Clerk) throw new Error("Failed to download latest ClerkJS. Contact support@clerk.com.");
  const clerkJSInstance = window.Clerk;
  if (!$clerk.get()) $clerk.set(clerkJSInstance);
  const internalOptions = options;
  const keylessClaimUrl = internalOptions.__internal_keylessClaimUrl;
  const keylessApiKeysUrl = internalOptions.__internal_keylessApiKeysUrl;
  const clerkOptions = {
    routerPush: createNavigationHandler(window.history.pushState.bind(window.history)),
    routerReplace: createNavigationHandler(window.history.replaceState.bind(window.history)),
    ...options,
    ui: {
      ...options?.ui,
      ClerkUI
    },
    ...keylessClaimUrl && { __internal_keyless_claimKeylessApplicationUrl: keylessClaimUrl },
    ...keylessApiKeysUrl && { __internal_keyless_copyInstanceKeysUrl: keylessApiKeysUrl }
  };
  return clerkJSInstance.load(clerkOptions).then(() => {
    $csrState.setKey("isLoaded", true);
    $clerkStore.notify();
    mountAllClerkAstroJSComponents();
    invokeClerkAstroJSFunctions();
    clerkJSInstance.addListener((payload) => {
      $csrState.setKey("client", payload.client);
      $csrState.setKey("user", payload.user);
      $csrState.setKey("session", payload.session);
      $csrState.setKey("organization", payload.organization);
    });
  }).catch(() => {
  });
}
async function getClerkJsEntryChunk(options) {
  await loadClerkJSScript(options);
}
function getClerkUIEntryChunk(options) {
  if (options?.ui?.ClerkUI) return options.ui.ClerkUI;
  if (options?.ui || options?.prefetchUI === false) return;
  return loadClerkUIEntryChunk(options);
}
async function loadClerkUIEntryChunk(options) {
  await loadClerkUIScript(options);
  if (!window.__internal_ClerkUICtor) throw new Error("Failed to download latest Clerk UI. Contact support@clerk.com.");
  return window.__internal_ClerkUICtor;
}
function mergePrefetchUIConfig(paramPrefetchUI) {
  if (paramPrefetchUI === false) return false;
}
const mergeEnvVarsWithParams = (params) => {
  const { signInUrl: paramSignIn, signUpUrl: paramSignUp, isSatellite: paramSatellite, proxyUrl: paramProxy, domain: paramDomain, publishableKey: paramPublishableKey, telemetry: paramTelemetry, __internal_clerkJSUrl: paramClerkJSUrl, __internal_clerkJSVersion: paramClerkJSVersion, __internal_clerkUIUrl: paramClerkUIUrl, __internal_clerkUIVersion: paramClerkUIVersion, prefetchUI: paramPrefetchUI, unsafe_disableDevelopmentModeConsoleWarning: paramUnsafeDisableDevelopmentModeConsoleWarning, ...rest } = params || {};
  const internalOptions = params;
  return {
    signInUrl: paramSignIn || void 0,
    signUpUrl: paramSignUp || void 0,
    isSatellite: paramSatellite || void 0,
    proxyUrl: paramProxy || void 0,
    domain: paramDomain || void 0,
    publishableKey: paramPublishableKey || internalOptions?.publishableKey || "pk_test_Y3V0ZS1nb3NoYXdrLTk4LmNsZXJrLmFjY291bnRzLmRldiQ",
    __internal_clerkJSUrl: paramClerkJSUrl || void 0,
    __internal_clerkJSVersion: paramClerkJSVersion || void 0,
    __internal_clerkUIUrl: paramClerkUIUrl || void 0,
    __internal_clerkUIVersion: paramClerkUIVersion || void 0,
    prefetchUI: mergePrefetchUIConfig(paramPrefetchUI),
    telemetry: paramTelemetry || {
      disabled: isTruthy(void 0),
      debug: isTruthy(void 0)
    },
    unsafe_disableDevelopmentModeConsoleWarning: paramUnsafeDisableDevelopmentModeConsoleWarning ?? isTruthy(void 0),
    __internal_keylessClaimUrl: internalOptions?.keylessClaimUrl,
    __internal_keylessApiKeysUrl: internalOptions?.keylessApiKeysUrl,
    ...rest
  };
};
function createInjectionScriptRunner(creator) {
  async function runner(astroClerkOptions) {
    const ssrDataContainer = document.getElementById("__CLERK_ASTRO_DATA__");
    if (ssrDataContainer) $initialState.set(JSON.parse(ssrDataContainer.textContent || "{}"));
    const clientSafeVarsContainer = document.getElementById("__CLERK_ASTRO_SAFE_VARS__");
    let clientSafeVars = {};
    if (clientSafeVarsContainer) clientSafeVars = JSON.parse(clientSafeVarsContainer.textContent || "{}");
    await creator({ ...mergeEnvVarsWithParams({
      ...astroClerkOptions,
      ...clientSafeVars
    }) });
  }
  return runner;
}
const runInjectionScript = createInjectionScriptRunner(createClerkInstance);
await runInjectionScript({ "sdkMetadata": { "version": "3.4.19", "name": "@clerk/astro", "environment": "production" } });
