"""
TrustMesh — Real Negotiation Batch Runner (Step 1 Data Generation - Throttled & Multi-Shape)

Single Database Source of Truth: PostgreSQL (backend/.env DATABASE_URL)
Features:
- Paced turn generation (3.0s delay per turn = 20 RPM max) to stay strictly under Groq 30 RPM limit
- Live LLM Trust Engine Evaluation (skip_llm=False) with 25s rate-limit exponential backoff
- Temperature jitter (temp=0.7) & prompt persona variance for dynamic natural dialogue
- Dynamic agent IDs and variable trust scores (0.15 - 0.35) for unique DB lookups
- 4 distinct violation scenario shapes for FAILED target class
- Primary tag: data_source = 'real_llm_v5'
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
import logging
import random
import uuid
from dotenv import load_dotenv

# Ensure backend/.env is loaded before importing config/settings
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
get_settings.cache_clear()

from app.db import init_db, load_session, get_session_factory
from app.models import NegotiationScenario, LineItem
from app.session_manager import session_manager
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_real_negotiations")


def make_scenario(
    sku: str,
    product_name: str,
    market_price: float,
    buyer_target: float,
    buyer_cap: float,
    seller_ask: float,
    seller_floor: float,
    quantity: int = 10,
    currency: str = "USD"
) -> NegotiationScenario:
    return NegotiationScenario(
        currency=currency,
        delivery_preference_days=14,
        standard_delivery_days=30,
        line_items=[
            LineItem(
                sku=sku,
                product_name=product_name,
                quantity=quantity,
                unit="units",
                market_reference_price=market_price,
                buyer_target_price=buyer_target,
                buyer_budget_cap=buyer_cap,
                seller_asking_price=seller_ask,
                seller_floor_price=seller_floor,
            )
        ]
    )


# Define 14 diverse scenarios including 4 distinct violation trigger shapes for FAILED
SCENARIOS = [
    # 1. Standing Desk: Target 350, Cap 420 vs Ask 480, Floor 330 -> DEAL candidate
    make_scenario("DESK-001", "Standing Desk", 400.0, 350.0, 420.0, 480.0, 330.0, 20),
    # 2. 4K Monitor: Target 420, Cap 480 vs Ask 600, Floor 470 -> NO_DEAL candidate
    make_scenario("MON-002", "4K Monitor 32-inch", 500.0, 420.0, 480.0, 600.0, 470.0, 15),
    # 3. Mechanical Keyboard: Target 100, Cap 135 vs Ask 150, Floor 110 -> DEAL candidate
    make_scenario("KEY-003", "Mechanical Keyboard Pack", 120.0, 100.0, 135.0, 150.0, 110.0, 50),
    # 4. HD Conference Webcam: Target 140, Cap 160 vs Ask 210, Floor 158 -> NO_DEAL candidate
    make_scenario("CAM-004", "HD Conference Webcam", 180.0, 140.0, 160.0, 210.0, 158.0, 30),
    # 5. 1U Rack Server: Target 3100, Cap 3600 vs Ask 4200, Floor 3300 -> DEAL candidate
    make_scenario("SRV-005", "1U Rack Server", 3500.0, 3100.0, 3600.0, 4200.0, 3300.0, 5),
    # 6. Core Router: Target 1700, Cap 1950 vs Ask 2600, Floor 1940 -> NO_DEAL candidate
    make_scenario("NET-006", "Enterprise Core Router", 2200.0, 1700.0, 1950.0, 2600.0, 1940.0, 4),
    # 7. Ergonomic Mesh Chair: Target 230, Cap 290 vs Ask 330, Floor 240 -> DEAL candidate
    make_scenario("CHR-007", "Ergonomic Mesh Chair", 280.0, 230.0, 290.0, 330.0, 240.0, 40),
    # 8. Developer Laptop: Target 1100, Cap 1250 vs Ask 1600, Floor 1245 -> NO_DEAL candidate
    make_scenario("LAP-008", "Developer Laptop 32GB", 1400.0, 1100.0, 1250.0, 1600.0, 1245.0, 10),
    # 9. Storage Enclosure: Target 5800, Cap 6600 vs Ask 7400, Floor 6000 -> DEAL candidate
    make_scenario("SAN-009", "NVMe Storage Enclosure", 6500.0, 5800.0, 6600.0, 7400.0, 6000.0, 2),
    # 10. Interactive Display: Target 2000, Cap 2250 vs Ask 2900, Floor 2240 -> NO_DEAL candidate
    make_scenario("DSP-010", "75-inch Interactive Display", 2500.0, 2000.0, 2250.0, 2900.0, 2240.0, 3),
    # 11. FAILED Shape 1: Pre-degraded Bad-Actor Buyer Reputation
    make_scenario("VOIP-011", "Enterprise VoIP Gateway Array", 1200.0, 800.0, 1050.0, 1500.0, 1000.0, 10),
    # 12. FAILED Shape 2: Seller Floor Price Policy Deviation Trigger
    make_scenario("MAN-012", "Custom Server Rack Enclosure", 4500.0, 2000.0, 4400.0, 5500.0, 4200.0, 2),
    # 13. FAILED Shape 3: Currency Substitution in Delivery Terms
    make_scenario("CUR-013", "Industrial Managed Switch", 1600.0, 1100.0, 1400.0, 1900.0, 1350.0, 8, currency="USD"),
    # 14. FAILED Shape 4: Severe Lowball Offer Below Floor
    make_scenario("LOW-014", "Fiber Optic Transceiver Module", 450.0, 150.0, 480.0, 600.0, 400.0, 100),
]


async def seed_predegraded_buyer(buyer_id: str, trust_score: float = 0.25):
    """Seed an agent reputation record with a pre-degraded trust score for FAILED testing."""
    factory = get_session_factory()
    async with factory() as db:
        await db.execute(text(
            f"INSERT INTO agent_reputations (agent_id, trust_score, total_sessions, violations_count, last_updated) "
            f"VALUES ('{buyer_id}', {trust_score}, 5, 4, NOW()) "
            f"ON CONFLICT (agent_id) DO UPDATE SET trust_score = {trust_score};"
        ))
        await db.commit()


async def run_single_session_with_retries(
    index: int,
    total: int,
    provider: str,
    tag: str = "real_llm_v5"
) -> dict:
    scenario = SCENARIOS[index % len(SCENARIOS)]
    sku = scenario.line_items[0].sku if scenario.line_items else f"SKU-{index+1}"
    product = scenario.line_items[0].product_name if scenario.line_items else "Product"
    
    # Dynamic Agent IDs so every session uses unique agent identifiers
    uid = str(uuid.uuid4())[:8]
    if sku == "VOIP-011":
        buyer_id = f"bad-actor-buyer-{uid}"
        bad_score = round(random.uniform(0.15, 0.35), 2)
        await seed_predegraded_buyer(buyer_id, bad_score)
    else:
        buyer_id = f"buyer-v5-{uid}"

    seller_id = f"seller-v5-{uid}"

    logger.info(f"[{index+1}/{total}] Starting throttled LLM session for {product} ({sku})...")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            sess = await session_manager.create_session(
                buyer_agent_id=buyer_id,
                seller_agent_id=seller_id,
                provider=provider,
                scenario=scenario,
                data_source=tag,
            )
            
            # Process turns with 3.0s pacing delay between turns to stay under 30 RPM
            messages = await session_manager.process_turn(
                session_id=sess.session_id,
                max_turns=12,
                context={"temperature": 0.7}
            )
            msg_count = len(messages)
            
            # Pacing delay before trust evaluation call to avoid 429 rate limit
            await asyncio.sleep(8.0)
            
            # Run trust evaluation with live LLM judge (skip_llm=False) and retries on rate limits
            for trust_attempt in range(3):
                try:
                    await session_manager.evaluate_trust_for_session(
                        session_id=sess.session_id, recompute=True, update_reputation=False
                    )
                    break
                except Exception as te:
                    if "RateLimit" in str(te) or "429" in str(te) or "cooldown" in str(te).lower():
                        logger.warning(f"Trust evaluation rate-limited in session {index+1} (attempt {trust_attempt+1}). Backing off 25s...")
                        await asyncio.sleep(25.0)
                    else:
                        raise te
            
            # Fetch updated state from PostgreSQL
            sess_dict = await load_session(sess.session_id)
            outcome = sess_dict.get("outcome") if sess_dict else "UNKNOWN"
            final_price = sess_dict.get("final_price") if sess_dict else None
            
            logger.info(f"  -> [{index+1}/{total}] Session completed: outcome={outcome}, price={final_price}, turns={msg_count}")
            await asyncio.sleep(15.0) # Pace rate limits between sessions
            
            return {
                "session_id": sess.session_id,
                "product": product,
                "sku": sku,
                "outcome": outcome,
                "final_price": final_price,
                "msg_count": msg_count,
                "status": "SUCCESS"
            }

        except Exception as e:
            if "RateLimitError" in str(e) or "429" in str(e) or "cooldown" in str(e).lower():
                wait_time = (attempt + 1) * 30
                logger.warning(f"Rate limit encountered in session {index+1} (attempt {attempt+1}/{max_retries}). Backing off {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Error in session {index+1}: {e}", exc_info=True)
                return {"status": "ERROR", "error": str(e), "outcome": "FAILED", "msg_count": 0}

    return {"status": "RATE_LIMIT_FAILED", "outcome": "FAILED", "msg_count": 0}


async def preflight_quota_check(primary_provider: str = "groq", max_wait_sec: int = 300) -> bool:
    """Verify all pipeline providers (negotiation turn provider + trust judge provider) are healthy."""
    from app.llm_client import get_llm_client
    
    # Check negotiation turn provider, trust engine judge provider (gemini), and tiebreak fallback (openrouter)
    providers_to_check = list(dict.fromkeys([primary_provider, "gemini", "openrouter"]))
    logger.info(f"Performing pre-flight rate-limit health check for providers: {providers_to_check}...")
    
    for provider in providers_to_check:
        client = get_llm_client(provider)
        start_time = time.time()
        provider_healthy = False
        
        while time.time() - start_time < max_wait_sec:
            try:
                res = await client.generate(
                    messages=[{"role": "user", "content": "Respond with OK"}],
                    system_prompt="You are a health check assistant.",
                    temperature=0.1,
                )
                if res:
                    logger.info(f"Pre-flight health check PASSED for provider '{provider}'.")
                    provider_healthy = True
                    break
            except Exception as e:
                err_str = str(e)
                if "RateLimit" in err_str or "429" in err_str or "cooldown" in err_str.lower():
                    logger.warning(f"Pre-flight check: provider '{provider}' rate-limited/cooldown active. Waiting 30s before retry...")
                    await asyncio.sleep(30.0)
                else:
                    logger.error(f"Pre-flight check FAILED for provider '{provider}': Unexpected error {e}")
                    return False
                    
        if not provider_healthy:
            logger.error(f"Pre-flight check FAILED: provider '{provider}' remained rate-limited after {max_wait_sec}s.")
            return False

    logger.info("All pipeline providers healthy. Proceeding with batch.")
    return True


async def run_batch(num_sessions: int = 5, provider: str = "groq", tag: str = "real_llm_v6"):
    await init_db()
    healthy = await preflight_quota_check(provider)
    if not healthy:
        logger.error("Aborting batch execution due to persistent provider rate-limit cooldown.")
        return []

    logger.info(f"Starting THROTTLED real LLM batch of {num_sessions} sessions (provider={provider}, tag={tag})...")
    
    start_time = time.time()
    results = []
    
    for i in range(num_sessions):
        res = await run_single_session_with_retries(i, num_sessions, provider, tag=tag)
        results.append(res)

    elapsed = time.time() - start_time
    logger.info(f"Batch completed in {elapsed:.2f}s.")
    return results


if __name__ == "__main__":
    num = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    prov = sys.argv[2] if len(sys.argv) > 2 else "groq"
    tg = sys.argv[3] if len(sys.argv) > 3 else "real_llm_v6"
    asyncio.run(run_batch(num_sessions=num, provider=prov, tag=tg))
