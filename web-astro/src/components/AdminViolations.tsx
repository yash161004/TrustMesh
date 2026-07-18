interface Violation {
  id: string;
  org: string;
  session: string;
  detector: string;
  type: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  turn: number;
  description: string;
  timestamp: string;
}

const SEV_DOT: Record<string, string> = {
  critical: 'bg-dot-flagged',
  high: 'bg-dot-flagged',
  medium: 'bg-dot-active',
  low: 'bg-dot-completed',
};

const MOCK: Violation[] = [
  { id: 'v-001', org: 'Acme Corp', session: 'sess-001', detector: 'PolicyDeviationFlagger', type: 'Budget Override', severity: 'critical', turn: 4, description: 'Offer exceeded buyer budget cap of $500 by $120.', timestamp: '2026-07-18T10:32:00Z' },
  { id: 'v-002', org: 'Beta Supplies', session: 'sess-002', detector: 'ManipulationDetector', type: 'Fabricated Scarcity', severity: 'high', turn: 3, description: 'Seller claimed competing buyers to pressure acceptance.', timestamp: '2026-07-18T09:18:00Z' },
  { id: 'v-003', org: 'Gamma Materials', session: 'sess-003', detector: 'CommitmentConsistencyChecker', type: 'Bait & Switch', severity: 'medium', turn: 5, description: 'Delivery terms changed from 10 to 30 days at acceptance.', timestamp: '2026-07-17T17:02:00Z' },
  { id: 'v-004', org: 'Delta Parts', session: 'sess-004', detector: 'ManipulationDetector', type: 'Authority Fabrication', severity: 'high', turn: 1, description: 'Buyer cited non-existent board resolution to cap price.', timestamp: '2026-07-17T14:25:00Z' },
  { id: 'v-005', org: 'Epsilon Trade', session: 'sess-005', detector: 'PolicyDeviationFlagger', type: 'Quantity Trick', severity: 'low', turn: 2, description: 'Volume discount requested at 10000 units (100x standard).', timestamp: '2026-07-16T11:05:00Z' },
];

export default function AdminViolations() {
  return (
    <div class="rounded-card border border-border bg-surface-800 px-card py-card">
      <h2 class="mb-4 text-sm font-semibold text-text-primary tracking-wide">Recent Violations</h2>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead>
            <tr class="border-b border-border text-[10px] font-medium uppercase tracking-widest text-text-muted">
              <th class="pb-2 pr-4">Org</th>
              <th class="pb-2 pr-4">Detector</th>
              <th class="pb-2 pr-4">Type</th>
              <th class="pb-2 pr-4">Sev</th>
              <th class="pb-2 pr-4">Description</th>
              <th class="pb-2 text-right">Time</th>
            </tr>
          </thead>
          <tbody>
            {MOCK.map((v) => (
              <tr key={v.id} class="border-b border-border/50 last:border-0 transition-colors duration-150 hover:bg-surface-750">
                <td class="py-2.5 pr-4">
                  <span class="text-sm text-text-primary">{v.org}</span>
                  <p class="text-[10px] font-mono text-text-muted">{v.session}</p>
                </td>
                <td class="py-2.5 pr-4 text-xs text-text-secondary">{v.detector}</td>
                <td class="py-2.5 pr-4 text-xs text-text-primary">{v.type}</td>
                <td class="py-2.5 pr-4">
                  <span class="flex items-center gap-1.5 text-xs text-text-secondary">
                    <span class={`h-1.5 w-1.5 rounded-full ${SEV_DOT[v.severity]}`} />
                    {v.severity}
                  </span>
                </td>
                <td class="py-2.5 pr-4 text-xs text-text-secondary max-w-[240px] truncate">{v.description}</td>
                <td class="py-2.5 text-right font-mono text-[11px] text-text-muted whitespace-nowrap">{v.timestamp.slice(11, 16)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
