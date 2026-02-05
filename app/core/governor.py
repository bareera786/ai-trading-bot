from __future__ import annotations
import logging
import uuid
from typing import Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("ai_trading_bot.governor")

@dataclass
class GovernorDecision:
    decision_id: str
    symbol: str
    action: str  # BUY, SELL, HOLD, REDUCE
    confidence: float
    reason: str
    strategies_involved: List[str]
    alignment_score: float
    timestamp: float
    meta: Dict[str, Any] = field(default_factory=dict)

class EnsembleGovernor:
    """
    The Supreme Authority for Strategy Decisions.
    Aggregates signals from multiple strategies and decides execution.
    """
    
    def __init__(self):
        self.min_alignment_score = 0.6  # 60% of weighted strategies must agree
        self.min_global_confidence = 0.65
        self.decision_history = []
    
    def decide(self, symbol: str, strategy_signals: Dict[str, Dict[str, Any]], oracle_advice: Dict = None) -> GovernorDecision:
        """
        Evaluate multiple strategy signals and issue a decision.
        """
        decision_id = str(uuid.uuid4())
        
        # 1. Collect Votes
        votes = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}
        total_weight = 0.0
        participating_strategies = []
        
        for strat_name, signal in strategy_signals.items():
            direction = signal.get("signal", "HOLD").upper()
            confidence = float(signal.get("confidence", 0.0))
            
            # Skip low confidence signals
            if confidence < 0.3:
                continue
                
            participating_strategies.append(strat_name)
            
            # Simple weighting: can be enhanced with strategy performance later
            weight = 1.0 
            
            # Add to votes
            if direction in votes:
                votes[direction] += confidence * weight
                total_weight += weight
                
        # 2. Calculate Alignment
        if total_weight == 0:
            return GovernorDecision(decision_id, symbol, "HOLD", 0.0, "No valid signals", [], 0.0, datetime.utcnow().timestamp())
            
        buy_score = votes["BUY"] / total_weight
        sell_score = votes["SELL"] / total_weight
        
        # 3. Decision Logic
        final_action = "HOLD"
        final_confidence = 0.0
        reason = "Indecisive"
        alignment_score = 0.0
        
        # Consensus Rules
        if buy_score > self.min_alignment_score:
            final_action = "BUY"
            final_confidence = buy_score
            alignment_score = buy_score
            reason = f"Consensus BUY ({buy_score:.1%} align)"
            
        elif sell_score > self.min_alignment_score:
            final_action = "SELL"
            final_confidence = sell_score
            alignment_score = sell_score
            reason = f"Consensus SELL ({sell_score:.1%} align)"
            
        else:
            # Wash Trading Prevention: strategies are fighting
            align_conflict = min(buy_score, sell_score)
            if align_conflict > 0.3:
                reason = f"Conflict detected (Buy {buy_score:.1%} / Sell {sell_score:.1%})"
            else:
                reason = "Insufficient conviction"
                
        # 4. Oracle Veto (Optional - Governor can override Oracle if consensus is massive)
        if oracle_advice and oracle_advice.get("status") == "ready":
             oracle_conf = oracle_advice.get("confidence", 0.5)
             oracle_dir = oracle_advice.get("direction", "NEUTRAL")
             
             if final_action != "HOLD":
                 # If Oracle strongly disagrees, downgrade or veto
                 if (final_action == "BUY" and oracle_dir in ["SELL", "DOWN", "0"] and oracle_conf > 0.8):
                     final_action = "HOLD"
                     reason += " | VETOED by Oracle (Strong Bearish)"
                 elif (final_action == "SELL" and oracle_dir in ["BUY", "UP", "1"] and oracle_conf > 0.8):
                     final_action = "HOLD"
                     reason += " | VETOED by Oracle (Strong Bullish)"
        
        decision = GovernorDecision(
            decision_id=decision_id,
            symbol=symbol,
            action=final_action,
            confidence=final_confidence,
            reason=reason,
            strategies_involved=participating_strategies,
            alignment_score=alignment_score,
            timestamp=datetime.utcnow().timestamp(),
            meta={"votes": votes, "oracle": oracle_advice}
        )
        
        self.decision_history.append(decision)
        # Keep history small
        if len(self.decision_history) > 1000:
            self.decision_history.pop(0)
            
        return decision
