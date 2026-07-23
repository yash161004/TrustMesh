# TrustMesh — Training Dataset Manifest (Step 1 Real Data Generation)

## Executive Summary
This manifest documents the 100-session real LLM dataset generated for training the TrustMesh Deal-Outcome Prediction Model (Roadmap Tier 1 #1).

* **Dataset Version**: `real_llm_v1`
* **Total Sessions**: 100
* **Data Origin**: 100% Live Multi-Agent LLM Negotiations (`groq/llama-3.3-70b-versatile`) with Live LLM Trust Judge evaluations (`skip_llm=False`)
* **Synthetic Data Included**: 0% (Synthetic padding skipped; dataset is 100% real)
* **Financial Cost**: $0.00 (Groq Developer Tier)
* **Generation Duration**: 531.10 seconds (~8.85 minutes)

---

## Database Target & Tagging
All sessions and evaluation records are persisted in the primary database with an explicit tag to prevent legacy data pollution:
* **Table**: `negotiation_sessions`
* **Filter Tag**: `data_source = 'real_llm_v1'`
* **Evaluated Records**: 100 total `trust_reports` records bound via `session_id`

---

## Class Outcome Breakdown

| Target Class | Count | Percentage | Primary Drivers / Scenario Types |
| :--- | :---: | :---: | :--- |
| **`DEAL`** | **42** | **42.0%** | Flexible budget overlap; mutual concession convergence |
| **`NO_DEAL`** | **42** | **42.0%** | Tight or non-overlapping budget caps vs. floor limits; buyer hard-stop walkaway |
| **`FAILED`** | **16** | **16.0%** | Live trust engine critical violations (pre-degraded reputation, severe policy cap breaches, lowball flags) |
| **TOTAL** | **100** | **100.0%** | Balanced distribution across all 3 target classes |

---

## Feature Leakage Prevention Directives (Step 2 Prep)

To guarantee model generalization and prevent shortcut learning:
1. **Agent Identifier Exclusion**: String identifiers (`buyer_agent_id`, `seller_agent_id`, `session_id`, `user_id`, `org_id`) MUST be strictly excluded from the training feature matrix.
2. **Numeric Feature Extraction Only**: Feature extraction in Step 2 will pull continuous numerical features only:
   - Initial trust scores (`buyer_trust_score`, `seller_trust_score`)
   - Reputation trend trajectory ($\Delta \text{score}$)
   - Dynamic turn metrics (`current_price_gap`, `turn_number`, `cumulative_violations`)
   - Category-level violation counts (`POLICY_DEVIATION`, `MANIPULATION`, `COMMITMENT_FLIP`)

---

## Verification & Audit Trails
- **Session ID Integrity**: Every session generated was assigned a unique UUID4 (`session_id = str(uuid4())`).
- **Fail-Fast Mock Prevention**: `session_manager.py` enforces fail-fast error checking (`ValueError`) when `data_source` starts with `"real"` and provider API keys are missing.
- **Mock Tagging**: Any sessions created in mock mode are assigned `data_source = 'mock'`.

---

## Conclusion & Recommendation
Because the 100-session live LLM batch yielded a robust 42% / 42% / 16% class distribution across all target outcomes, **synthetic data padding is unnecessary**. The model can be trained on a **100% real empirical dataset**, avoiding synthetic artifacts.
