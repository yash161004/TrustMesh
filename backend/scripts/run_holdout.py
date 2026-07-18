#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import NegotiationMessage, NegotiationScenario
from app.trust.detectors.commitments import CommitmentConsistencyChecker

import asyncio
import argparse
import hashlib
import sys
from app.llm_client import get_llm_client

async def run_holdout():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-cache", action="store_true", help="Disable LLM response caching")
    args = parser.parse_args()

    scenarios_path = Path(__file__).parent.parent / "tests" / "benchmark_data" / "holdout_scenarios.json"
    with open(scenarios_path, "r") as f:
        data = json.load(f)
        
    commit_checker = CommitmentConsistencyChecker()
    commit_checker.llm = get_llm_client(provider="groq")
    
    if not getattr(commit_checker.llm, "api_key", None):
        print("ERROR: LLMClient is in mock mode (missing or placeholder API key). Aborting to prevent caching mock results.")
        sys.exit(1)
        
    cache_dir = Path(__file__).parent.parent / "tests" / "benchmark_data" / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    original_generate = commit_checker.llm.generate
    current_scenario_id = None
    
    async def cached_generate(messages: list[dict], system: str = "") -> str:
        prompt_content = json.dumps(messages)
        h = hashlib.md5(prompt_content.encode()).hexdigest()
        cache_file = cache_dir / f"{current_scenario_id}_{h}.json"
        
        if not args.no_cache and cache_file.exists():
            with open(cache_file, "r") as f:
                return json.load(f)["response"]
                
        response = await original_generate(messages, system)
        with open(cache_file, "w") as f:
            json.dump({"response": response}, f)
        return response
        
    commit_checker.llm.generate = cached_generate
    
    tp, fp, tn, fn, total = 0, 0, 0, 0, 0
    
    for item in data:
        total += 1
        current_scenario_id = item.get("id", "unknown_id")
        
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
        history = [NegotiationMessage(**m) for m in item.get("message_history", [])]
        
        expected_flagged = item["expected_flagged"]
        
        result = await commit_checker.evaluate(message, history, scenario)
        await asyncio.sleep(2)  # Avoid rate limits
        is_flagged = result["flagged"]
        
        if is_flagged and expected_flagged:
            tp += 1
        elif is_flagged and not expected_flagged:
            fp += 1
            print(f"[FP] {item['name']} - Reason: {result['reason']}")
        elif not is_flagged and not expected_flagged:
            tn += 1
        elif not is_flagged and expected_flagged:
            fn += 1
            print(f"[FN] {item['name']}")

    if (tp + fp) > 0:
        precision_val = tp / (tp + fp)
        precision_str = f"{precision_val:.2f}"
    else:
        precision_str = "N/A"
    
    if (tp + fn) > 0:
        recall_val = tp / (tp + fn)
        recall_str = f"{recall_val:.2f}"
    else:
        recall_str = "N/A"
    
    if precision_str != "N/A" and recall_str != "N/A":
        denom = precision_val + recall_val
        f1_val = 2 * (precision_val * recall_val) / denom if denom > 0 else 0.0
        f1_str = f"{f1_val:.2f}"
    else:
        f1_str = "N/A"
    
    print("=" * 40)
    print("CommitmentConsistencyChecker Holdout Report")
    print("=" * 40)
    print(f"Total Scenarios Run : {total}")
    print(f"True Positives      : {tp}")
    print(f"False Positives     : {fp}")
    print(f"True Negatives      : {tn}")
    print(f"False Negatives     : {fn}")
    print(f"Precision           : {precision_str}")
    print(f"Recall              : {recall_str}")
    print(f"F1 Score            : {f1_str}")
    if (tp + fn) == 0:
        print(f"  ^ Precision/Recall/F1 are N/A because no positive ground-truth cases exist in this holdout set.")
    elif (tp + fp) == 0:
        print(f"  ^ Precision is N/A because the detector made no positive predictions. Recall is {recall_str}.")
    print("=" * 40)

if __name__ == "__main__":
    asyncio.run(run_holdout())
