import { afterEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';

afterEach(cleanup);

import AdminStats from '../components/AdminStats';
import AdminViolations from '../components/AdminViolations';
import AdminTrustPanel from '../components/AdminTrustPanel';
import AdminLedger from '../components/AdminLedger';
import OrgSettings from '../components/OrgSettings';
import SessionList from '../components/SessionList';
import LaunchForm from '../components/LaunchForm';
import SessionView from '../components/SessionView';

const mockSessions = [
  { session_id: 'sess-001', buyer_agent_id: 'buyer-agent-001', seller_agent_id: 'Acme Corp', status: 'ACTIVE', created_at: '2026-07-18T10:30:00Z', message_count: 5 },
  { session_id: 'sess-002', buyer_agent_id: 'buyer-agent-001', seller_agent_id: 'Beta Supplies', status: 'FAILED', created_at: '2026-07-18T09:15:00Z', message_count: 3 },
  { session_id: 'sess-003', buyer_agent_id: 'buyer-agent-001', seller_agent_id: 'Gamma Materials', status: 'COMPLETED', created_at: '2026-07-17T16:45:00Z', message_count: 8 },
];

const mockMessages = [
  { message_type: 'OFFER', sender: 'buyer-agent-001', price: 450, quantity: 100, delivery_terms: 'Net-30', timestamp: '2026-07-18T09:00:00Z', turn_number: 1, notes: null, session_id: 'sess-002', signature: null, signer_public_key: null },
  { message_type: 'COUNTER_OFFER', sender: 'seller-agent-001', price: 480, quantity: 100, delivery_terms: 'Net-30', timestamp: '2026-07-18T09:01:00Z', turn_number: 2, notes: 'Standard rate', session_id: 'sess-002', signature: null, signer_public_key: null },
];

const mockSession = mockSessions[1];

const mockTrust = {
  session_id: 'sess-002',
  evaluated_at: '2026-07-18T09:15:00Z',
  buyer_score: { agent_id: 'buyer-agent-001', overall_score: 42, violation_count: 1, recent_trend: 'declining' },
  seller_score: { agent_id: 'seller-agent-001', overall_score: 88, violation_count: 0, recent_trend: 'stable' },
  violations: [{ violation_type: 'MANIPULATION', severity: 'high', message_turn: 2, agent_id: 'seller-agent-001', description: 'Fabricated competition', status: 'confirmed', detail: null, confidence_band: 'high_confidence', disagreement_rate: 0.33 }],
  events: [{ event_type: 'EVALUATION_DEGRADED', message_turn: 1, agent_id: 'buyer-agent-001', description: 'Rate limit' }],
  summary: 'Violation detected',
};

describe('Phase 4 island components', () => {
  test('AdminStats renders stat cards', () => {
    const { container } = render(<AdminStats />);
    expect(container.querySelectorAll('.rounded-card').length).toBe(4);
  });

  test('AdminViolations renders violation table', () => {
    render(<AdminViolations />);
    expect(screen.getByText('Recent Violations')).toBeInTheDocument();
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.getByText('Epsilon Trade')).toBeInTheDocument();
  });

  test('AdminTrustPanel renders trust bars', () => {
    render(<AdminTrustPanel />);
    expect(screen.getByText('Trust Scores by Organization')).toBeInTheDocument();
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.getByText('Zeta Industries')).toBeInTheDocument();
  });

  test('AdminLedger renders ledger entries', () => {
    render(<AdminLedger />);
    expect(screen.getByText('Cryptographic Ledger')).toBeInTheDocument();
    expect(screen.getByText('Chain Broken')).toBeInTheDocument();
  });

  test('OrgSettings renders org info and members', () => {
    render(<OrgSettings />);
    expect(screen.getByText('Organization')).toBeInTheDocument();
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.getByText('Members')).toBeInTheDocument();
    expect(screen.getByText('Alice Chen')).toBeInTheDocument();
    expect(screen.getByText('Dan Kim')).toBeInTheDocument();
  });

  test('SessionList renders session items after loading', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => mockSessions,
    } as Response);

    render(<SessionList />);
    await waitFor(() => {
      expect(screen.getByText(/Acme Corp/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Gamma Materials/)).toBeInTheDocument();
    expect(screen.getByText(/Beta Supplies/)).toBeInTheDocument();
    vi.restoreAllMocks();
  });

  test('SessionList shows empty state when no sessions', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    } as Response);

    render(<SessionList />);
    await waitFor(() => {
      expect(screen.getByText('No sessions yet')).toBeInTheDocument();
    });
    vi.restoreAllMocks();
  });

  test('LaunchForm renders form fields and submit button', () => {
    render(<LaunchForm />);
    expect(screen.getByLabelText('Counterparty')).toBeInTheDocument();
    expect(screen.getByLabelText('Product')).toBeInTheDocument();
    expect(screen.getByLabelText('Budget Cap ($)')).toBeInTheDocument();
    expect(screen.getByLabelText('Quantity')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Launch Session' })).toBeInTheDocument();
  });

  test('SessionView renders transcript and sidebar after loading', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({ ok: true, json: async () => mockSession } as Response)
      .mockResolvedValueOnce({ ok: true, json: async () => mockMessages } as Response)
      .mockResolvedValueOnce({ ok: true, json: async () => mockTrust } as Response);

    render(<SessionView sessionId="sess-002" />);
    await waitFor(() => {
      expect(screen.getByText('Transcript')).toBeInTheDocument();
    });
    expect(screen.getAllByText(/Buyer/)[0]).toBeInTheDocument();
    expect(screen.getByText(/Detected Violations/i)).toBeInTheDocument();
    expect(screen.getByText('⚠️ Verification Unavailable')).toBeInTheDocument();
    expect(screen.getByText('high confidence')).toBeInTheDocument();
    expect(screen.getByText('Detector samples disagreed 33% of the time')).toBeInTheDocument();
    vi.restoreAllMocks();
  });
});
