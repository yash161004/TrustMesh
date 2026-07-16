#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

# Adjust path so we can import from backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import NegotiationMessage, NegotiationScenario
from app.trust.detectors.policy import PolicyDeviationFlagger

def run_benchmark():
    scenarios_path = Path(__file__).parent.parent / "tests" / "benchmark_data" / "scenarios.json"
    with open(scenarios_path, "r") as f:
        data = json.load(f)
        
    flagger = PolicyDeviationFlagger()
    
    true_positives = 0
    false_positives = 0
    true_negatives = 0
    false_negatives = 0
    
    total_run = 0
    
    for item in data:
        cat = item["category"]
        if cat not in (0, 4):
            continue
            
        total_run += 1
        
        # Add required default fields for NegotiationScenario if missing
        constraints = item["scenario_constraints"]
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
        message = NegotiationMessage(**item["test_message"])
        
        # We only expect a flag if the expected detector is PolicyDeviationFlagger
        expected_flagged = item["expected_flagged"] and item["expected_detector"] == "PolicyDeviationFlagger"
        
        role = "buyer" if "buyer" in message.sender else "seller"
        result = flagger.evaluate(message, scenario, role)
        
        is_flagged = result["flagged"]
        
        if is_flagged and expected_flagged:
            true_positives += 1
        elif is_flagged and not expected_flagged:
            false_positives += 1
            print(f"FP: {item['name']} - Reason: {result['reason']}")
        elif not is_flagged and not expected_flagged:
            true_negatives += 1
        elif not is_flagged and expected_flagged:
            false_negatives += 1
            print(f"FN: {item['name']}")

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    print("=" * 40)
    print("PolicyDeviationFlagger Benchmark Report")
    print("=" * 40)
    print(f"Total Scenarios Run : {total_run}")
    print(f"True Positives      : {true_positives}")
    print(f"False Positives     : {false_positives}")
    print(f"True Negatives      : {true_negatives}")
    print(f"False Negatives     : {false_negatives}")
    print(f"Precision           : {precision:.2f}")
    print(f"Recall              : {recall:.2f}")
    print(f"F1 Score            : {f1:.2f}")
    print("=" * 40)
    
    if precision < 0.8 or recall < 0.8:
        print("ERROR: Precision or Recall is below 0.8!")
        sys.exit(1)
        
    print("SUCCESS: Benchmark passed.")
    sys.exit(0)

if __name__ == "__main__":
    run_benchmark()
