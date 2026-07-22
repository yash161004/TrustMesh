import glob, re

scenario_replace = '''    return NegotiationScenario(
        currency="USD",
        line_items=[
            LineItem(
                sku="SKU-TEST",
                product_name="Test Product",
                quantity=100,
                unit="units",
                market_reference_price=100.0,
                buyer_target_price=450.0,
                buyer_budget_cap=500.0,
                seller_asking_price=550.0,
                seller_floor_price=400.0,
            )
        ],
        delivery_preference_days=10,
        standard_delivery_days=20
    )'''

message_replace = '''    return NegotiationMessage(
        message_type="OFFER",
        sender="buyer-agent-1" if role == "buyer" else "seller-agent-1",
        proposed_items=[
            ProposedItem(sku="SKU-TEST", price=price, quantity=quantity)
        ],
        delivery_terms="Standard",
        timestamp="2026-07-16T12:00:00Z",
        turn_number=1
    )'''

for file in glob.glob('tests/test_*.py'):
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()

    changed = False

    # Add LineItem, ProposedItem to imports if not there
    if 'from app.models import' in content and 'LineItem' not in content:
        content = content.replace('from app.models import NegotiationMessage, NegotiationScenario', 'from app.models import NegotiationMessage, NegotiationScenario, LineItem, ProposedItem')
        changed = True

    if 'get_base_scenario' in content and 'product_name=' in content:
        content = re.sub(
            r'return NegotiationScenario\([\s\S]*?standard_delivery_days=20\n\s*\)',
            scenario_replace,
            content
        )
        changed = True
        
    if 'get_base_message' in content and 'price=' in content and 'ProposedItem' not in content:
        # Update function signature to accept price and quantity if not already
        content = content.replace('def get_base_message(role="buyer"):', 'def get_base_message(role="buyer", price=450.0, quantity=100):')
        content = re.sub(
            r'return NegotiationMessage\([\s\S]*?turn_number=1\n\s*\)',
            message_replace,
            content
        )
        changed = True

    if changed:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated {file}')
