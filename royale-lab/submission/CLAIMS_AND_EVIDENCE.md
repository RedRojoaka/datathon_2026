# Claims & Evidence appendix

Fictional casino; synthetic challenge data. Draft findings for team review.

## F-01: Weekday averages was selected using only pre-May validation.

- Query / transformation: property_day → forecasting.run_forecast → forecast_metrics.csv
- Result: May–June MAE $68,699; constant-mean MAE $218,258; relative reduction 68.5%.
- Alternative: A constant mean can be sufficient if weekday patterns weaken.
- Limitation: One final 61-day holdout; models and tuning rules are declared in source.

## F-02: July forecast is a baseline-demand planning scenario.

- Query / transformation: property_day → model refit through June 30 → forecast_july.csv
- Result: July 1–30 expected wagers $40,711,162; expected contribution after supplied costs $3,603,038.
- Alternative: Changes in events, availability or game mix can shift demand and expected hold.
- Limitation: Future actuals are unavailable. Contribution uses June expected hold, F&B margin and cost assumptions; it is not realized or full net profit.

## F-03: Recent demand changes can be separated into exposure, occupancy and wagering intensity.

- Query / transformation: property_day → daily coin-in = available hours/day × occupied/available hours × wagers/occupied hour
- Result: May→June change $-62,241/day: exposure $2,223, occupancy $-35,788, intensity $-28,677.
- Alternative: Weekday composition, event timing, guest/game mix and changing demand can drive the components.
- Limitation: Sequential bridge: available hours per day, then occupied/available hours, then wagers/occupied hour. Contributions depend on this order. Weekday mix, events and other confounding can affect each factor; these are descriptive accounting effects, not causal treatment effects.

## B-02: Compare one technician package with a two-day promotion using explicit break-even requirements.

- Query / transformation: action_catalog + June peer-rate downtime opportunity + forecast_july; one unit each
- Result: Technician: $11,520 cost versus $9,056 gross recovery scenario over 23 days, requiring 127.2% recovery. Promotion July 19–20: $15,000 cost requires $158,833 incremental wagers, or 4.9% above baseline weekend demand.
- Alternative: A technician could create other benefits not priced here. A promotion can shift existing visits rather than add demand, and extra comps can raise its cost.
- Limitation: One catalogue unit each. Technician: July 8–30 recovery at June peer rates, optimistically 100% incremental and fully recoverable. Promotion: first eligible complete Saturday/Sunday weekend, July 19–20, with unchanged June expected hold. No extra F&B margin, comp expense or cannibalization is included; add these to a final experiment budget. These are break-even requirements, not causal forecasts.

## M-01: Payout variation is assessed against configured game variance before considering replacement.

- Query / transformation: machine_day.sum_bet_squared × game_math.payout_multiplier_variance / 10,000; aggregated by machine
- Result: Most negative residual: M-1158, $-36,165; z=-4.57; Bonferroni-adjusted p=0.001511 across 310 machines.
- Alternative: Random variation, approximation error or configuration/data mismatch can explain an unusual residual.
- Limitation: Independent spins and published variance are assumed; 95% screening controls multiplicity approximately, not causality. Filtered chart signals are exploratory.

## D-01: Downtime is an exposure loss; its financial value requires a counterfactual.

- Query / transformation: machine_day scheduled/available seconds; prepared_daily_view zone × config × weekday peer rates
- Result: 5,021.1 unavailable machine-hours; gross expected-win opportunity scenario $93,671.
- Alternative: Guests may substitute to another machine, and busy-period rates may differ from healthy-period rates.
- Limitation: This is not observed lost revenue. Use 0–100% realization/recovery sensitivities; machine pooling includes own healthy exposure.

## G-01: Tracked player outcomes use payouts minus wagers and distinct players across months.

- Query / transformation: player_period → group by player_id after month filters → sum monetary fields
- Result: 113,890 tracked players; net gaming result $-15,585,461; top 1% wager share 22.9%.
- Alternative: Carded behavior may differ from uncarded behavior; one person may also play without a card.
- Limitation: Guest analysis uses complete months and no machine/zone attribution. Concentration does not justify encouraging heavy losers to gamble more.

## C-01: Comp reinvestment is redeemed economic cost divided by theo; costs are subtracted once.

- Query / transformation: property_day.comp_cost_usd / theo_usd; property contribution uses pos_cogs_usd once
- Result: January ratio 0.73%; June 0.88%.
- Alternative: Redemption timing, wager mix and guest mix can shift ratios without a policy effect.
- Limitation: A before/after comparison does not measure causal loyalty-program lift.

## B-01: Fund at most three catalogue action types, respecting lead times, limits and conflicts.

- Query / transformation: action_catalog → analysis.action_cost / validate_plan → interactive scenario planner
- Result: Draft inspection cost $1,200; preserved budget $98,800.
- Alternative: A controlled promotion or staffing intervention may be worthwhile if credible benefit exceeds break-even.
- Limitation: Action uplift is unknown. The planner exposes assumptions instead of claiming an optimal causal allocation.

