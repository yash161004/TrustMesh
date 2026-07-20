import asyncio
import json
from app.trust.detectors.manipulation import ManipulationDetector
from app.models import NegotiationMessage, NegotiationScenario

async def main():
    print("Loading scenarios...")
    with open("tests/benchmark_data/holdout_scenarios.json") as f:
        data = json.load(f)[:3]  # Take first 3 scenarios
        
    detector = ManipulationDetector()
    
    for i, item in enumerate(data):
        print(f"\n--- SCENARIO {i+1}: {item['name']} ---")
        constraints = item["scenario_constraints"]
        
        # Add defaults
        defaults = {
            "product_name": "Product",
            "quantity": 100,
            "currency": "USD",
            "market_reference_price": 500,
            "buyer_budget_cap": 500,
            "buyer_target_price": 400,
            "seller_floor_price": 400,
            "seller_asking_price": 600,
            "delivery_preference_days": 14,
            "standard_delivery_days": 30
        }
        for k, v in defaults.items():
            if k not in constraints:
                constraints[k] = v
                
        scenario = NegotiationScenario(**constraints)
        message = NegotiationMessage(**item["test_message"])
        history = [NegotiationMessage(**m) for m in item.get("message_history", [])]
        
        # Run self-consistency voting
        # Note: no_cache is implicitly handled since we didn't mock detector.llm.generate with cache!
        result = await detector.evaluate(message, history, scenario, majority_vote=False)
        print(f"Final Result: Flagged={result['flagged']}, Disagreement={result['disagreement_rate']}")
        
        await asyncio.sleep(15)  # Throttle just in case

if __name__ == "__main__":
    asyncio.run(main())
