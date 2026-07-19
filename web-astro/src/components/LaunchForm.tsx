import { useState, type FormEvent } from 'react';
import { useAuth } from '@clerk/astro/react';
import { createSession } from '../lib/api';

interface FormFields {
  counterparty: string;
  product: string;
  budgetCap: string;
  quantity: string;
}

function FormIcon({ type }: { type: 'building' | 'cube' | 'currency' | 'hashtag' }) {
  const icons = {
    building: <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21" />,
    cube: <path stroke-linecap="round" stroke-linejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />,
    currency: <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />,
    hashtag: <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 8.25h15m-16.5 7.5h15m-1.8-13.5l-3.9 19.5m-2.1-19.5l-3.9 19.5" />
  };
  return (
    <svg class="h-4 w-4 text-text-muted absolute left-3.5 top-1/2 -translate-y-1/2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
      {icons[type]}
    </svg>
  );
}

interface Props {
  clerkBypass?: boolean;
}

export default function LaunchForm({ clerkBypass }: Props = {}) {
  const { getToken } = useAuth();

  const [fields, setFields] = useState<FormFields>({
    counterparty: 'Acme Corp',
    product: 'Industrial Valves',
    budgetCap: '500.00',
    quantity: '100',
  });

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  function update<K extends keyof FormFields>(k: K, v: FormFields[K]) {
    setFields((prev) => ({ ...prev, [k]: v }));
  }

  function handleBlur(field: keyof FormFields) {
    setTouched((prev) => ({ ...prev, [field]: true }));
  }

  const isInvalid = (field: keyof FormFields) => touched[field] && !fields[field];

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const token = clerkBypass ? "mock_token" : (await getToken() || "mock_token");

      const result = await createSession(token, {
        buyer_agent_id: 'buyer-agent-001',
        seller_agent_id: 'seller-agent-001',
        provider: 'mock',
        scenario: {
          product_name: fields.product || 'Office chairs',
          quantity: parseInt(fields.quantity, 10) || 100,
          market_reference_price: parseFloat(fields.budgetCap) || 500,
          buyer_budget_cap: parseFloat(fields.budgetCap) || 500,
          buyer_target_price: (parseFloat(fields.budgetCap) || 500) * 0.88,
          seller_floor_price: (parseFloat(fields.budgetCap) || 500) * 0.84,
          seller_asking_price: (parseFloat(fields.budgetCap) || 500) * 1.1,
          delivery_preference_days: 14,
          standard_delivery_days: 21,
        },
      });

      window.location.href = `/dashboard/sessions/${result.session_id}`;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create session');
      setSubmitting(false);
    }
  }

  if (submitting) {
    return (
      <div class="rounded-card border border-border bg-surface-800 px-card py-16 text-center">
        <div class="mb-3 mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-surface-750">
          <svg class="h-6 w-6 animate-spin text-gold" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
        <p class="text-base font-medium text-text-primary">Creating session…</p>
        <p class="mt-1 text-sm text-text-secondary">Connecting to backend</p>
      </div>
    );
  }

  return (
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
      <form onSubmit={handleSubmit} class="space-y-5 lg:col-span-2">
        {error && (
          <div class="rounded-card border border-dot-flagged/30 bg-dot-flagged/10 px-4 py-3 text-sm text-dot-flagged flex items-center gap-2">
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            {error}
          </div>
        )}

        <div>
          <label htmlFor="field-counterparty" class="mb-1.5 block text-[13px] font-semibold text-text-primary tracking-wide">Counterparty</label>
          <div class="relative">
            <FormIcon type="building" />
            <input
              id="field-counterparty"
              value={fields.counterparty}
              onBlur={() => handleBlur('counterparty')}
              onChange={(e) => update('counterparty', e.target.value)}
              placeholder="e.g. Acme Corp"
              class={`w-full rounded-card border bg-surface-800 pl-10 pr-4 py-2.5 text-sm text-text-primary placeholder:text-text-muted transition-colors duration-150 focus:outline-none focus-visible:ring-2 ${
                isInvalid('counterparty') 
                  ? 'border-dot-flagged focus-visible:ring-dot-flagged/30' 
                  : 'border-border focus:border-border-hover focus-visible:ring-gold/50'
              }`}
            />
          </div>
          {isInvalid('counterparty') && <p class="mt-1 text-[11px] text-dot-flagged">Counterparty is required.</p>}
        </div>

        <div>
          <label htmlFor="field-product" class="mb-1.5 block text-[13px] font-semibold text-text-primary tracking-wide">Product</label>
          <div class="relative">
            <FormIcon type="cube" />
            <input
              id="field-product"
              value={fields.product}
              onBlur={() => handleBlur('product')}
              onChange={(e) => update('product', e.target.value)}
              placeholder="e.g. Industrial Valves"
              class={`w-full rounded-card border bg-surface-800 pl-10 pr-4 py-2.5 text-sm text-text-primary placeholder:text-text-muted transition-colors duration-150 focus:outline-none focus-visible:ring-2 ${
                isInvalid('product') 
                  ? 'border-dot-flagged focus-visible:ring-dot-flagged/30' 
                  : 'border-border focus:border-border-hover focus-visible:ring-gold/50'
              }`}
            />
          </div>
          {isInvalid('product') && <p class="mt-1 text-[11px] text-dot-flagged">Product is required.</p>}
        </div>

        <div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <div>
            <label htmlFor="field-budget" class="mb-1.5 block text-[13px] font-semibold text-text-primary tracking-wide">Budget Cap ($)</label>
            <div class="relative">
              <FormIcon type="currency" />
              <input
                id="field-budget"
                type="number"
                step="0.01"
                value={fields.budgetCap}
                onBlur={() => handleBlur('budgetCap')}
                onChange={(e) => update('budgetCap', e.target.value)}
                class={`w-full rounded-card border bg-surface-800 pl-10 pr-4 py-2.5 text-sm text-text-primary font-mono transition-colors duration-150 focus:outline-none focus-visible:ring-2 ${
                  isInvalid('budgetCap') || parseFloat(fields.budgetCap) <= 0 
                    ? 'border-dot-flagged focus-visible:ring-dot-flagged/30' 
                    : 'border-border focus:border-border-hover focus-visible:ring-gold/50'
                }`}
              />
            </div>
            {(isInvalid('budgetCap') || parseFloat(fields.budgetCap) <= 0) && touched.budgetCap && <p class="mt-1 text-[11px] text-dot-flagged">Enter a valid budget.</p>}
          </div>

          <div>
            <label htmlFor="field-quantity" class="mb-1.5 block text-[13px] font-semibold text-text-primary tracking-wide">Quantity</label>
            <div class="relative">
              <FormIcon type="hashtag" />
              <input
                id="field-quantity"
                type="number"
                value={fields.quantity}
                onBlur={() => handleBlur('quantity')}
                onChange={(e) => update('quantity', e.target.value)}
                class={`w-full rounded-card border bg-surface-800 pl-10 pr-4 py-2.5 text-sm text-text-primary font-mono transition-colors duration-150 focus:outline-none focus-visible:ring-2 ${
                  isInvalid('quantity') || parseInt(fields.quantity, 10) < 1
                    ? 'border-dot-flagged focus-visible:ring-dot-flagged/30' 
                    : 'border-border focus:border-border-hover focus-visible:ring-gold/50'
                }`}
              />
            </div>
            {(isInvalid('quantity') || parseInt(fields.quantity, 10) < 1) && touched.quantity && <p class="mt-1 text-[11px] text-dot-flagged">Quantity must be at least 1.</p>}
          </div>
        </div>

        <button
          type="submit"
          disabled={submitting}
          class="rounded-card bg-gold px-5 py-2.5 text-sm font-medium text-surface-900 transition-all duration-150 hover:bg-gold-hover hover:shadow-lg hover:shadow-gold/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/50 disabled:opacity-50"
        >
          Launch Session
        </button>
      </form>
      
      {/* Mini Preview Panel */}
      <div class="rounded-card border border-border bg-surface-800 p-5 hidden lg:block">
        <h3 class="mb-4 text-xs font-semibold uppercase tracking-widest text-text-muted">Negotiation Envelope</h3>
        <dl class="space-y-3 text-sm">
          <div class="flex justify-between items-center pb-3 border-b border-border/50">
            <dt class="text-text-secondary text-xs">Total Target Value</dt>
            <dd class="font-mono text-gold font-medium">
              ${(parseFloat(fields.budgetCap || '0') * parseInt(fields.quantity || '0', 10)).toLocaleString()}
            </dd>
          </div>
          <div class="flex justify-between items-center">
            <dt class="text-text-secondary text-xs">Buyer Target Price</dt>
            <dd class="font-mono text-text-primary">
              ${(parseFloat(fields.budgetCap || '0') * 0.88).toFixed(2)}
            </dd>
          </div>
          <div class="flex justify-between items-center">
            <dt class="text-text-secondary text-xs">Seller Floor Price</dt>
            <dd class="font-mono text-text-muted">
              ${(parseFloat(fields.budgetCap || '0') * 0.84).toFixed(2)}
            </dd>
          </div>
          <div class="flex justify-between items-center">
            <dt class="text-text-secondary text-xs">Seller Ask Price</dt>
            <dd class="font-mono text-text-muted">
              ${(parseFloat(fields.budgetCap || '0') * 1.1).toFixed(2)}
            </dd>
          </div>
        </dl>
      </div>
    </div>
  );
}
