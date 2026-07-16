#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import NegotiationMessage, NegotiationScenario
from app.trust.detectors.manipulation import ManipulationDetector
import asyncio
import argparse
import hashlib
from app.llm_client import get_llm_client

async def run_holdout():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-cache", action="store_true", help="Disable LLM response caching")
    args = parser.parse_args()

    scenarios_path = Path(__file__).parent.parent / "tests" / "benchmark_data" / "manipulation_holdout.json"
    with open(scenarios_path, "r") as f:
        data = json.load(f)
        
    detector = ManipulationDetector()
    llm = get_llm_client()
    detector.llm = llm
    
    if all(name.startswith("mock") for name, _ in llm.clients):
        print("ERROR: LLMClient is in mock mode (missing or placeholder API key). Aborting.")
        sys.exit(1)
        
    cache_dir = Path(__file__).parent.parent / "tests" / "benchmark_data" / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    original_generate = llm.generate
    current_scenario_id = None
    
    provider_stats = {"cache": 0}
    
    async def cached_generate(messages: list[dict], system: str = "") -> str:
        prompt_content = json.dumps(messages)
        h = hashlib.md5(prompt_content.encode()).hexdigest()
        cache_file = cache_dir / f"man_{current_scenario_id}_{h}.json"
        
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
        
    detector.llm.generate = cached_generate
    
    metrics = {"TP": 0, "FP": 0, "TN": 0, "FN": 0, "Total": 0}
    
    for item in data:
        cat = item["category"]
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
        
        metrics["Total"] += 1
        result = await detector.evaluate(message, history, scenario)
        await asyncio.sleep(20)  # Avoid rate limits
        
        is_flagged = result["flagged"]
        should_flag = expected_flagged
        
        if is_flagged and should_flag:
            metrics["TP"] += 1
        elif is_flagged and not should_flag:
            metrics["FP"] += 1
            print(f"[FP] Holdout: {item['name']} - Reason: {result['reason']}")
        elif not is_flagged and not should_flag:
            metrics["TN"] += 1
        elif not is_flagged and should_flag:
            metrics["FN"] += 1
            print(f"[FN] Holdout: {item['name']}")

    tp, fp, tn, fn = metrics["TP"], metrics["FP"], metrics["TN"], metrics["FN"]
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    print("=" * 40)
    print("ManipulationDetector Holdout Report")
    print("=" * 40)
    print(f"Total Scenarios Run : {metrics['Total']}")
    print(f"True Positives      : {tp}")
    print(f"False Positives     : {fp}")
    print(f"True Negatives      : {tn}")
    print(f"False Negatives     : {fn}")
    print(f"Precision           : {precision:.2f}")
    print(f"Recall              : {recall:.2f}")
    print(f"F1 Score            : {f1:.2f}")
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

if __name__ == "__main__":
    asyncio.run(run_holdout())
