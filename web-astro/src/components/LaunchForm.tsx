import { useState, type FormEvent } from 'react';
import { useAuth } from '@clerk/astro/react';
import { createSession } from '../lib/api';

interface FormFields {
  counterparty: string;
  product: string;
  budgetCap: string;
  quantity: string;
}

export default function LaunchForm() {
  const { getToken } = useAuth();

  const [fields, setFields] = useState<FormFields>({
    counterparty: '',
    product: '',
    budgetCap: '500.00',
    quantity: '100',
  });

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function update<K extends keyof FormFields>(k: K, v: FormFields[K]) {
    setFields((prev) => ({ ...prev, [k]: v }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const token = await getToken();
      if (!token) throw new Error('Not authenticated');

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
    <form onSubmit={handleSubmit} class="space-y-5">
      {error && (
        <div class="rounded-card border border-dot-flagged/30 bg-dot-flagged/10 px-4 py-3 text-sm text-dot-flagged">
          {error}
        </div>
      )}

      <div>
        <label htmlFor="field-counterparty" class="mb-1.5 block text-sm font-medium text-text-primary">Counterparty</label>
        <input
          id="field-counterparty"
          value={fields.counterparty}
          onChange={(e) => update('counterparty', e.target.value)}
          placeholder="e.g. Acme Corp"
          class="w-full rounded-card border border-border bg-surface-800 px-4 py-2.5 text-sm text-text-primary placeholder:text-text-muted transition-colors duration-150 focus:border-border-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-gold/50"
        />
      </div>

      <div>
        <label htmlFor="field-product" class="mb-1.5 block text-sm font-medium text-text-primary">Product</label>
        <input
          id="field-product"
          value={fields.product}
          onChange={(e) => update('product', e.target.value)}
          placeholder="e.g. Industrial Valves"
          class="w-full rounded-card border border-border bg-surface-800 px-4 py-2.5 text-sm text-text-primary placeholder:text-text-muted transition-colors duration-150 focus:border-border-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-gold/50"
          required
        />
      </div>

      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="field-budget" class="mb-1.5 block text-sm font-medium text-text-primary">Budget Cap ($)</label>
          <input
            id="field-budget"
            type="number"
            step="0.01"
            value={fields.budgetCap}
            onChange={(e) => update('budgetCap', e.target.value)}
            class="w-full rounded-card border border-border bg-surface-800 px-4 py-2.5 text-sm text-text-primary font-mono transition-colors duration-150 focus:border-border-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-gold/50"
          />
        </div>

        <div>
          <label htmlFor="field-quantity" class="mb-1.5 block text-sm font-medium text-text-primary">Quantity</label>
          <input
            id="field-quantity"
            type="number"
            value={fields.quantity}
            onChange={(e) => update('quantity', e.target.value)}
            class="w-full rounded-card border border-border bg-surface-800 px-4 py-2.5 text-sm text-text-primary font-mono transition-colors duration-150 focus:border-border-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-gold/50"
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={submitting}
        class="rounded-card bg-gold px-5 py-2.5 text-sm font-medium text-surface-900 transition-colors duration-150 hover:bg-gold-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/50 disabled:opacity-50"
      >
        Launch Session
      </button>
    </form>
  );
}
