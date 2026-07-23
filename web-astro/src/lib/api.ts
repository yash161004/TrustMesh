const API_BASE = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';

export interface SessionResponse {
  session_id: string;
  buyer_agent_id: string;
  seller_agent_id: string;
  buyer_identity_id: string | null;
  seller_identity_id: string | null;
  status: string;
  created_at: string;
  message_count: number;
}

export interface NegotiationMessage {
  message_type: string;
  sender: string;
  price: number;
  quantity: number;
  delivery_terms: string;
  timestamp: string;
  turn_number: number;
  notes: string | null;
  session_id: string | null;
  signature: string | null;
  signer_public_key: string | null;
}

export interface AgentCardResponse {
  agent_id: string;
  role: string;
  display_name: string;
  capabilities: string[];
  public_key: string;
  created_at: string;
  version: string;
  is_verified: boolean;
  signature: string;
}

export interface LedgerEntry {
  id: number;
  session_id: string;
  sequence: number;
  message_json: string;
  signature: string;
  signer_public_key: string;
  prev_hash: string;
  entry_hash: string;
  created_at: string;
}

export interface LedgerResponse {
  session_id: string;
  entries: LedgerEntry[];
  chain_valid: boolean;
  broken_at: number | null;
}

export interface TrustScore {
  agent_id: string;
  overall_score: number;
  violation_count: number;
  recent_trend: string;
}

export interface TacticFrequency {
  tactic_name: string;
  frequency: number;
}

export interface SessionsPerOrg {
  org_id: string;
  session_count: number;
}

export interface AverageTrust {
  average_trust_score: number;
}

export interface Violation {
  violation_type: string;
  severity: string;
  message_turn: number;
  agent_id: string;
  description: string;
  status: string;
  detail: string | null;
  confidence_band?: string | null;
  disagreement_rate?: number | null;
}

export interface SessionEvent {
  event_type: string;
  message_turn: number;
  agent_id: string;
  description: string;
}

export interface TrustReport {
  session_id: string;
  evaluated_at: string;
  buyer_score: TrustScore;
  seller_score: TrustScore;
  violations: Violation[];
  events?: SessionEvent[];
  summary: string;
}

export interface CreateSessionPayload {
  buyer_agent_id?: string;
  seller_agent_id?: string;
  provider?: string;
  scenario?: {
    product_name: string;
    quantity: number;
    currency?: string;
    market_reference_price: number;
    buyer_budget_cap: number;
    buyer_target_price: number;
    seller_floor_price: number;
    seller_asking_price: number;
    delivery_preference_days: number;
    standard_delivery_days: number;
    expedited_delivery_days?: number;
    expedited_premium_per_unit?: number;
  };
}

async function authFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`API ${res.status}: ${body || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function createSession(
  token: string,
  payload: CreateSessionPayload = {},
): Promise<SessionResponse> {
  return authFetch<SessionResponse>('/api/v1/sessions', token, {
    method: 'POST',
    body: JSON.stringify({
      buyer_agent_id: 'buyer-agent-001',
      seller_agent_id: 'seller-agent-001',
      provider: 'mock',
      ...payload,
    }),
  });
}

export async function listSessions(
  token: string,
  limit = 50,
  offset = 0,
): Promise<SessionResponse[]> {
  return authFetch<SessionResponse[]>(
    `/api/v1/sessions?limit=${limit}&offset=${offset}`,
    token,
  );
}

export async function loadDemoData(token: string): Promise<{ status: string }> {
  return authFetch<{ status: string }>('/api/v1/sessions/load-demo', token, {
    method: 'POST',
  });
}

export async function getSession(
  token: string,
  sessionId: string,
): Promise<SessionResponse> {
  return authFetch<SessionResponse>(`/api/v1/sessions/${sessionId}`, token);
}

export async function exportSessionPdf(
  token: string,
  sessionId: string,
): Promise<Blob> {
  const res = await fetch(`${API_BASE}/api/v1/sessions/${sessionId}/export`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`API ${res.status}: ${body || res.statusText}`);
  }
  return res.blob();
}

export async function getTacticsFrequency(token: string): Promise<TacticFrequency[]> {
  return authFetch<TacticFrequency[]>('/api/v1/metrics/tactics-frequency', token);
}

export async function getSessionsPerOrg(token: string): Promise<SessionsPerOrg[]> {
  return authFetch<SessionsPerOrg[]>('/api/v1/metrics/sessions-per-org', token);
}

export async function listAgentCards(token: string): Promise<AgentCardResponse[]> {
  return authFetch<AgentCardResponse[]>('/api/v1/agent-cards', token);
}

export async function getAverageTrust(token: string): Promise<AverageTrust> {
  return authFetch<AverageTrust>('/api/v1/metrics/average-trust', token);
}

export async function getSessionMessages(
  token: string,
  sessionId: string,
): Promise<NegotiationMessage[]> {
  return authFetch<NegotiationMessage[]>(
    `/api/v1/sessions/${sessionId}/messages`,
    token,
  );
}

export async function getTrustReport(
  token: string,
  sessionId: string,
): Promise<TrustReport> {
  return authFetch<TrustReport>(`/api/v1/sessions/${sessionId}/trust`, token);
}

export async function getLedger(
  token: string,
  sessionId: string,
): Promise<LedgerResponse> {
  return authFetch<LedgerResponse>(`/api/v1/sessions/${sessionId}/ledger`, token);
}

export async function startSession(
  token: string,
  sessionId: string,
): Promise<{ status: string; session_id: string }> {
  return authFetch(`/api/v1/sessions/${sessionId}/start`, token, {
    method: 'POST',
  });
}

export async function processTurn(
  token: string,
  sessionId: string,
  maxTurns = 5,
): Promise<{ status: string; session_id: string }> {
  return authFetch(`/api/v1/sessions/${sessionId}/turn`, token, {
    method: 'POST',
    body: JSON.stringify({ max_turns: maxTurns }),
  });
}

export function getWebSocketUrl(sessionId: string, token: string): string {
  const wsBase = API_BASE.replace(/^http/, 'ws');
  return `${wsBase}/api/v1/sessions/${sessionId}/ws?token=${encodeURIComponent(token)}`;
}
