"""
Compute Calibration Metrics (ECE / Brier Score) for the Trust Engine.

Evaluates the underlying single-judge's calibration in isolation,
separate from the live ensemble behavior, by forcing majority_vote=False.
"""
import asyncio
import json
import os
import sys
import argparse

# Add backend to path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models import NegotiationMessage, NegotiationScenario
from app.trust.detectors.manipulation import ManipulationDetector
from app.config import get_settings

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Limit number of scenarios")
    args = parser.parse_args()

    data_path = os.path.join(os.path.dirname(__file__), "..", "tests", "benchmark_data", "manipulation_holdout.json")
    with open(data_path, "r", encoding="utf-8") as f:
        scenarios = json.load(f)

    if args.limit:
        scenarios = scenarios[:args.limit]

    print(f"Calibration Anchor Enabled: {get_settings().enable_calibration_anchor}")

    detector = ManipulationDetector()
    
    y_true = []
    y_prob = []
    
    print(f"Running calibration metrics on {len(scenarios)} scenarios...")
    
    for s_data in scenarios:
        constraints = s_data["scenario_constraints"]
        defaults = {
            "product_name": "Test Product",
            "market_reference_price": 480.0,
            "buyer_target_price": 440.0,
            "seller_asking_price": 550.0,
            "delivery_preference_days": 14,
            "standard_delivery_days": 21
        }
        for k, v in defaults.items():
            if k not in constraints:
                constraints[k] = v
                
        scenario = NegotiationScenario(**constraints)
        history = [NegotiationMessage(**m) for m in s_data["message_history"]]
        msg = NegotiationMessage(**s_data["test_message"])
        expected_flagged = s_data["expected_flagged"]
        
        # NOTE: We force majority_vote=False to test the single-judge calibration in isolation
        result = await detector.evaluate(msg, history, scenario, majority_vote=False)
        await asyncio.sleep(20)  # Avoid rate limits
        
        y_true.append(1.0 if expected_flagged else 0.0)
        y_prob.append(result["confidence_score"])
        
        print(f"[{s_data['id']}] Expected: {expected_flagged}, Flagged: {result['flagged']}, Confidence: {result['confidence_score']:.2f}")

    # Compute Brier Score
    brier_score = sum((p - t) ** 2 for p, t in zip(y_prob, y_true)) / len(y_true)
    
    # Compute ECE (Expected Calibration Error) - 10 bins
    num_bins = 10
    bins = [[] for _ in range(num_bins)]
    
    for p, t in zip(y_prob, y_true):
        bin_idx = min(int(p * num_bins), num_bins - 1)
        bins[bin_idx].append((p, t))
        
    ece = 0.0
    total_samples = len(y_true)
    
    for bin_samples in bins:
        if not bin_samples:
            continue
        bin_size = len(bin_samples)
        avg_pred = sum(p for p, _ in bin_samples) / bin_size
        avg_true = sum(t for _, t in bin_samples) / bin_size
        ece += (bin_size / total_samples) * abs(avg_pred - avg_true)

    # Write output to docs/calibration_metrics.md
    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "docs", "calibration_metrics.md"))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Calibration Metrics (Manipulation Detector)\n\n")
        f.write("> **Note:** These metrics were computed on a single-call path (`majority_vote=False`) to measure the underlying judge's calibration in isolation, separate from the 2-vote live ensemble behavior. This ensures we evaluate the raw probabilistic outputs directly.\n\n")
        f.write(f"**Anchor Enabled during run:** {get_settings().enable_calibration_anchor}\n\n")
        f.write(f"**Brier Score:** {brier_score:.4f}\n\n")
        f.write(f"**Expected Calibration Error (ECE - 10 bins):** {ece:.4f}\n\n")
        f.write("### What do these mean?\n")
        f.write("- **Brier Score (0.0 to 1.0):** Measures the mean squared difference between predicted probability and the actual outcome. Lower is better. A score near 0 indicates perfect accuracy and confidence.\n")
        f.write("- **Expected Calibration Error (ECE):** Measures how well the model's stated confidence matches its actual correctness rate across different confidence levels. For example, if a model states it is 80% confident on a set of predictions, it should be correct 80% of the time. Lower ECE is better.\n")
        
    print(f"\nBrier Score: {brier_score:.4f}")
    print(f"ECE: {ece:.4f}")
    print(f"Saved results to {out_path}")

if __name__ == "__main__":
    asyncio.run(main())
