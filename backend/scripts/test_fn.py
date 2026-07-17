import json
import asyncio
import sys
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import NegotiationMessage, NegotiationScenario
from app.trust.detectors.manipulation import ManipulationDetector

async def main():
    with open('tests/benchmark_data/scenarios.json', 'r') as f:
        data = json.load(f)
        
    detector = ManipulationDetector()
    
    target_names = ['The Approved Exception', 'The Budget Deadline', 'The Corporate Reorganization (Stealthy)']
    
    for item in data:
        if item['name'] in target_names:
            print(f"\n{'='*50}")
            print(f"SCENARIO: {item['name']}")
            msg = item['test_message']
            text = f"{msg.get('delivery_terms', '')} {msg.get('notes', '')}".strip()
            print(f"MESSAGE TEXT: {text}")
            
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
            
            print("-" * 50)
            # Run evaluate with majority vote
            result = await detector.evaluate(message, history, scenario, majority_vote=True)
            print(f"FINAL RESULT: Flagged={result.get('flagged')}, Confidence={result.get('confidence_score', 'N/A')}, Status={result.get('status')}")
            print(f"REASON: {result['reason']}")

if __name__ == "__main__":
    asyncio.run(main())
