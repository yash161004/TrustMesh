#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

# Adjust path so we can import from backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import NegotiationMessage, NegotiationScenario
from app.trust.detectors.policy import PolicyDeviationFlagger
from app.trust.detectors.commitments import CommitmentConsistencyChecker
from app.trust.detectors.manipulation import ManipulationDetector

import asyncio
import argparse
import hashlib
import sys
from app.llm_client import get_llm_client

async def run_benchmark():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-cache", action="store_true", help="Disable LLM response caching")
    args = parser.parse_args()

    scenarios_path = Path(__file__).parent.parent / "tests" / "benchmark_data" / "scenarios.json"
    with open(scenarios_path, "r") as f:
        data = json.load(f)
        
    policy_flagger = PolicyDeviationFlagger()
    commit_checker = CommitmentConsistencyChecker()
    manipulation_detector = ManipulationDetector()
    
    llm = get_llm_client()
    commit_checker.llm = llm
    manipulation_detector.llm = llm
    
    if all(name.startswith("mock") for name, _ in llm.clients):
        print("ERROR: LLMClient is in mock mode (missing or placeholder API key). Aborting to prevent caching mock results.")
        sys.exit(1)
        
    cache_dir = Path(__file__).parent.parent / "tests" / "benchmark_data" / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    original_generate = llm.generate
    current_scenario_id = None
    
    provider_stats = {"cache": 0}
    
    async def cached_generate(messages: list[dict], system: str = "") -> str:
        prompt_content = json.dumps(messages)
        h = hashlib.md5(prompt_content.encode()).hexdigest()
        cache_file = cache_dir / f"{current_scenario_id}_{h}.json"
        
        if not args.no_cache and cache_file.exists():
            with open(cache_file, "r") as f:
                provider_stats["cache"] += 1
                return json.load(f)["response"]
                
        response = await original_generate(messages, system)
        with open(cache_file, "w") as f:
            json.dump({"response": response}, f)
            
        provider_used = getattr(llm, "last_used_provider", "unknown")
        provider_stats[provider_used] = provider_stats.get(provider_used, 0) + 1
        return response
        
    commit_checker.llm.generate = cached_generate
    manipulation_detector.llm.generate = cached_generate
    
    metrics = {
        "PolicyDeviationFlagger": {"TP": 0, "FP": 0, "TN": 0, "FN": 0, "Total": 0},
        "CommitmentConsistencyChecker": {"TP": 0, "FP": 0, "TN": 0, "FN": 0, "Total": 0},
        "ManipulationDetector": {"TP": 0, "FP": 0, "TN": 0, "FN": 0, "Total": 0}
    }
    
    for item in data:
        cat = item["category"]
        current_scenario_id = item.get("id", "unknown_id")
        
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
        history = [NegotiationMessage(**m) for m in item.get("message_history", [])]
        
        expected_flagged = item["expected_flagged"]
        expected_detector = item.get("expected_detector")
        role = "buyer" if "buyer" in message.sender else "seller"
        
        # PolicyDeviationFlagger
        if cat in (0, 4):
            metrics["PolicyDeviationFlagger"]["Total"] += 1
            result = policy_flagger.evaluate(message, scenario, role)
            is_flagged = result["flagged"]
            should_flag = expected_flagged and expected_detector == "PolicyDeviationFlagger"
            
            if is_flagged and should_flag:
                metrics["PolicyDeviationFlagger"]["TP"] += 1
            elif is_flagged and not should_flag:
                metrics["PolicyDeviationFlagger"]["FP"] += 1
                print(f"[Policy FP] {item['name']} - Reason: {result['reason']}")
            elif not is_flagged and not should_flag:
                metrics["PolicyDeviationFlagger"]["TN"] += 1
            elif not is_flagged and should_flag:
                metrics["PolicyDeviationFlagger"]["FN"] += 1
                print(f"[Policy FN] {item['name']}")
                
        # CommitmentConsistencyChecker
        if expected_detector == "CommitmentConsistencyChecker" or cat == 0:
            metrics["CommitmentConsistencyChecker"]["Total"] += 1
            result = await commit_checker.evaluate(message, history, scenario)
            await asyncio.sleep(2)  # Avoid rate limits
            is_flagged = result["flagged"]
            should_flag = expected_flagged and expected_detector == "CommitmentConsistencyChecker"
            
            if is_flagged and should_flag:
                metrics["CommitmentConsistencyChecker"]["TP"] += 1
            elif is_flagged and not should_flag:
                metrics["CommitmentConsistencyChecker"]["FP"] += 1
                print(f"[Commitment FP] {item['name']} - Reason: {result['reason']}")
            elif not is_flagged and not should_flag:
                metrics["CommitmentConsistencyChecker"]["TN"] += 1
            elif not is_flagged and should_flag:
                metrics["CommitmentConsistencyChecker"]["FN"] += 1
                print(f"[Commitment FN] {item['name']}")

        # ManipulationDetector
        if expected_detector == "ManipulationDetector" or cat == 0:
            metrics["ManipulationDetector"]["Total"] += 1
            result = await manipulation_detector.evaluate(message, history, scenario)
            await asyncio.sleep(2)  # Avoid rate limits
            is_flagged = result["flagged"]
            should_flag = expected_flagged and expected_detector == "ManipulationDetector"
            
            if is_flagged and should_flag:
                metrics["ManipulationDetector"]["TP"] += 1
            elif is_flagged and not should_flag:
                metrics["ManipulationDetector"]["FP"] += 1
                print(f"[Manipulation FP] {item['name']} - Reason: {result['reason']}")
            elif not is_flagged and not should_flag:
                metrics["ManipulationDetector"]["TN"] += 1
            elif not is_flagged and should_flag:
                metrics["ManipulationDetector"]["FN"] += 1
                print(f"[Manipulation FN] {item['name']}")

    failed = False
    for detector_name, m in metrics.items():
        tp, fp, tn, fn = m["TP"], m["FP"], m["TN"], m["FN"]
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        print("=" * 40)
        print(f"{detector_name} Benchmark Report")
        print("=" * 40)
        print(f"Total Scenarios Run : {m['Total']}")
        print(f"True Positives      : {tp}")
        print(f"False Positives     : {fp}")
        print(f"True Negatives      : {tn}")
        print(f"False Negatives     : {fn}")
        print(f"Precision           : {precision:.2f}")
        print(f"Recall              : {recall:.2f}")
        print(f"F1 Score            : {f1:.2f}")
        print("=" * 40)
        
        if precision < 0.8 or recall < 0.8:
            print(f"ERROR: {detector_name} Precision or Recall is below 0.8!")
            failed = True
            
    print("=" * 40)
    print("LLM Provider Usage Summary")
    print("=" * 40)
    total_calls = sum(provider_stats.values())
    print(f"Total LLM calls: {total_calls}")
    for provider, count in provider_stats.items():
        if provider == "cache":
            print(f"  - from {provider}: {count}")
        else:
            print(f"  - via {provider} (live): {count}")
    print("=" * 40)
            
    if failed:
        sys.exit(1)
        
    print("SUCCESS: Benchmark passed.")
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
