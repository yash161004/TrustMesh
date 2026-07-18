#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

# Adjust path so we can import from backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import NegotiationMessage, NegotiationScenario
from app.trust.detectors.manipulation import ManipulationDetector

import asyncio
import argparse
import hashlib
from app.llm_client import get_llm_client

def brier_score(predictions: list[float], labels: list[int]) -> float:
    if not labels: return 0.0
    return sum((p - y) ** 2 for p, y in zip(predictions, labels)) / len(labels)

def expected_calibration_error(predictions: list[float], labels: list[int], n_bins: int = 10) -> float:
    if not labels: return 0.0
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

category_names = {
    10: "Stealthy/Structural",
    11: "Multi-turn",
    12: "Borderline Benign",
    13: "Helpfulness Disguise",
    14: "Mixed"
}

async def run_benchmark():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-cache", action="store_true", help="Disable LLM response caching")
    parser.add_argument("--limit", type=int, help="Limit the number of scenarios to run")
    args = parser.parse_args()

    scenarios_path = Path(__file__).parent.parent / "tests" / "benchmark_data" / "adversarial_scenarios.json"
    with open(scenarios_path, "r") as f:
        data = json.load(f)
        
    if args.limit:
        data = data[:args.limit]
        
    manipulation_detector = ManipulationDetector()
    llm = get_llm_client()
    manipulation_detector.llm = llm
    
    if getattr(llm, "model_name", "") == "mock":
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
        
    manipulation_detector.llm.generate = cached_generate
    
    overall_metrics = {"TP": 0, "FP": 0, "TN": 0, "FN": 0, "Total": 0, "Errors": 0}
    cat_metrics = {cat: {"TP": 0, "FP": 0, "TN": 0, "FN": 0, "Total": 0, "Errors": 0} for cat in category_names}
    
    manip_predictions: list[float] = []
    manip_labels: list[int] = []
    cat_predictions = {cat: [] for cat in category_names}
    cat_labels = {cat: [] for cat in category_names}
    
    false_results = []
    
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
        
        overall_metrics["Total"] += 1
        cat_metrics[cat]["Total"] += 1
        
        try:
            result = await manipulation_detector.evaluate(message, history, scenario)
        except Exception as e:
            print(f"[Manipulation ERROR/RETRY] {item['name']} - {e}")
            overall_metrics["Errors"] += 1
            cat_metrics[cat]["Errors"] += 1
            continue
            
        await asyncio.sleep(4)  # Avoid rate limits
        is_flagged = result["flagged"]
        
        confidence = result.get("confidence_score")
        if confidence is not None:
            p_manipulation = confidence if is_flagged else (1.0 - confidence)
            manip_predictions.append(p_manipulation)
            manip_labels.append(1 if expected_flagged else 0)
            cat_predictions[cat].append(p_manipulation)
            cat_labels[cat].append(1 if expected_flagged else 0)
        
        if is_flagged and expected_flagged:
            overall_metrics["TP"] += 1
            cat_metrics[cat]["TP"] += 1
        elif is_flagged and not expected_flagged:
            overall_metrics["FP"] += 1
            cat_metrics[cat]["FP"] += 1
            false_results.append(f"FALSE POSITIVE | {current_scenario_id}: {item['name']} - Reason given: {result['reason']}")
        elif not is_flagged and not expected_flagged:
            overall_metrics["TN"] += 1
            cat_metrics[cat]["TN"] += 1
        elif not is_flagged and expected_flagged:
            overall_metrics["FN"] += 1
            cat_metrics[cat]["FN"] += 1
            false_results.append(f"FALSE NEGATIVE | {current_scenario_id}: {item['name']}")

    def print_report(name, m, preds, labels):
        tp, fp, tn, fn = m["TP"], m["FP"], m["TN"], m["FN"]
        total = m["Total"]
        
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
        
        print("=" * 60)
        print(f"--- {name} ---")
        print(f"Total Scenarios : {total}")
        print(f"True Positives  : {tp}")
        print(f"False Positives : {fp}")
        print(f"True Negatives  : {tn}")
        print(f"False Negatives : {fn}")
        if m["Errors"] > 0:
            print(f"Errors          : {m['Errors']}")
        print(f"Precision       : {precision_str}")
        print(f"Recall          : {recall_str}")
        print(f"F1 Score        : {f1_str}")
        if (tp + fn) == 0:
            print(f"  ^ Precision/Recall/F1 are N/A because no positive ground-truth cases exist in this category. All {total}/{total} scenarios are non-manipulative and the detector correctly classified all {tn} as such (0 false positives).")
        elif (tp + fp) == 0:
            print(f"  ^ Precision is N/A because the detector made no positive predictions for this group. Recall is {recall_str}.")
        if preds:
            bs = brier_score(preds, labels)
            ece = expected_calibration_error(preds, labels)
            print(f"Brier Score     : {bs:.4f}")
            print(f"ECE             : {ece:.4f}")

    print("\n" + "=" * 60)
    print("MANIPULATION DETECTOR - ADVERSARIAL BENCHMARK")
    print("=" * 60)

    print_report("OVERALL AGGREGATE", overall_metrics, manip_predictions, manip_labels)
    
    for cat, name in category_names.items():
        if cat_metrics[cat]["Total"] > 0:
            print_report(f"CATEGORY: {name}", cat_metrics[cat], cat_predictions[cat], cat_labels[cat])

    print("=" * 60)
    print("FALSE RESULTS SUMMARY (FP/FN)")
    print("=" * 60)
    if not false_results:
        print("None! Perfect run (excluding API errors).")
    else:
        for fr in false_results:
            print(fr)

    print("=" * 60)
    print("LLM Provider Usage Summary")
    print("=" * 60)
    total_calls = sum(provider_stats.values())
    print(f"Total LLM calls: {total_calls}")
    for provider, count in provider_stats.items():
        if provider == "cache":
            print(f"  - from {provider}: {count}")
        else:
            print(f"  - via {provider} (live): {count}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
