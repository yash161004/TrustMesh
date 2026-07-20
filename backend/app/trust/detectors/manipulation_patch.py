        if majority_vote:
            original_model = getattr(self.llm, "model_name", "mock")
            original_provider = getattr(self.llm, "provider", "mock")
            
            try:
                # Call Groq
                self.llm.model_name = "groq-voter"
                self.llm.provider = "groq"
                try:
                    res1 = await run_call(self.llm, temperature=0.0)
                except Exception as e:
                    res1 = e
                    
                # Call Gemini
                self.llm.model_name = "gemini-voter"
                self.llm.provider = "gemini"
                try:
                    res2 = await run_call(self.llm, temperature=0.0)
                except Exception as e:
                    res2 = e
            finally:
                self.llm.model_name = original_model
                self.llm.provider = original_provider
            
            results = []
            if res1 is not None and not isinstance(res1, Exception):
                print(f"[DEBUG] Groq vote: Flagged={res1['flagged']}, Score={res1['confidence_score']}, Reason={res1['reason']}")
                results.append(res1)
            else:
                print(f"[DEBUG] Groq failed: {res1}")
                logger.warning(f"Provider Groq failed: {res1}")
                
            if res2 is not None and not isinstance(res2, Exception):
                print(f"[DEBUG] Gemini vote: Flagged={res2['flagged']}, Score={res2['confidence_score']}, Reason={res2['reason']}")
                results.append(res2)
            else:
                print(f"[DEBUG] Gemini failed: {res2}")
                logger.warning(f"Provider Gemini failed: {res2}")

            # HARD GUARD: Never silently fall back
            if len(results) < 2:
                logger.error(f"Majority vote provider failed. Res1: {res1}, Res2: {res2}")
                return {
                    "flagged": False,
                    "reason": "Degraded cross-provider voting due to provider failure",
                    "trust_impact": 0,
                    "status": "DEGRADED",
                    "confidence_score": 0.0,
                    "degraded": True,
                    "disagreement_rate": 0.0
                }
                
            disagree = False
            if results[0]["flagged"] != results[1]["flagged"]:
                disagree = True
            elif abs(results[0]["confidence_score"] - results[1]["confidence_score"]) > 0.2:
                disagree = True
                
            if disagree:
                print("[DEBUG] Tie-break fired! Calling OpenRouter...")
                self.llm.model_name = "openrouter-tiebreak"
                self.llm.provider = "openrouter"
                try:
                    res3 = await run_call(self.llm, temperature=0.0)
                    if res3 is not None and not isinstance(res3, Exception):
                        print(f"[DEBUG] OpenRouter vote: Flagged={res3['flagged']}, Score={res3['confidence_score']}, Reason={res3['reason']}")
                        results.append(res3)
                    else:
                        print(f"[DEBUG] OpenRouter failed: {res3}")
                        logger.warning(f"Provider OpenRouter failed: {res3}")
                except Exception as e:
                    print(f"[DEBUG] OpenRouter exception: {e}")
                    logger.warning(f"Provider OpenRouter exception: {e}")
                finally:
                    self.llm.model_name = original_model
                    self.llm.provider = original_provider
                    
                # HARD GUARD for tie-break
                if len(results) < 3:
                    logger.error(f"Tie-break provider failed.")
                    return {
                        "flagged": False,
                        "reason": "Degraded cross-provider voting due to tie-break provider failure",
                        "trust_impact": 0,
                        "status": "DEGRADED",
                        "confidence_score": 0.0,
                        "degraded": True,
                        "disagreement_rate": 0.0
                    }
                
            flagged_count = sum(1 for r in results if r["flagged"])
            avg_confidence = sum(r["confidence_score"] for r in results) / len(results)
            
            if flagged_count > len(results) / 2:
                # Majority flagged
                flagged_results = [r for r in results if r["flagged"]]
                avg_impact = sum(r["trust_impact"] for r in flagged_results) // len(flagged_results)
                reasons_set = list(set(r["reason"] for r in flagged_results if r["reason"]))
                return {
                    "flagged": True,
                    "reason": " | ".join(reasons_set),
                    "trust_impact": avg_impact,
                    "status": "FLAGGED",
                    "confidence_score": avg_confidence,
                    "degraded": False,
                    "disagreement_rate": 0.0 if not disagree else 0.33
                }
            elif flagged_count == len(results) / 2 and len(results) % 2 == 0:
                # Tie: one flagged, one didn't (only happens if len(results) == 2 or 4)
                reasons_set = []
                for r in results:
                    if r["flagged"]:
                        reasons_set.append(f"Flagged: {r['reason']}")
                    else:
                        reasons_set.append(f"Cleared.")
                return {
                    "flagged": True, # set True so it's surfaced as a Violation object
                    "reason": " | ".join(reasons_set),
                    "trust_impact": 0,
                    "status": "DISPUTED",
                    "confidence_score": avg_confidence,
                    "degraded": False,
                    "disagreement_rate": 0.5
                }
            else:
                return {
                    "flagged": False,
                    "reason": "",
                    "trust_impact": 0,
                    "status": "CLEARED",
                    "confidence_score": avg_confidence,
                    "degraded": False,
                    "disagreement_rate": 0.0 if not disagree else 0.33
                }
        else:
            # Self-consistency sampling (default)
            original_model = getattr(self.llm, "model_name", "mock")
            original_provider = getattr(self.llm, "provider", "mock")
            
            try:
                self.llm.model_name = "gemini-voter"
                self.llm.provider = "gemini"
                
                # 3 concurrent calls to Gemini
                tasks = [run_call(self.llm, temperature=0.15) for _ in range(3)]
                sc_results_raw = await asyncio.gather(*tasks, return_exceptions=True)
            finally:
                self.llm.model_name = original_model
                self.llm.provider = original_provider
                
            sc_results = [r for r in sc_results_raw if r is not None and not isinstance(r, Exception)]
            
            if len(sc_results) < 3:
                logger.error("Self-consistency sampling failed: One or more provider calls failed.")
                return {
                    "flagged": False,
                    "reason": "Degraded self-consistency due to provider failure",
                    "trust_impact": 0,
                    "status": "DEGRADED",
                    "confidence_score": 0.0,
                    "degraded": True,
                    "disagreement_rate": 0.0
                }
                
            flagged_count = sum(1 for r in sc_results if r["flagged"])
            majority_flagged = flagged_count > len(sc_results) / 2
            
            # Disagreement rate: ratio of minority vote
            minority_count = min(flagged_count, len(sc_results) - flagged_count)
            disagreement_rate = minority_count / len(sc_results)
            
            # Confidence and impact averaged over agreeing subset
            agreeing_subset = [r for r in sc_results if r["flagged"] == majority_flagged]
            avg_confidence = sum(r["confidence_score"] for r in agreeing_subset) / len(agreeing_subset)
            
            if majority_flagged:
                avg_impact = sum(r["trust_impact"] for r in agreeing_subset) // len(agreeing_subset)
                reasons_set = list(set(r["reason"] for r in agreeing_subset if r["reason"]))
                return {
                    "flagged": True,
                    "reason": " | ".join(reasons_set),
                    "trust_impact": avg_impact,
                    "status": "FLAGGED",
                    "confidence_score": avg_confidence,
                    "degraded": False,
                    "disagreement_rate": disagreement_rate
                }
            else:
                return {
                    "flagged": False,
                    "reason": "",
                    "trust_impact": 0,
                    "status": "CLEARED",
                    "confidence_score": avg_confidence,
                    "degraded": False,
                    "disagreement_rate": disagreement_rate
                }
