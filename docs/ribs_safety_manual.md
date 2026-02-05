# RIBS Safety & Hardening Manual (CLAW_BOT)

This document outlines the safety mechanisms implemented to protect capital and ensure strategy stability within the RIBS (Recursive Iterative Backtest System) optimization engine.

## 1. Market Regime Detection
The system no longer runs in a "one-size-fits-all" mode. It dynamically adapts to current conditions.
- **Indicators**: Analyzes 48h BTCUSDT momentum (SMA crossover) and volatility (Daily StdDev).
- **Regimes**:
  - `trending_bull`: Aggressive growth enabled.
  - `trending_bear`: Defensive positioning; reduced risk multipliers.
  - `volatile`: 20% objective penalty applied to aggressive Solution candidates with wide stops.
  - `sideways`: Standard operation with tighter TP/SL.

## 2. Overfitting Prevention (Robustness Score)
To prevent "curve-fitting" where a strategy looks great on one set of data but fails in live markets, we use **Segmented Validation**.
- **The Process**: Each strategy candidate is evaluated on two separate halves of the market data.
- **Robustness Objective**:
  - `Objective = (Lower_Segment_Return * 0.7) + (Average_Return * 0.3)`
  - This weighting forces the optimizer to favor strategies that perform reliably across different time periods rather than finding a single "lucky" peak.

## 3. Mandatory Paper Trading Gating
No RIBS strategy can be promoted to live trading without passing through the **Validation Box**.
- **Isolation**: All new deployments are hard-coded with `paper_only=True`.
- **Promotion**: Strategies are registered in the `StrategyManager` but remain **Inactive** (`active_strategies[id] = False`) until manually audited.
- **Verification**: Strategies must demonstrate stability in a live "Paper Valuation" phase before being flipped to real capital.

## 4. Capital Allocation Limit
Traditional strategies might allocate up to 10% or 20% of a portfolio. RIBS strategies are now hard-clamped.
- **Limit**: **5% Max** position size (`position_size <= 0.05`).
- **Enforcement**: This is enforced at the **Optimization Layer** (clamped during generation) and the **Deployment Layer** (overridden before registration).

## 5. Emergency Controls
- **Global Kill Switch**: `ribs_control.json` can be set to `active: false` to immediately cease all optimization and liquidate positions.
- **Monitoring**: Logs are tagged with `🧬` emoji for easy auditing of RIBS-specific events.
