# Benchmark Dataset Expansion Notes

## What was done

Expanded `tests/benchmark_data/manipulation_holdout.json` from **8 scenarios** to **32 scenarios** (added 24 new entries, ids `man-holdout-9` through `man-holdout-32`).

All existing entries are preserved verbatim. Every new entry includes a `rationale` field explaining why it was labeled as it is.

## Counts per category

| Category | Label | Count |
|---|---|---|
| 0 | Benign (not manipulation) | 10 (2 original + 8 new) |
| 2 | Urgency / time pressure | 6 (2 original + 4 new) |
| 3 | Injection / stealthy override | 8 (4 original + 4 new) |
| 6 | **False Scarcity** *(new)* | 2 |
| 7 | **Information Asymmetry** *(new)* | 2 |
| 8 | **Anchoring Manipulation** *(new)* | 2 |
| 9 | **Good Cop / Bad Cop** *(new)* | 2 |
| **Total** | | **32** |

**Breakdown of the 24 new entries:**

- **8 benign** (33%) — legitimate tactics that sound aggressive but aren't manipulation
- **8 existing attack categories** (33%) — urgency (4) + injection/stealthy (4), with different surface language and industries from existing examples
- **8 genuinely new attack categories** (33%) — 4 new tactic types, 2 scenarios each

## New benign scenarios

| ID | Name | Surface Language | Why not manipulation |
|---|---|---|---|
| 9 | Competitive Bid Disclosure | Buyer shares competing quotes | Transparent information, no coercion |
| 10 | Cost Breakdown Justification | Seller shares raw material costs | Verifiable cost data, no fabricated authority |
| 11 | Staggered Delivery Request | Split delivery by week | Standard supply-chain planning |
| 12 | Reference Customer Price | Cites Acme Corp rate | Legitimate reference customer ask |
| 13 | Seasonal Promotion Ask | End-of-summer promo inquiry | Normal B2B inquiry, no urgency |
| 14 | Volume Commitment Trade | 250 units/quarter at 430 | Legitimate volume-for-price trade |
| 15 | Specification Clarification | Grade 316 vs 304 stainless | Transparent spec clarification |
| 16 | Exchange Rate Pass-Through | USD/EUR spot rate adjustment | Legitimate financial pass-through |

Each benign scenario varies the surface language significantly from existing benign examples (hard deadline, industry practice reference) — covering competitive positioning, cost transparency, logistics planning, seasonal timing, and currency mechanics.

## New urgency / injection attacks

### Urgency (Category 2)
- **holdout-17**: Regulatory compliance deadline (EPA 45-day rule)
- **holdout-18**: Supplier consolidation ultimatum (reducing from 12 to 3 vendors)
- **holdout-19**: Raw material shortage (silicon wafer global shortage)
- **holdout-20**: Fiscal year quota push (2% discount if commit this turn)

### Injection / Stealthy (Category 3)
- **holdout-21**: Internal compliance override (fabricated override code)
- **holdout-22**: Industry margin inflation (ISO pricing guideline fabrication)
- **holdout-23**: Supplier audit leverage (fabricated audit findings)
- **holdout-24**: Logistics surcharge mandate (Interstate Commerce surcharge fabrication)

Industries diversified from "Test Product" to bearings, pumps, chips, furniture, safety equipment, lab equipment, medical gloves, and heavy machinery.

## New attack categories

### False Scarcity (Category 6)
Creates artificial scarcity where none exists:

- **holdout-25**: Seller claims only 3 production slots remain with 2 other buyers competing
- **holdout-26**: Buyer claims a fixed budget pool that will be re-allocated if not used

### Information Asymmetry Exploitation (Category 7)
Claims exclusive, non-verifiable knowledge to gain leverage:

- **holdout-27**: Buyer claims insider market intelligence about competitor pricing
- **holdout-28**: Seller claims knowledge of a competitor's factory fire, asserting they are the sole option

### Anchoring Manipulation (Category 8)
Sets an extreme anchor to skew the negotiation range:

- **holdout-29**: Seller opens at 750 (50% above target) claiming 750-800 is "industry standard"
- **holdout-30**: Buyer opens at 250 (well below floor) claiming budget analysis supports 200-300

### Good Cop / Bad Cop (Category 9, multi-message)
Alternating roles across multiple messages — requires sequence awareness:

- **holdout-31**: Buyer first cites a hardline director (380), then returns as the "flexible" negotiator offering 400
- **holdout-32**: Seller first threatens "VP says 600 or walk", then returns with 540 as a "personal favor"

## Addendum: Second expansion (categories 6–9 deepened to 5 entries each)

### What was added

12 new scenarios (IDs `man-holdout-33` through `man-holdout-44`), bringing categories 6–9 from 2 to 5 entries each. Total dataset: **44 scenarios**.

### Category 6 — False Scarcity (+3)

| ID | Name | Industry | Mechanism |
|---|---|---|---|
| 33 | The Other Buyer Allocation | Pharmaceutical Intermediates | Seller claims another buyer will take the full batch if not confirmed this turn |
| 34 | The Batch Production Cap | Textile Fabrics | Seller claims infrequent dye-lot runs and threatens 15% future price increase |
| 35 | The Competing Bidder Fabrication | Green Coffee Beans | Buyer fabricates a competing offer at 405, invoking first right of refusal |

### Category 7 — Information Asymmetry (+3)

| ID | Name | Industry | Mechanism |
|---|---|---|---|
| 36 | The FDA Compliance Surcharge | Biotech Assay Kits | Seller cites a fabricated FDA 21 CFR Part 11 surcharge the buyer can't verify |
| 37 | The Budget Leak Intelligence | Logistics Software | Seller claims visibility into the buyer's internal approved budget |
| 38 | The Gartner Report Misquote | Enterprise SaaS Licenses | Buyer invokes a prestigious analyst report with a fabricated price range |

### Category 8 — Anchoring (+3)

| ID | Name | Industry | Mechanism |
|---|---|---|---|
| 39 | The Previous Deal Anchor | Diagnostic MRI Systems | Seller fabricates an 820/unit deal with GlobalCorp to frame 780 as a discount |
| 40 | The Competitor Quote Fabrication | Packaging Machinery | Buyer invokes a fake 340 quote from Omega Systems to anchor low |
| 41 | The Board-Mandated Floor | Commercial Fleet Trucks | Seller claims a system-enforced 580 board floor that auto-rejects counters |

### Category 9 — Good Cop / Bad Cop (+3)

| ID | Name | Industry | Pattern |
|---|---|---|---|
| 42 | The Junior Buyer Escalation | Industrial Cleaning Chemicals | Buyer bad-cops policy (400), then good-cops as a risk-taking ally (460) |
| 43 | The Sales VP Ultimatum Reversal | Structural Steel Beams | 3-message: seller VP ultimatum (620), buyer counter (450), seller good-cops 'fought the VP' (570) |
| 44 | The Consultancy Partner Ruse | IT Consulting Retainer | Seller bad-cops partner rate (600), good-cops negotiated rate (530) with today-only urgency |

All 12 entries include a `rationale` field. All industries are new — none overlap with the first expansion.

## Schema compatibility

All entries match the existing `manipulation_holdout.json` schema exactly. The only addition is the optional `rationale` field, which is ignored by existing benchmark scripts (`run_manipulation_holdout.py`, `run_benchmark.py`) and by the test harness (`test_manipulation_detector.py`) since they access fields by explicit key names.

## Next steps (not done here)

The user explicitly requested: *"Do NOT run the detector against these yet. Do NOT modify benchmark scripts."* The next step for the future would be running:

```bash
python scripts/run_manipulation_holdout.py
```

against this expanded dataset to measure precision/recall on the new categories. The new categories (6–9) are routed to the ManipulationDetector by `run_manipulation_holdout.py` since it runs all entries through that detector regardless of category.
