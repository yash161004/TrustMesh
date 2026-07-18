interface Member {
  role: string;
  email: string;
  name: string;
  avatar: string;
}

const MOCK_ORG = {
  name: 'Acme Corp',
  slug: 'acme-corp',
  plan: 'Enterprise',
  created: '2025-11-01',
  members: [
    { role: 'Admin', email: 'alice@acme.dev', name: 'Alice Chen', avatar: 'AC' },
    { role: 'Admin', email: 'bob@acme.dev', name: 'Bob Gupta', avatar: 'BG' },
    { role: 'Member', email: 'carol@acme.dev', name: 'Carol Davis', avatar: 'CD' },
    { role: 'Viewer', email: 'dan@acme.dev', name: 'Dan Kim', avatar: 'DK' },
  ] satisfies Member[],
};

function Avatar({ children }: { children: string }) {
  return (
    <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-card bg-surface-700 font-mono text-[10px] font-bold text-text-secondary">
      {children}
    </span>
  );
}

export default function OrgSettings() {
  return (
    <div class="mx-auto max-w-3xl space-y-6">
      {/* Org Info */}
      <section class="rounded-card border border-border bg-surface-800 px-card py-card">
        <h2 class="mb-4 text-sm font-semibold text-text-primary tracking-wide">Organization</h2>
        <dl class="space-y-3 text-sm">
          <div class="flex items-center justify-between border-b border-border/50 pb-3">
            <dt class="text-[10px] font-medium uppercase tracking-widest text-text-muted">Name</dt>
            <dd class="font-mono text-text-primary">{MOCK_ORG.name}</dd>
          </div>
          <div class="flex items-center justify-between border-b border-border/50 pb-3">
            <dt class="text-[10px] font-medium uppercase tracking-widest text-text-muted">Slug</dt>
            <dd class="font-mono text-text-secondary">{MOCK_ORG.slug}</dd>
          </div>
          <div class="flex items-center justify-between border-b border-border/50 pb-3">
            <dt class="text-[10px] font-medium uppercase tracking-widest text-text-muted">Plan</dt>
            <dd>
              <span class="inline-flex items-center gap-1.5 rounded-full border border-gold/30 bg-gold/5 px-2.5 py-0.5 text-[10px] font-medium text-gold">
                <span class="h-1.5 w-1.5 rounded-full bg-gold" />
                {MOCK_ORG.plan}
              </span>
            </dd>
          </div>
          <div class="flex items-center justify-between">
            <dt class="text-[10px] font-medium uppercase tracking-widest text-text-muted">Created</dt>
            <dd class="font-mono text-xs text-text-secondary">{MOCK_ORG.created}</dd>
          </div>
        </dl>
      </section>

      {/* Members */}
      <section class="rounded-card border border-border bg-surface-800 px-card py-card">
        <h2 class="mb-4 text-sm font-semibold text-text-primary tracking-wide">Members</h2>
        <div class="space-y-2">
          {MOCK_ORG.members.map((m) => (
            <div key={m.email} class="flex items-center gap-3 rounded-card px-2 py-2 transition-colors duration-150 hover:bg-surface-750">
              <Avatar>{m.avatar}</Avatar>
              <div class="min-w-0 flex-1">
                <p class="text-sm text-text-primary truncate">{m.name}</p>
                <p class="text-[10px] text-text-muted truncate">{m.email}</p>
              </div>
              <span class="shrink-0 rounded-full border border-border bg-surface-700/50 px-2 py-0.5 text-[10px] font-medium text-text-secondary">
                {m.role}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
