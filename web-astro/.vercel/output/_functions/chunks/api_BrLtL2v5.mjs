import { d as $authStore, a as $csrState, $ as $clerk } from "./external-DHTxQaok_Bm5cKQZz.mjs";
import React, { useCallback, useSyncExternalStore, useEffect } from "react";
import { computed } from "nanostores";
import { jsx, Fragment } from "react/jsx-runtime";
import { createCheckAuthorization, resolveAuthState } from "@clerk/shared/authorization";
import { deriveState } from "@clerk/shared/deriveState";
import { a as authAsyncStorage } from "./async-local-storage.server_B4Fwrbxx.mjs";
import "@clerk/shared/react";
function useStore$1(store) {
  const get = store.get.bind(store);
  return React.useSyncExternalStore(store.listen, get, get);
}
const withClerk = (Component, displayName) => {
  displayName = displayName || Component.displayName || Component.name || "Component";
  Component.displayName = displayName;
  const HOC = (props) => {
    const clerk = useStore$1(computed([$csrState, $clerk], (state, clerk2) => {
      return state.isLoaded ? clerk2 : null;
    }));
    return /* @__PURE__ */ jsx(Component, {
      ...props,
      clerk
    }, clerk ? "a" : "b");
  };
  HOC.displayName = `withClerk(${displayName})`;
  return HOC;
};
const assertSingleChild = (children) => (name) => {
  try {
    return React.Children.only(children);
  } catch {
    const childArray = React.Children.toArray(children);
    if (childArray.length === 1 && React.isValidElement(childArray[0])) return childArray[0];
    return `You've passed multiple children components to <${name}/>. You can only pass a single child component or text.`;
  }
};
const normalizeWithDefaultValue = (children, defaultText) => {
  if (!children) children = defaultText;
  if (typeof children === "string") children = /* @__PURE__ */ jsx("button", {
    type: "button",
    children
  });
  return children;
};
const safeExecute = (cb) => (...args) => {
  if (cb && typeof cb === "function") return cb(...args);
};
withClerk(({ clerk, children, ...props }) => {
  const { planId, planPeriod, for: _for, onSubscriptionComplete, newSubscriptionRedirectUrl, checkoutProps, ...rest } = props;
  children = normalizeWithDefaultValue(children, "Checkout");
  const child = assertSingleChild(children)("CheckoutButton");
  const clickHandler = () => {
    if (!clerk) return;
    return clerk.__internal_openCheckout({
      planId,
      planPeriod,
      for: _for,
      onSubscriptionComplete,
      newSubscriptionRedirectUrl,
      ...checkoutProps
    });
  };
  const wrappedChildClickHandler = (e) => {
    if (child && typeof child === "object" && "props" in child) safeExecute(child.props.onClick)(e);
    return clickHandler();
  };
  const childProps = {
    ...rest,
    onClick: wrappedChildClickHandler
  };
  return React.cloneElement(child, childProps);
}, "CheckoutButton");
withClerk(({ clerk, children, ...props }) => {
  const { plan, planId, initialPlanPeriod, planDetailsProps, ...rest } = props;
  children = normalizeWithDefaultValue(children, "Plan details");
  const child = assertSingleChild(children)("PlanDetailsButton");
  const clickHandler = () => {
    if (!clerk) return;
    return clerk.__internal_openPlanDetails({
      plan,
      planId,
      initialPlanPeriod,
      ...planDetailsProps
    });
  };
  const wrappedChildClickHandler = (e) => {
    if (child && typeof child === "object" && "props" in child) safeExecute(child.props.onClick)(e);
    return clickHandler();
  };
  const childProps = {
    ...rest,
    onClick: wrappedChildClickHandler
  };
  return React.cloneElement(child, childProps);
}, "PlanDetailsButton");
withClerk(({ clerk, children, ...props }) => {
  const { signUpFallbackRedirectUrl, forceRedirectUrl, fallbackRedirectUrl, signUpForceRedirectUrl, mode, ...rest } = props;
  children = normalizeWithDefaultValue(children, "Sign in");
  const child = assertSingleChild(children)("SignInButton");
  const clickHandler = () => {
    const opts = {
      forceRedirectUrl,
      fallbackRedirectUrl,
      signUpFallbackRedirectUrl,
      signUpForceRedirectUrl
    };
    if (!clerk) return;
    if (mode === "modal") return clerk.openSignIn({
      ...opts,
      appearance: props.appearance
    });
    return clerk.redirectToSignIn({
      ...opts,
      signInFallbackRedirectUrl: fallbackRedirectUrl,
      signInForceRedirectUrl: forceRedirectUrl
    });
  };
  const wrappedChildClickHandler = async (e) => {
    if (child && typeof child === "object" && "props" in child) await safeExecute(child.props.onClick)(e);
    return clickHandler();
  };
  const childProps = {
    ...rest,
    onClick: wrappedChildClickHandler
  };
  return React.cloneElement(child, childProps);
}, "SignInButton");
withClerk(({ clerk, children, ...props }) => {
  const { redirectUrl = "/", sessionId, ...rest } = props;
  children = normalizeWithDefaultValue(children, "Sign out");
  const child = assertSingleChild(children)("SignOutButton");
  const clickHandler = () => clerk?.signOut({
    redirectUrl,
    sessionId
  });
  const wrappedChildClickHandler = async (e) => {
    if (child && typeof child === "object" && "props" in child) await safeExecute(child.props.onClick)(e);
    return clickHandler();
  };
  const childProps = {
    ...rest,
    onClick: wrappedChildClickHandler
  };
  return React.cloneElement(child, childProps);
}, "SignOutButton");
withClerk(({ clerk, children, ...props }) => {
  const { fallbackRedirectUrl, forceRedirectUrl, signInFallbackRedirectUrl, signInForceRedirectUrl, mode, ...rest } = props;
  children = normalizeWithDefaultValue(children, "Sign up");
  const child = assertSingleChild(children)("SignUpButton");
  const clickHandler = () => {
    const opts = {
      fallbackRedirectUrl,
      forceRedirectUrl,
      signInFallbackRedirectUrl,
      signInForceRedirectUrl
    };
    if (!clerk) return;
    if (mode === "modal") return clerk.openSignUp({
      ...opts,
      appearance: props.appearance,
      unsafeMetadata: props.unsafeMetadata
    });
    return clerk.redirectToSignUp({
      ...opts,
      signUpFallbackRedirectUrl: fallbackRedirectUrl,
      signUpForceRedirectUrl: forceRedirectUrl
    });
  };
  const wrappedChildClickHandler = async (e) => {
    if (child && typeof child === "object" && "props" in child) await safeExecute(child.props.onClick)(e);
    return clickHandler();
  };
  const childProps = {
    ...rest,
    onClick: wrappedChildClickHandler
  };
  return React.cloneElement(child, childProps);
}, "SignUpButton");
withClerk(({ clerk, children, ...props }) => {
  const { for: _for, subscriptionDetailsProps, onSubscriptionCancel, ...rest } = props;
  children = normalizeWithDefaultValue(children, "Subscription details");
  const child = assertSingleChild(children)("SubscriptionDetailsButton");
  const clickHandler = () => {
    if (!clerk) return;
    return clerk.__internal_openSubscriptionDetails({
      for: _for,
      onSubscriptionCancel,
      ...subscriptionDetailsProps
    });
  };
  const wrappedChildClickHandler = (e) => {
    if (child && typeof child === "object" && "props" in child) safeExecute(child.props.onClick)(e);
    return clickHandler();
  };
  const childProps = {
    ...rest,
    onClick: wrappedChildClickHandler
  };
  return React.cloneElement(child, childProps);
}, "SubscriptionDetailsButton");
const isMountProps = (props) => {
  return "mount" in props;
};
const isOpenProps = (props) => {
  return "open" in props;
};
var Portal = class extends React.PureComponent {
  portalRef = React.createRef();
  componentDidUpdate(prevProps) {
    if (!isMountProps(prevProps) || !isMountProps(this.props)) return;
    if (prevProps.props.appearance !== this.props.props.appearance || prevProps.props?.customPages?.length !== this.props.props?.customPages?.length) this.props.updateProps?.({
      node: this.portalRef.current,
      props: this.props.props
    });
  }
  componentDidMount() {
    if (this.portalRef.current) {
      if (isMountProps(this.props)) this.props.mount?.(this.portalRef.current, this.props.props);
      if (isOpenProps(this.props)) this.props.open?.(this.props.props);
    }
  }
  componentWillUnmount() {
    if (this.portalRef.current) {
      if (isMountProps(this.props)) this.props.unmount?.(this.portalRef.current);
      if (isOpenProps(this.props)) this.props.close?.();
    }
  }
  render() {
    return /* @__PURE__ */ jsx(Fragment, { children: /* @__PURE__ */ jsx("div", { ref: this.portalRef }) });
  }
};
withClerk(({ clerk, ...props }) => {
  return /* @__PURE__ */ jsx(Portal, {
    mount: clerk?.mountSignIn,
    unmount: clerk?.unmountSignIn,
    updateProps: clerk?.__internal_updateProps,
    props
  });
}, "SignIn");
withClerk(({ clerk, ...props }) => {
  return /* @__PURE__ */ jsx(Portal, {
    mount: clerk?.mountSignUp,
    unmount: clerk?.unmountSignUp,
    updateProps: clerk?.__internal_updateProps,
    props
  });
}, "SignUp");
withClerk(({ clerk, ...props }) => {
  return /* @__PURE__ */ jsx(Portal, {
    mount: clerk?.mountUserButton,
    unmount: clerk?.unmountUserButton,
    updateProps: clerk?.__internal_updateProps,
    props
  });
}, "UserButton");
withClerk(({ clerk, ...props }) => {
  return /* @__PURE__ */ jsx(Portal, {
    mount: clerk?.mountUserProfile,
    unmount: clerk?.unmountUserProfile,
    updateProps: clerk?.__internal_updateProps,
    props
  });
}, "UserProfile");
withClerk(({ clerk, ...props }) => {
  return /* @__PURE__ */ jsx(Portal, {
    mount: clerk?.mountOrganizationProfile,
    unmount: clerk?.unmountOrganizationProfile,
    updateProps: clerk?.__internal_updateProps,
    props
  });
}, "OrganizationProfile");
withClerk(({ clerk, ...props }) => {
  return /* @__PURE__ */ jsx(Portal, {
    mount: clerk?.mountOrganizationSwitcher,
    unmount: clerk?.unmountOrganizationSwitcher,
    updateProps: clerk?.__internal_updateProps,
    props
  });
}, "OrganizationSwitcher");
withClerk(({ clerk, ...props }) => {
  return /* @__PURE__ */ jsx(Portal, {
    mount: clerk?.mountOrganizationList,
    unmount: clerk?.unmountOrganizationList,
    updateProps: clerk?.__internal_updateProps,
    props
  });
}, "OrganizationList");
withClerk(({ clerk, ...props }) => {
  return /* @__PURE__ */ jsx(Portal, {
    open: clerk?.openGoogleOneTap,
    close: clerk?.closeGoogleOneTap,
    props
  });
}, "GoogleOneTap");
withClerk(({ clerk, ...props }) => {
  return /* @__PURE__ */ jsx(Portal, {
    mount: clerk?.mountWaitlist,
    unmount: clerk?.unmountWaitlist,
    props
  });
}, "Waitlist");
withClerk(({ clerk, ...props }) => {
  return /* @__PURE__ */ jsx(Portal, {
    mount: clerk?.mountPricingTable,
    unmount: clerk?.unmountPricingTable,
    props
  });
}, "PricingTable");
withClerk(({ clerk, ...props }) => {
  return /* @__PURE__ */ jsx(Portal, {
    mount: clerk?.mountOAuthConsent,
    unmount: clerk?.unmountOAuthConsent,
    props
  });
}, "OAuthConsent");
const clerkLoaded = () => {
  return new Promise((resolve) => {
    $csrState.subscribe(({ isLoaded }) => {
      if (isLoaded) resolve($clerk.get());
    });
  });
};
const createGetToken = () => {
  return async (options) => {
    const clerk = await clerkLoaded();
    if (!clerk.session) return null;
    return clerk.session.getToken(options);
  };
};
const createSignOut = () => {
  return async (...args) => {
    return (await clerkLoaded()).signOut(...args);
  };
};
const useAuth = ({ treatPendingAsSignedOut } = {}) => {
  const authContext = useAuthStore();
  const getToken = useCallback(createGetToken(), []);
  const signOut = useCallback(createSignOut(), []);
  const { userId, orgId, orgRole, orgPermissions, factorVerificationAge, sessionClaims } = authContext;
  const has = useCallback((params) => {
    return createCheckAuthorization({
      userId,
      orgId,
      orgRole,
      orgPermissions,
      factorVerificationAge,
      features: sessionClaims?.fea || "",
      plans: sessionClaims?.pla || ""
    })(params);
  }, [
    userId,
    orgId,
    orgRole,
    orgPermissions,
    factorVerificationAge,
    sessionClaims
  ]);
  const payload = resolveAuthState({
    authObject: {
      ...authContext,
      getToken,
      signOut,
      has
    },
    options: { treatPendingAsSignedOut }
  });
  if (!payload) throw new Error("Invalid state. Feel free to submit a bug or reach out to support");
  return payload;
};
function useStore(store, getServerSnapshot) {
  const get = store.get.bind(store);
  return useSyncExternalStore(store.listen, get, getServerSnapshot || get);
}
function useAuthStore() {
  const get = $authStore.get.bind($authStore);
  return useStore($authStore, () => {
    if (typeof window === "undefined") return deriveState(false, {
      user: null,
      session: null,
      client: null,
      organization: null
    }, authAsyncStorage.getStore());
    return get();
  });
}
computed($csrState, (state) => state.isLoaded);
withClerk(({ clerk, ...handleRedirectCallbackParams }) => {
  useEffect(() => {
    clerk?.handleRedirectCallback(handleRedirectCallbackParams);
  }, []);
  return null;
}, "AuthenticateWithRedirectCallback");
const API_BASE = "http://localhost:8000";
async function authFetch(path, token, init) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...init?.headers
    }
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body || res.statusText}`);
  }
  return res.json();
}
async function createSession(token, payload = {}) {
  return authFetch("/api/v1/sessions", token, {
    method: "POST",
    body: JSON.stringify({
      buyer_agent_id: "buyer-agent-001",
      seller_agent_id: "seller-agent-001",
      provider: "mock",
      ...payload
    })
  });
}
async function listSessions(token, limit = 50, offset = 0) {
  return authFetch(
    `/api/v1/sessions?limit=${limit}&offset=${offset}`,
    token
  );
}
async function loadDemoData(token) {
  return authFetch("/api/v1/sessions/load-demo", token, {
    method: "POST"
  });
}
async function getSession(token, sessionId) {
  return authFetch(`/api/v1/sessions/${sessionId}`, token);
}
async function exportSessionPdf(token, sessionId) {
  const res = await fetch(`${API_BASE}/api/v1/sessions/${sessionId}/export`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body || res.statusText}`);
  }
  return res.blob();
}
async function getTacticsFrequency(token) {
  return authFetch("/api/v1/metrics/tactics-frequency", token);
}
async function getSessionsPerOrg(token) {
  return authFetch("/api/v1/metrics/sessions-per-org", token);
}
async function listAgentCards(token) {
  return authFetch("/api/v1/agent-cards", token);
}
async function getAverageTrust(token) {
  return authFetch("/api/v1/metrics/average-trust", token);
}
async function getSessionMessages(token, sessionId) {
  return authFetch(
    `/api/v1/sessions/${sessionId}/messages`,
    token
  );
}
async function getTrustReport(token, sessionId) {
  return authFetch(`/api/v1/sessions/${sessionId}/trust`, token);
}
async function getLedger(token, sessionId) {
  return authFetch(`/api/v1/sessions/${sessionId}/ledger`, token);
}
function getWebSocketUrl(sessionId, token) {
  const wsBase = API_BASE.replace(/^http/, "ws");
  return `${wsBase}/api/v1/sessions/${sessionId}/ws?token=${encodeURIComponent(token)}`;
}
export {
  getSessionsPerOrg as a,
  getTacticsFrequency as b,
  createSession as c,
  getWebSocketUrl as d,
  exportSessionPdf as e,
  getSession as f,
  getAverageTrust as g,
  getSessionMessages as h,
  getTrustReport as i,
  getLedger as j,
  listSessions as k,
  listAgentCards as l,
  loadDemoData as m,
  useAuth as u
};
