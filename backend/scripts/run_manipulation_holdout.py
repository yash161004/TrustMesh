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

    parser.add_argument("--fail-below-precision", type=float, default=0.90, help="Fail if precision is below this threshold")
    parser.add_argument("--fail-below-recall", type=float, default=0.80, help="Fail if recall is below this threshold")
    parser.add_argument("--prompt-version", type=str, default="post-few-shot-expansion", help="Note on which prompt version was used")
    args = parser.parse_args()

    scenarios_path = Path(__file__).parent.parent / "tests" / "benchmark_data" / "manipulation_holdout.json"
    with open(scenarios_path, "r") as f:
        data = json.load(f)
        
    if args.limit:
        data = data[:args.limit]
        
    detector = ManipulationDetector()
    llm = get_llm_client()
    detector.llm = llm
    
    if llm.model_name == "mock":
        print("ERROR: LLMClient is in mock mode (missing or placeholder API key). Aborting.")
        sys.exit(1)
        
    cache_dir = Path(__file__).parent.parent / "tests" / "benchmark_data" / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    original_generate = llm.generate
    current_scenario_id = None
    
    provider_stats = {"cache": 0}
    
    async def cached_generate(messages: list[dict], system: str = "", **kwargs) -> str:
        prompt_content = json.dumps(messages)
        model_tag = f"{getattr(llm, 'model_name', 'unknown')}_{getattr(llm, 'provider', 'unknown')}"
        h = hashlib.md5(f"{model_tag}:{prompt_content}".encode()).hexdigest()
        cache_file = cache_dir / f"man_{current_scenario_id}_{h}.json"
        
        if not args.no_cache and cache_file.exists():
            with open(cache_file, "r") as f:
                provider_stats["cache"] += 1
                return json.load(f)["response"]
                
        response = await original_generate(messages, system, **kwargs)
        with open(cache_file, "w") as f:
            json.dump({"response": response}, f)
            
        provider_used = getattr(llm, "last_used_provider", "unknown")
        provider_stats[provider_used] = provider_stats.get(provider_used, 0) + 1
        return response
        
    detector.llm.generate = cached_generate
    
    metrics = {"TP": 0, "FP": 0, "TN": 0, "FN": 0, "Degraded": 0, "Total": 0}
    predictions: list[float] = []
    labels: list[int] = []
    disagreement_rates = []
    
    import app.llm_client
    app.llm_client.llm_stats = {"cost": 0.0, "tokens": 0}
    
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
        await asyncio.sleep(15)  # Throttle to stay under ~12 RPM for Gemini free tier
        
        if result.get("degraded"):
            metrics["Degraded"] += 1
            print(f"[DEGRADED] Holdout: {item['name']} - Excluded from metrics")
            continue
        
        if result and "disagreement_rate" in result and result["disagreement_rate"] is not None:
            disagreement_rates.append(result["disagreement_rate"])
        
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
    if metrics["Degraded"] > 0:
        print(f"Degraded (Excluded) : {metrics['Degraded']}")
    print(f"True Positives      : {tp}")
    print(f"False Positives     : {fp}")
    print(f"True Negatives      : {tn}")
    print(f"False Negatives     : {fn}")
    print(f"Precision           : {precision_str}")
    print(f"Recall              : {recall_str}")
    print(f"F1 Score            : {f1_str}")
    if disagreement_rates:
        avg_disagree = sum(disagreement_rates) / len(disagreement_rates)
        print(f"Disagreement Rate   : {avg_disagree:.2f}")
    else:
        print(f"Disagreement Rate   : N/A")
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
    
    cost_stats = getattr(app.llm_client, "llm_stats", {"cost": 0.0, "tokens": 0})
    print(f"Total Tokens   : {cost_stats['tokens']}")
    print(f"Total Cost     : ${cost_stats['cost']:.6f}")
    
    for provider, count in provider_stats.items():
        if provider == "cache":
            print(f"  - from {provider}: {count}")
        else:
            print(f"  - via {provider} (live): {count}")
    print("=" * 40)

    # Logging to EVAL_RESULTS.md
    import datetime
    import subprocess
    
    if (tp + fp + tn + fn) == 0:
        print("\nERROR: All scenarios degraded or holdout set empty. Aborting before writing N/A to results log.")
        sys.exit(1)
    
    docs_dir = Path(__file__).parent.parent.parent / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    eval_file = docs_dir / "EVAL_RESULTS.md"
    
    try:
        git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()[:7]
    except Exception:
        git_sha = "unknown"
        
    date_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    avg_disagree_str = f"{avg_disagree:.2f}" if disagreement_rates else "N/A"
    
    if not eval_file.exists():
        with open(eval_file, "w") as f:
            f.write("# Manipulation Detector Holdout Results\n\n")
            f.write("| Date | Git SHA | Precision | Recall | F1 Score | Disagreement Rate | Prompt Version |\n")
            f.write("|------|---------|-----------|--------|----------|-------------------|----------------|\n")
            
    with open(eval_file, "a") as f:
        f.write(f"| {date_str} | `{git_sha}` | {precision_str} | {recall_str} | {f1_str} | {avg_disagree_str} | {args.prompt_version} |\n")

    # CI Threshold checks
    failed = False
    if precision_str != "N/A" and precision_val < args.fail_below_precision:
        print(f"\nERROR: Precision {precision_val:.2f} is below threshold {args.fail_below_precision}")
        failed = True
    if recall_str != "N/A" and recall_val < args.fail_below_recall:
        print(f"\nERROR: Recall {recall_val:.2f} is below threshold {args.fail_below_recall}")
        failed = True
        
    if failed:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_holdout())
