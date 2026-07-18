interface Entry {
  seq: number;
  sender: string;
  hash: string;
  sig: string;
  broken?: boolean;
}

function truncate(h: string, n = 10) {
  if (!h) return '—';
  return h.length > n ? h.slice(0, n) + '…' : h;
}

const MOCK_ENTRIES: Entry[] = [
  { seq: 1, sender: 'buyer-agent-001', hash: 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0', sig: 'sig_a1b2c3d4e5f6a7b8c9d0e1f2a3b' },
  { seq: 2, sender: 'seller-agent-001', hash: 'b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1', sig: 'sig_b2c3d4e5f6a7b8c9d0e1f2a3b4c' },
  { seq: 3, sender: 'buyer-agent-001', hash: 'c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2', sig: 'sig_c3d4e5f6a7b8c9d0e1f2a3b4c5d', broken: true },
  { seq: 4, sender: 'seller-agent-001', hash: 'd4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3', sig: 'sig_d4e5f6a7b8c9d0e1f2a3b4c5d6e' },
];

export default function AdminLedger() {
  return (
    <div class="rounded-card border border-border bg-surface-800 px-card py-card">
      <div class="mb-4 flex items-center justify-between">
        <h2 class="text-sm font-semibold text-text-primary tracking-wide">Cryptographic Ledger</h2>
        <span class="inline-flex items-center gap-1.5 rounded-full border border-dot-flagged/30 bg-dot-flagged/10 px-2.5 py-0.5 text-[10px] font-medium text-dot-flagged">
          <span class="h-1.5 w-1.5 rounded-full bg-dot-flagged" />
          Chain Broken
        </span>
      </div>

          <div class="space-y-1">
        {MOCK_ENTRIES.map((e) => (
          <div
            key={e.seq}
            class={`grid grid-cols-[auto_1fr_auto] gap-x-2 gap-y-0.5 items-center rounded-card px-3 py-2.5 text-xs transition-colors duration-150 sm:flex sm:flex-wrap sm:items-center sm:gap-3 ${
              e.broken
                ? 'bg-dot-flagged/10 border border-dot-flagged/30'
                : 'hover:bg-surface-750'
            } ${!e.broken && e.seq < MOCK_ENTRIES.length ? 'border-b border-border/50' : ''}`}
          >
            <span class={`flex h-6 w-6 items-center justify-center rounded-card font-mono text-[10px] font-bold sm:shrink-0 ${
              e.broken ? 'bg-dot-flagged/20 text-dot-flagged' : 'bg-surface-700 text-text-secondary'
            }`}>
              {e.seq}
            </span>
            <span class={`text-[10px] font-medium sm:shrink-0 ${
              e.sender.includes('buyer') ? 'text-text-secondary' : 'text-text-muted'
            }`}>
              {e.sender}
            </span>
            <span class="col-span-2 row-start-2 font-mono text-[10px] text-text-muted sm:col-auto sm:row-auto sm:shrink-0">
              <span class="sm:hidden">{truncate(e.hash, 20)}</span>
              <span class="hidden sm:inline">{truncate(e.hash)}</span>
            </span>
            <span class="ml-auto font-mono text-[10px] text-text-muted sm:ml-0">{truncate(e.sig, 12)}</span>
            {e.broken && (
              <span class="col-span-3 mt-0.5 rounded bg-dot-flagged/15 px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wider text-dot-flagged sm:col-auto sm:mt-0">
                broken
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
