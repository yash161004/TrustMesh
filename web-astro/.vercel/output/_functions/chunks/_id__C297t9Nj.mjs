import { c as createComponent } from "./astro-component_CBpBdRmF.mjs";
import "piccolore";
import { I as renderTemplate, u as maybeRenderHead } from "./sequence_DVNL_MTV.mjs";
import { r as renderComponent } from "./entrypoint_DiKPQF1W.mjs";
import { $ as $$Layout } from "./Layout_CxVI5k03.mjs";
import { jsxs, jsx, Fragment } from "react/jsx-runtime";
import { useState, useRef, useCallback, useEffect } from "react";
import { u as useAuth, d as getWebSocketUrl, e as exportSessionPdf, f as getSession, h as getSessionMessages, i as getTrustReport, j as getLedger } from "./api_BrLtL2v5.mjs";
function getSessionIdFromUrl() {
  const match = window.location.pathname.match(/\/dashboard\/sessions\/([^/]+)/);
  return match?.[1] ?? null;
}
function severityClass(severity) {
  switch (severity) {
    case "high":
      return "border-l-dot-flagged";
    case "medium":
      return "border-l-dot-active";
    default:
      return "border-l-border";
  }
}
function messageText(msg) {
  if (msg.notes) return msg.notes;
  if (msg.delivery_terms) return msg.delivery_terms;
  return msg.message_type.replace(/_/g, " ").toLowerCase();
}
function TrustGauge({ score, label }) {
  const radius = 36;
  const strokeWidth = 8;
  const circumference = radius * Math.PI;
  const dashoffset = circumference - score / 100 * circumference;
  let color = "text-dot-flagged";
  if (score >= 75) color = "text-gold";
  else if (score >= 50) color = "text-dot-active";
  return /* @__PURE__ */ jsxs("div", { className: "flex flex-col items-center", children: [
    /* @__PURE__ */ jsx("p", { className: "text-[10px] font-medium uppercase tracking-widest text-text-muted mb-2", children: label }),
    /* @__PURE__ */ jsxs("div", { className: "relative flex items-end justify-center h-[40px]", children: [
      /* @__PURE__ */ jsxs("svg", { className: "w-[80px] h-[40px]", viewBox: "0 0 80 40", children: [
        /* @__PURE__ */ jsx("path", { d: "M 4 40 A 36 36 0 0 1 76 40", fill: "none", stroke: "currentColor", className: "text-surface-750", strokeWidth, strokeLinecap: "round" }),
        /* @__PURE__ */ jsx("path", { d: "M 4 40 A 36 36 0 0 1 76 40", fill: "none", stroke: "currentColor", className: `${color} transition-all duration-1000 ease-out`, strokeWidth, strokeLinecap: "round", strokeDasharray: circumference, strokeDashoffset: dashoffset })
      ] }),
      /* @__PURE__ */ jsx("span", { className: "absolute bottom-0 text-xl font-bold font-mono text-text-primary leading-none", children: score > 0 ? score.toFixed(0) : "—" })
    ] })
  ] });
}
function SessionView({ sessionId: propSessionId, clerkBypass } = {}) {
  const { getToken, isLoaded } = useAuth();
  const [sessionId] = useState(() => propSessionId ?? getSessionIdFromUrl());
  const [session, setSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [trust, setTrust] = useState(null);
  const [ledger, setLedger] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [wsStatus, setWsStatus] = useState("disconnected");
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);
  const unmountedRef = useRef(false);
  const sessionRef = useRef(null);
  const isTerminal = (status) => status === "COMPLETED" || status === "FAILED";
  const connectWs = useCallback(async () => {
    if (unmountedRef.current || !sessionId) return;
    const sess = sessionRef.current;
    if (sess && isTerminal(sess.status)) {
      if (!unmountedRef.current) setWsStatus("closed");
      return;
    }
    try {
      const token = clerkBypass ? "mock_token" : await getToken() || "mock_token";
      if (!token || unmountedRef.current) return;
      setWsStatus("connecting");
      const url = getWebSocketUrl(sessionId, token);
      const ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onopen = () => {
        if (!unmountedRef.current) setWsStatus("connected");
      };
      ws.onmessage = (event) => {
        if (unmountedRef.current) return;
        try {
          const data = JSON.parse(event.data);
          if (data.type === "history" && Array.isArray(data.messages)) {
            setMessages(data.messages);
          } else if (data.type === "new_message" && data.message) {
            setMessages((prev) => [...prev, data.message]);
          }
        } catch {
        }
      };
      ws.onclose = (event) => {
        if (unmountedRef.current) return;
        wsRef.current = null;
        if (event.code === 4003) {
          setWsStatus("forbidden");
          return;
        }
        const sess2 = sessionRef.current;
        if (sess2 && isTerminal(sess2.status)) {
          setWsStatus("closed");
          return;
        }
        setWsStatus("disconnected");
        reconnectTimer.current = setTimeout(connectWs, 3e3);
      };
      ws.onerror = () => {
        ws.close();
      };
    } catch {
      if (!unmountedRef.current) setWsStatus("disconnected");
    }
  }, [getToken, sessionId, clerkBypass]);
  useEffect(() => {
    unmountedRef.current = false;
    async function load() {
      if (!sessionId) {
        setError("Invalid session URL");
        setLoading(false);
        return;
      }
      try {
        const token = clerkBypass ? "mock_token" : await getToken() || "mock_token";
        if (!token || unmountedRef.current) return;
        const [sess, msgs, trustReport, ledgerReport] = await Promise.all([
          getSession(token, sessionId),
          getSessionMessages(token, sessionId).catch(() => []),
          getTrustReport(token, sessionId).catch(() => null),
          getLedger(token, sessionId).catch(() => null)
        ]);
        if (unmountedRef.current) return;
        setSession(sess);
        sessionRef.current = sess;
        setMessages(msgs);
        setTrust(trustReport);
        setLedger(ledgerReport);
      } catch (err) {
        if (!unmountedRef.current) {
          setError(err instanceof Error ? err.message : "Failed to load session");
        }
      } finally {
        if (!unmountedRef.current) setLoading(false);
      }
    }
    if (isLoaded || clerkBypass) load();
    return () => {
      unmountedRef.current = true;
    };
  }, [isLoaded, getToken, sessionId, clerkBypass]);
  useEffect(() => {
    if (!loading && session && !error) {
      connectWs();
    }
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [loading, session, error, connectWs]);
  if (loading) {
    return /* @__PURE__ */ jsxs("div", { className: "flex items-center justify-center py-20", children: [
      /* @__PURE__ */ jsxs("svg", { className: "h-6 w-6 animate-spin text-text-muted", fill: "none", viewBox: "0 0 24 24", children: [
        /* @__PURE__ */ jsx("circle", { className: "opacity-25", cx: "12", cy: "12", r: "10", stroke: "currentColor", strokeWidth: "4" }),
        /* @__PURE__ */ jsx("path", { className: "opacity-75", fill: "currentColor", d: "M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" })
      ] }),
      /* @__PURE__ */ jsx("span", { className: "ml-3 text-sm text-text-secondary", children: "Loading session…" })
    ] });
  }
  if (error || !session) {
    return /* @__PURE__ */ jsxs("div", { className: "rounded-card border border-dot-flagged/30 bg-dot-flagged/10 px-card py-16 text-center", children: [
      /* @__PURE__ */ jsx("p", { className: "text-sm text-dot-flagged", children: error ?? "Session not found" }),
      /* @__PURE__ */ jsx("a", { href: "/dashboard", className: "mt-4 inline-block text-sm text-text-secondary hover:text-text-primary transition-colors", children: "Back to Sessions" })
    ] });
  }
  const wsBadge = {
    connecting: "bg-dot-active/20 text-dot-active",
    connected: "bg-dot-completed/20 text-dot-completed",
    disconnected: "bg-surface-750 text-text-muted",
    forbidden: "bg-dot-flagged/20 text-dot-flagged",
    closed: "bg-surface-750 text-text-muted"
  }[wsStatus];
  const wsLabel = {
    connecting: "Connecting",
    connected: "Live",
    disconnected: "Disconnected",
    forbidden: "Forbidden",
    closed: "Session ended"
  }[wsStatus];
  return /* @__PURE__ */ jsxs("div", { className: "grid grid-cols-1 gap-5 lg:grid-cols-3", children: [
    /* @__PURE__ */ jsx("div", { className: "lg:col-span-2 space-y-4", children: /* @__PURE__ */ jsxs("div", { className: "rounded-card border border-border bg-surface-800 flex flex-col h-[600px]", children: [
      /* @__PURE__ */ jsxs("div", { className: "flex items-center justify-between border-b border-border px-card py-4", children: [
        /* @__PURE__ */ jsxs("div", { children: [
          /* @__PURE__ */ jsx("h1", { className: "text-sm font-semibold text-text-primary tracking-wide", children: "Transcript" }),
          /* @__PURE__ */ jsxs("p", { className: "mt-0.5 text-xs text-text-muted font-mono", children: [
            session.buyer_agent_id,
            " vs ",
            session.seller_agent_id
          ] })
        ] }),
        /* @__PURE__ */ jsxs("div", { className: "flex items-center gap-3", children: [
          /* @__PURE__ */ jsx(
            "button",
            {
              onClick: async () => {
                if (!session?.session_id) return;
                try {
                  const token = clerkBypass ? "mock_token" : await getToken() || "mock_token";
                  if (!token) ;
                  const blob = await exportSessionPdf(token, session.session_id);
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `session_${session.session_id}.pdf`;
                  document.body.appendChild(a);
                  a.click();
                  a.remove();
                  URL.revokeObjectURL(url);
                } catch (err) {
                  console.error("Failed to download PDF", err);
                }
              },
              className: "rounded bg-surface-700 px-3 py-1.5 text-[11px] font-medium text-text-primary hover:bg-surface-750 transition-colors border border-border",
              children: "Download Report"
            }
          ),
          ledger?.chain_valid && /* @__PURE__ */ jsxs("span", { className: "inline-flex items-center gap-1.5 rounded-full bg-gold/10 px-2 py-1 text-xs font-medium text-gold border border-gold/20", children: [
            /* @__PURE__ */ jsx("svg", { className: "w-3.5 h-3.5", viewBox: "0 0 20 20", fill: "currentColor", children: /* @__PURE__ */ jsx("path", { fillRule: "evenodd", d: "M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z", clipRule: "evenodd" }) }),
            "Ledger Verified"
          ] }),
          ledger && !ledger.chain_valid && /* @__PURE__ */ jsxs("span", { className: "inline-flex items-center gap-1.5 rounded-full bg-dot-flagged/10 px-2 py-1 text-xs font-medium text-dot-flagged border border-dot-flagged/20", children: [
            /* @__PURE__ */ jsx("span", { className: "h-1.5 w-1.5 rounded-full bg-dot-flagged" }),
            "Chain Broken"
          ] }),
          /* @__PURE__ */ jsx("span", { className: `rounded px-1.5 py-0.5 text-[10px] font-medium ${wsBadge}`, children: wsLabel })
        ] })
      ] }),
      /* @__PURE__ */ jsxs("div", { className: "flex-1 overflow-y-auto px-card py-card space-y-6", tabIndex: 0, children: [
        messages.length === 0 && /* @__PURE__ */ jsx("p", { className: "text-sm text-text-muted text-center py-8", children: "No messages yet. Start the session to begin negotiation." }),
        messages.map((msg) => {
          const isCurrentUser = msg.sender.includes("buyer");
          const degradedEvent = trust?.events?.find((e) => e.message_turn === msg.turn_number && e.event_type === "EVALUATION_DEGRADED");
          return /* @__PURE__ */ jsxs("div", { className: `flex flex-col ${isCurrentUser ? "items-end" : "items-start"}`, children: [
            /* @__PURE__ */ jsxs("div", { className: "mb-1 text-[11px] font-medium uppercase tracking-widest text-text-muted", children: [
              isCurrentUser ? "Buyer" : "Seller",
              " · Turn ",
              msg.turn_number
            ] }),
            /* @__PURE__ */ jsxs("div", { className: `relative max-w-[85%] rounded-2xl px-4 py-3 ${isCurrentUser ? "bg-public-brand text-surface-900 rounded-tr-sm shadow-sm" : "bg-surface-750 text-text-primary rounded-tl-sm border border-border"}`, children: [
              /* @__PURE__ */ jsx("p", { className: "text-sm leading-relaxed", children: messageText(msg) }),
              /* @__PURE__ */ jsxs("div", { className: `mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 border-t pt-2 text-[11px] font-mono ${isCurrentUser ? "border-surface-900/20 text-surface-900/80" : "border-border text-text-muted"}`, children: [
                /* @__PURE__ */ jsxs("span", { className: "font-semibold", children: [
                  "$",
                  msg.price,
                  "/unit"
                ] }),
                /* @__PURE__ */ jsx("span", { className: "hidden sm:inline", children: "·" }),
                /* @__PURE__ */ jsxs("span", { children: [
                  "Qty: ",
                  msg.quantity
                ] }),
                degradedEvent && /* @__PURE__ */ jsxs(Fragment, { children: [
                  /* @__PURE__ */ jsx("span", { className: "hidden sm:inline", children: "·" }),
                  /* @__PURE__ */ jsx("span", { className: "text-dot-active font-bold px-1.5 py-0.5 rounded bg-dot-active/10 border border-dot-active/20", title: degradedEvent.description, children: "⚠️ Verification Unavailable" })
                ] })
              ] }),
              msg.notes && msg.notes !== messageText(msg) && /* @__PURE__ */ jsxs("div", { className: `mt-2 rounded p-2.5 text-[11px] italic leading-snug ${isCurrentUser ? "bg-surface-900/10 text-surface-900/90" : "bg-surface-800 text-text-secondary"}`, children: [
                /* @__PURE__ */ jsx("span", { className: "font-semibold not-italic block mb-0.5 uppercase tracking-wider text-[9px] opacity-80", children: "Internal Thought" }),
                msg.notes
              ] })
            ] })
          ] }, msg.turn_number);
        })
      ] })
    ] }) }),
    /* @__PURE__ */ jsxs("div", { className: "space-y-4", children: [
      /* @__PURE__ */ jsxs("div", { className: "rounded-card border border-border bg-surface-800 px-card py-6", children: [
        /* @__PURE__ */ jsxs("div", { className: "flex flex-col items-center gap-6 sm:flex-row sm:justify-around", children: [
          /* @__PURE__ */ jsx(TrustGauge, { score: trust?.buyer_score?.overall_score ?? 0, label: "Buyer Trust" }),
          /* @__PURE__ */ jsx("div", { className: "hidden h-10 w-px bg-border sm:block" }),
          /* @__PURE__ */ jsx(TrustGauge, { score: trust?.seller_score?.overall_score ?? 0, label: "Seller Trust" })
        ] }),
        trust?.violations && trust.violations.length > 0 && /* @__PURE__ */ jsxs("div", { className: "mt-6 pt-5 border-t border-border", children: [
          /* @__PURE__ */ jsx("h3", { className: "mb-3 text-xs font-semibold text-text-primary tracking-wide", children: "Detected Violations" }),
          /* @__PURE__ */ jsx("div", { className: "space-y-2.5", children: trust.violations.map((v, i) => /* @__PURE__ */ jsxs("div", { className: `rounded border-l-4 bg-surface-750 px-3 py-2.5 shadow-sm ${severityClass(v.severity)}`, children: [
            /* @__PURE__ */ jsxs("div", { className: "flex items-center justify-between", children: [
              /* @__PURE__ */ jsx("p", { className: "text-[11px] font-medium text-text-muted", children: v.violation_type }),
              v.confidence_band && /* @__PURE__ */ jsx("span", { className: `px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${v.confidence_band === "high_confidence" ? "bg-dot-flagged/20 text-dot-flagged" : v.confidence_band === "moderate_confidence" ? "bg-gold/20 text-gold" : "bg-surface-600 text-text-muted"}`, children: v.confidence_band.replace(/_/g, " ") })
            ] }),
            /* @__PURE__ */ jsx("p", { className: "mt-1 text-[13px] text-text-primary leading-snug", children: v.description }),
            v.disagreement_rate != null && v.disagreement_rate > 0 && /* @__PURE__ */ jsxs("p", { className: "mt-2 text-[10px] text-text-muted/80 italic", children: [
              "Detector samples disagreed ",
              (v.disagreement_rate * 100).toFixed(0),
              "% of the time"
            ] })
          ] }, i)) })
        ] }),
        trust && trust.violations.length === 0 && /* @__PURE__ */ jsx("div", { className: "mt-6 pt-5 border-t border-border text-center", children: /* @__PURE__ */ jsx("p", { className: "text-xs text-text-secondary", children: "No violations detected" }) })
      ] }),
      /* @__PURE__ */ jsxs("div", { className: "rounded-card border border-border bg-surface-800 px-card py-card", children: [
        /* @__PURE__ */ jsx("h3", { className: "mb-3 text-xs font-semibold text-text-primary tracking-wide", children: "Session Details" }),
        /* @__PURE__ */ jsxs("dl", { className: "space-y-2.5 text-sm", children: [
          /* @__PURE__ */ jsxs("div", { className: "flex justify-between", children: [
            /* @__PURE__ */ jsx("dt", { className: "text-text-muted text-xs", children: "ID" }),
            /* @__PURE__ */ jsxs("dd", { className: "font-mono text-xs text-text-primary", children: [
              session.session_id.slice(0, 12),
              "…"
            ] })
          ] }),
          /* @__PURE__ */ jsxs("div", { className: "flex justify-between", children: [
            /* @__PURE__ */ jsx("dt", { className: "text-text-muted text-xs", children: "Status" }),
            /* @__PURE__ */ jsx("dd", { className: "text-text-primary", children: /* @__PURE__ */ jsx("span", { className: `inline-block rounded px-1.5 py-0.5 text-[10px] font-medium ${session.status === "ACTIVE" ? "bg-dot-active/20 text-dot-active" : session.status === "COMPLETED" ? "bg-dot-completed/20 text-dot-completed" : session.status === "FAILED" ? "bg-dot-flagged/20 text-dot-flagged" : "bg-surface-750 text-text-muted"}`, children: session.status }) })
          ] }),
          /* @__PURE__ */ jsxs("div", { className: "flex justify-between items-center", children: [
            /* @__PURE__ */ jsx("dt", { className: "text-text-muted text-xs", children: "Messages" }),
            /* @__PURE__ */ jsx("dd", { className: "font-mono text-text-primary", children: session.message_count })
          ] }),
          /* @__PURE__ */ jsxs("div", { className: "flex justify-between items-center", children: [
            /* @__PURE__ */ jsx("dt", { className: "text-text-muted text-xs", children: "Created" }),
            /* @__PURE__ */ jsx("dd", { className: "text-text-primary text-xs", children: new Date(session.created_at).toLocaleString() })
          ] })
        ] })
      ] }),
      ledger && /* @__PURE__ */ jsxs("div", { className: "rounded-card border border-border bg-surface-800 px-card py-card", children: [
        /* @__PURE__ */ jsxs("div", { className: "flex items-center justify-between mb-3", children: [
          /* @__PURE__ */ jsxs("h3", { className: "text-xs font-semibold text-text-primary tracking-wide", children: [
            "Ledger (",
            ledger.entries.length,
            " entries)"
          ] }),
          /* @__PURE__ */ jsx("span", { className: `inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${ledger.chain_valid ? "bg-gold/10 text-gold border border-gold/20" : "bg-dot-flagged/10 text-dot-flagged border border-dot-flagged/30"}`, children: ledger.chain_valid ? "Verified" : `Broken at entry #${ledger.broken_at ?? "?"}` })
        ] }),
        /* @__PURE__ */ jsx("div", { className: "space-y-1 max-h-[260px] overflow-y-auto", children: ledger.entries.map((e) => {
          const isBroken = ledger.broken_at != null && e.sequence >= ledger.broken_at;
          return /* @__PURE__ */ jsxs(
            "div",
            {
              className: `flex items-center gap-2 rounded px-2 py-1.5 text-[10px] font-mono ${isBroken ? "bg-dot-flagged/10 border border-dot-flagged/30" : "hover:bg-surface-750"}`,
              children: [
                /* @__PURE__ */ jsx("span", { className: `flex h-5 w-5 shrink-0 items-center justify-center rounded text-[8px] font-bold ${isBroken ? "bg-dot-flagged/20 text-dot-flagged" : "bg-surface-700 text-text-muted"}`, children: e.sequence }),
                /* @__PURE__ */ jsx("span", { className: "text-text-muted truncate max-w-[100px]", children: JSON.parse(e.message_json).sender?.includes("buyer") ? "Buyer" : "Seller" }),
                /* @__PURE__ */ jsxs("span", { className: "text-text-muted/60 truncate flex-1", children: [
                  e.entry_hash.slice(0, 12),
                  "…"
                ] }),
                isBroken && /* @__PURE__ */ jsx("span", { className: "shrink-0 rounded bg-dot-flagged/15 px-1 py-0.5 text-[8px] font-bold uppercase tracking-wider text-dot-flagged", children: "broken" })
              ]
            },
            e.sequence
          );
        }) })
      ] })
    ] })
  ] });
}
const prerender = false;
const $$id = createComponent(($$result, $$props, $$slots) => {
  const Astro2 = $$result.createAstro($$props, $$slots);
  Astro2.self = $$id;
  const { id } = Astro2.params;
  if (!id) {
    return Astro2.redirect("/dashboard");
  }
  const clerkBypass = process.env.CLERK_BYPASS === "true";
  return renderTemplate`${renderComponent($$result, "Layout", $$Layout, { "title": "Session" }, { "default": ($$result2) => renderTemplate` ${maybeRenderHead()}<main class="mx-auto max-w-6xl px-6 py-page"> <a href="/dashboard" class="mb-6 inline-block text-sm text-text-secondary transition-colors duration-150 hover:text-text-primary">
&larr; Back to Sessions
</a> ${renderComponent($$result2, "SessionView", SessionView, { "client:load": true, "sessionId": id, "clerkBypass": clerkBypass, "client:component-hydration": "load", "client:component-path": "D:/TrustMesh/TrustMesh/web-astro/src/components/SessionView", "client:component-export": "default" })} </main> ` })}`;
}, "D:/TrustMesh/TrustMesh/web-astro/src/pages/dashboard/sessions/[id].astro", void 0);
const $$file = "D:/TrustMesh/TrustMesh/web-astro/src/pages/dashboard/sessions/[id].astro";
const $$url = "/dashboard/sessions/[id]";
const _page = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  default: $$id,
  file: $$file,
  prerender,
  url: $$url
}, Symbol.toStringTag, { value: "Module" }));
const page = () => _page;
export {
  page
};
