interface OrgTrust {
  org: string;
  score: number;
  trend: 'up' | 'down' | 'stable';
  sessions: number;
}

const MOCK: OrgTrust[] = [
  { org: 'Acme Corp', score: 88, trend: 'up', sessions: 6 },
  { org: 'Gamma Materials', score: 95, trend: 'up', sessions: 4 },
  { org: 'Delta Parts', score: 73, trend: 'stable', sessions: 3 },
  { org: 'Beta Supplies', score: 42, trend: 'down', sessions: 5 },
  { org: 'Epsilon Trade', score: 31, trend: 'down', sessions: 2 },
  { org: 'Zeta Industries', score: 67, trend: 'stable', sessions: 1 },
];

function scoreColor(s: number) {
  if (s >= 80) return 'text-gold';
  if (s >= 60) return 'text-text-primary';
  return 'text-text-muted';
}

function barColor(s: number) {
  if (s >= 80) return 'bg-gold';
  if (s >= 60) return 'bg-surface-700';
  return 'bg-surface-700/50';
}

function trendIcon(t: string) {
  switch (t) {
    case 'up': return '↑';
    case 'down': return '↓';
    default: return '→';
  }
}

function trendColor(t: string) {
  switch (t) {
    case 'up': return 'text-dot-active';
    case 'down': return 'text-dot-flagged';
    default: return 'text-text-muted';
  }
}

export default function AdminTrustPanel() {
  return (
    <div class="rounded-card border border-border bg-surface-800 px-card py-card">
      <h2 class="mb-4 text-sm font-semibold text-text-primary tracking-wide">Trust Scores by Organization</h2>
      <div class="space-y-3">
        {MOCK.map((o) => (
          <div key={o.org} class="flex items-center gap-4">
            <div class="w-28 shrink-0">
              <p class="text-xs text-text-primary truncate">{o.org}</p>
            </div>
            <div class="flex-1 h-2 rounded-full bg-surface-700/30 overflow-hidden">
              <div
                class={`h-full rounded-full transition-all duration-500 ${barColor(o.score)}`}
                style={{ width: `${o.score}%` }}
              />
            </div>
            <div class="w-16 text-right">
              <span class={`font-mono text-sm font-semibold ${scoreColor(o.score)}`}>{o.score}</span>
            </div>
            <div class={`w-6 text-center text-xs font-mono ${trendColor(o.trend)}`}>
              {trendIcon(o.trend)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
