interface Stat {
  label: string;
  value: string;
  sub: string;
}

const MOCK_STATS: Stat[] = [
  { label: 'Organizations', value: '12', sub: 'across 3 tiers' },
  { label: 'Active Sessions', value: '24', sub: '14 in last hour' },
  { label: 'Violations (today)', value: '7', sub: '3 critical' },
  { label: 'Avg Trust Score', value: '71', sub: '+5 vs yesterday' },
];

export default function AdminStats() {
  return (
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
      {MOCK_STATS.map((s) => (
        <div key={s.label} class="rounded-card border border-border bg-surface-800 px-card py-card">
          <p class="text-[10px] font-medium uppercase tracking-widest text-text-muted">{s.label}</p>
          <p class="mt-1.5 font-mono text-2xl font-bold text-text-primary">{s.value}</p>
          <p class="mt-0.5 text-xs text-text-secondary">{s.sub}</p>
        </div>
      ))}
    </div>
  );
}
