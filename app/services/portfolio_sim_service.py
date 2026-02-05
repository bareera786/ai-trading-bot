from __future__ import annotations
import random
from typing import Dict, List, Any

class PortfolioSimService:
    """
    Simulates portfolio performance by aggregating strategy results.
    """
    
    @staticmethod
    def run_simulation(strategies: List[Any], days: int = 30) -> Dict[str, Any]:
        """
        Run a Monte Carlo simulation of the portfolio based on current weights.
        
        Args:
            strategies: List of Strategy models
            days: Number of days to simulate
            
        Returns:
            Dict containing equity curve and correlation matrix.
        """
        equity_curve = []
        base_equity = 10000.0
        current_equity = base_equity
        
        # 1. Generate hypothetical daily returns for each strategy 
        # based on their risk profile
        daily_returns = []
        
        for d in range(days):
            day_pnl_percent = 0.0
            
            for s in strategies:
                weight = float(s.capital_weight or 0.0)
                if weight <= 0: continue
                
                # Simulate return based on profile
                volatility = 0.02 # default 2% daily vol
                drift = 0.001 # slightly positive drift
                
                if s.risk_profile == "aggressive":
                    volatility = 0.05
                    drift = 0.002
                elif s.risk_profile == "conservative":
                    volatility = 0.01
                    drift = 0.0005
                    
                # Monte Carlo step
                # In real life, we would sample from historical backtests per strategy
                strategy_return = random.normalvariate(drift, volatility)
                
                # Contribution to portfolio
                day_pnl_percent += (strategy_return * weight)
            
            # Update equity
            current_equity *= (1 + day_pnl_percent)
            equity_curve.append({
                "day": d + 1,
                "equity": round(current_equity, 2)
            })
            
        # 2. Calculate Correlations (Mock for MVP)
        # In sim, we generated independent randoms, so corr is near 0.
        # We will mock meaningful correlations for the UI visualization.
        correlation_matrix = []
        names = [s.name for s in strategies]
        
        for i in range(len(names)):
            row = []
            for j in range(len(names)):
                if i == j:
                    row.append(1.0)
                else:
                    # Random correlation between -0.4 and 0.8
                    row.append(round(random.uniform(-0.4, 0.8), 2))
            correlation_matrix.append(row)

        return {
            "equity_curve": equity_curve,
            "correlation_matrix": {
                "labels": names,
                "matrix": correlation_matrix
            },
            "final_equity": round(current_equity, 2),
            "total_return_percent": round((current_equity - base_equity) / base_equity * 100, 2)
        }
