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


def brier_score(predictions: list[float], labels: list[int]) -> float:
    return sum((p - y) ** 2 for p, y in zip(predictions, labels)) / len(labels)


def expected_calibration_error(predictions: list[float], labels: list[int], n_bins: int = 10) -> float:
    bins = [[] for _ in range(n_bins)]
    for p, y in zip(predictions, labels):
        idx = min(int(p * n_bins), n_bins - 1)
        bins[idx].append((p, y))
    ece = 0.0
    n = len(labels)
    for bucket in bins:
        if not bucket:
            continue
        avg_conf = sum(p for p, _ in bucket) / len(bucket)
        avg_acc = sum(y for _, y in bucket) / len(bucket)
        ece += (len(bucket) / n) * abs(avg_conf - avg_acc)
    return ece

async def run_holdout():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-cache", action="store_true", help="Disable LLM response caching")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of scenarios to run")
    args = parser.parse_args()

    scenarios_path = Path(__file__).parent.parent / "tests" / "benchmark_data" / "manipulation_holdout.json"
    with open(scenarios_path, "r") as f:
        data = json.load(f)
        
    if args.limit:
        data = data[:args.limit]
        
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
    predictions: list[float] = []
    labels: list[int] = []
    
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
        
        confidence = result.get("confidence_score")
        if confidence is not None:
            p_manipulation = confidence if is_flagged else (1.0 - confidence)
            predictions.append(p_manipulation)
            labels.append(1 if expected_flagged else 0)
        
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
    print("ManipulationDetector Holdout Report")
    print("=" * 40)
    print(f"Total Scenarios Run : {metrics['Total']}")
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
    if predictions:
        bs = brier_score(predictions, labels)
        ece = expected_calibration_error(predictions, labels)
        print(f"Brier Score         : {bs:.4f}")
        print(f"ECE                 : {ece:.4f}")
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
