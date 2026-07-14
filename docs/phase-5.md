# Phase 5 — Advanced Analysis 🔜 Coming

> **Deep insights** from all negotiations. Understand which strategies work, how agents perform, and export professional reports.

**📅 Status:** Planned | **🔗 Back to overview:** [PHASES.md](./PHASES.md)

---

## What It Will Do

Turn all the negotiation data into actionable intelligence:

### Analytics Features

| Feature | Description |
|---------|-------------|
| **Success Rates** | Which strategies & price ranges lead to deals |
| **Price Trends** | How prices evolve across sessions and agents |
| **Agent Performance** | Which AI providers (Gemini vs Groq) negotiate better |
| **Trust Reports** | Agent trustworthiness scores over time |
| **Comparison Views** | Side-by-side session comparisons |
| **Export** | PDF reports, CSV data dumps |

---

## How It Will Work

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  All Session │───►│  Analysis    │───►│  Reports     │
│  Data        │    │  Engine      │    │  & Export    │
└──────────────┘    └──────┬───────┘    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Dashboard   │
                    │  Insights    │
                    └──────────────┘
```

### Example Report View

```
📊 Session Summary Report
─────────────────────────
Total Sessions:    12
Successful Deals:  9 (75%)
Avg. Deal Price:   $197.50
Avg. Trust Score:  91.2

🏆 Best Performer: Gemini 2.5 Flash
   - 78% acceptance rate
   - Avg. 6.2 turns to deal
   - Trust score: 94.3

📈 Price Trend
   Starting: $240 → Closing: $197.50
   Avg. discount: 17.7%

📥 Export Options: [PDF] [CSV] [JSON]
```

---

## Planned Architecture

```
backend/app/analysis/
├── __init__.py          # Analysis exports
├── aggregator.py        # Data aggregation & statistics
├── report_generator.py  # PDF/CSV report generation
└── models.py            # Analysis result schemas

frontend/src/
└── components/
    ├── AnalyticsDashboard.jsx  # Main analytics view
    ├── SessionComparison.jsx   # Side-by-side compare
    └── ExportPanel.jsx         # Export controls
```

---

## Integration with Other Phases

- **Phase 1 (Agents):** Analyzes agent negotiation strategies
- **Phase 2 (Trust):** Reports on trust score trends
- **Phase 3 (Ledger):** Uses verified data for accurate reporting
- **Phase 4 (WebSocket):** Consumes live stream for real-time analytics
