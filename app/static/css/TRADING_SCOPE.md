# TRADING SCOPE — FROZEN

## CORE TRADING

- Strategy: EXISTING strategy only
- Exchange: EXISTING exchange configuration
- Mode: Paper trading OR Live (unchanged)
- Timeframe: As currently configured

- No new indicators
- No new ML models
- No strategy changes
- No parameter tuning
- No performance optimizations

---

## EXECUTION & ACCOUNTING (LOCKED)

- Order lifecycle must remain unchanged
- Position open/close logic must remain unchanged
- Exit logic (TP / SL) must remain unchanged
- PnL must be calculated from EXISTING exchange data only
- Persistence format (bot_state.json) is frozen
- Balance update logic is frozen

---

## RIBS / DASHBOARD / TRADE HISTORY (UI-ONLY)

- RIBS logic, scoring, and thresholds are FROZEN
- Dashboard work is VISUAL ONLY (layout, grouping, labels)
- Trade history must use EXISTING fields only
- No derived metrics added
- No backend changes for UI
- No new APIs, endpoints, or queries
- Symbol formatting and column ordering allowed
- Styling and readability improvements allowed

---

## NOT IN SCOPE (STRICT)

- Adding new RIBS metrics or signals
- Changing RIBS weighting or math
- Adding new dashboards or pages
- Adding filters that require backend changes
- Adding export/download features
- Adding alerts, notifications, or automation
- Refactoring for cleanliness or speed

---

## DEFINITION OF DONE

Trading is DONE only when:
- Orders place successfully
- Orders fill or correctly skip
- Positions remain consistent across memory + persistence
- Exits close positions correctly
- PnL reflects REAL executed values
- System runs 24h without crash or state corruption

UI is DONE only when:
- No backend code was changed
- No trading behavior changed
- Data clarity is improved without altering meaning

GOAL:
ONE stable strategy with correct execution, accounting, and a readable dashboard.
