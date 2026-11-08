# Tableau Public: build the executive story

Use the CSV files in `royale-lab/dist/downloads/`. In Tableau Public, select **Connect → Text File**, then open the appropriate CSV. Each fact table below should initially be a separate data source. These exports are in dollars except explicit catalogue `_cents` fields.

## Connections and grains

| Data source | Row grain | Use |
| --- | --- | --- |
| property_day.csv | One gaming day, whole property | Daily demand, contribution, comps, downtime |
| forecast_july.csv | One forecast day | July demand, daily bands, expected contribution |
| forecast_holdout.csv | One day × model | Validation plots; FILTER model to weekday (the selected model in this release) |
| forecast_metrics.csv | One model | CV MAE, test MAE, RMSE and bias |
| demand_bridge.csv | One May–June comparison | Daily wagering change decomposed into exposure, occupancy and intensity |
| machine_day.csv | One ACTIVE machine × gaming day | Filterable machine, bank and zone analysis |
| machine_summary.csv | One machine, full Jan–June | Full-period payout screening and ranks |
| player_month.csv | One tracked player × month | Distinct players, results and concentration |
| guest_segment_month.csv | One month × opening tier × region × age | Small cohort summaries; counts are PLAYER-MONTHS |
| action_catalog.csv | One action type | Supplied prices/limits/lead times |

Do not physically join daily property totals to machine-day rows or player-month facts: this repeats money. Use separate sheets/data sources or carefully scoped relationships. The static dashboard already implements the forecast and budget scenario if you do not want to recreate those features in Tableau.

## Dashboard 1: executive demand briefing

Suggested size: 1440 × 1000, cream background, dark green titles, gold highlights. Top row: four KPI worksheets. Below: forecast line chart, model-validation panel and weekday demand bars. Last row: financial bridge and priced recommendation.

1. **Historical demand:** `property_day.csv`. Columns: continuous DAY(gaming_date). Rows: SUM(coin_in_usd). Format dollars. Add event names to tooltips; treat associations as descriptive.
2. **July forecast:** `forecast_july.csv`. Columns: continuous DAY(gaming_date). Rows: SUM(forecast_coin_in_usd). Add lower_90_usd and upper_90_usd as clearly labeled daily error-band lines. Use a separate historical sheet if combining data sources is unfamiliar.
3. **Weekday planning:** create `DATENAME('weekday', [gaming_date])` on the July source, Rows: AVG(forecast_coin_in_usd), order Monday–Sunday. This estimates relative demand, not required staff counts.
4. **Financial bridge:** forecast wagers × assumed June expected hold → expected house win → add F&B margin → subtract supplied costs. Use the precomputed forecast fields; keep actual and expected results separate.
5. **Validation:** show metrics from forecast_metrics.csv and an actual-vs-forecast plot from forecast_holdout.csv filtered to the selected model. Do not sum actuals across the three model rows.
6. **Demand bridge:** use demand_bridge.csv to show the exposure_effect_usd, occupancy_effect_usd and intensity_effect_usd components. They sum to June daily wagers minus May daily wagers. This is a sequential accounting decomposition, not an estimate of causal effects; show the assumptions in the tooltip.

The selected model can change after a new official dataset release. Read forecast_methodology.json rather than permanently hardcoding a model name.

## Dashboard 2: machine performance and availability

Use machine_day.csv. Put gaming_date on a date-range filter and show zone_name, bank_id and manufacturer filters. Add a click-to-filter action from a machine ranking to its daily history.

Calculated fields:

```text
Observed hold
IF SUM([coin_in_usd]) > 0 THEN
    SUM([house_win_usd]) / SUM([coin_in_usd])
END

Availability
IF SUM([scheduled_hours]) > 0 THEN
    SUM([available_hours]) / SUM([scheduled_hours])
END

Theo per available hour
IF SUM([available_hours]) > 0 THEN
    SUM([theo_usd]) / SUM([available_hours])
END

Luck residual
SUM([house_win_usd]) - SUM([theo_usd])

Payout residual z
IF SUM([payout_variance_usd2]) > 0 THEN
    (SUM([house_win_usd]) - SUM([theo_usd])) /
    SQRT(SUM([payout_variance_usd2]))
END
```

Recommended sheets: scatter of expected versus actual win per available hour; downtime bar by zone; bottom-ten context table; cumulative actual/theo line for a selected machine. The diagonal in the scatter represents equal actual/expected productivity, not causal machine quality.

Do not average daily ratios. The export excludes inactive/off-floor rows. Use the latest-zone field in machine_summary only as a full-period summary label; machines can move. Full-period Bonferroni screening is in machine_summary.csv; filtered z values are exploratory.

## Dashboard 3: tracked guests and loyalty

Use player_month.csv. Convert period_month to a month date if needed:

```text
Month date
DATEPARSE('yyyy-MM', [period_month])

Tracked player net
SUM([tracked_payout_usd]) - SUM([tracked_coin_in_usd])

Comp reinvestment
IF SUM([theo_usd]) > 0 THEN
    SUM([comp_cost_usd]) / SUM([theo_usd])
END

Selected-month player net
{ FIXED [player_id] : SUM([tracked_net_usd]) }

Selected-month player wagers
{ FIXED [player_id] : SUM([tracked_coin_in_usd]) }

Players ahead
COUNTD(IF [Selected-month player net] > 0 THEN [player_id] END)
/
COUNTD([player_id])
```

**For FIXED calculations, add the month, opening-tier, region and age filters to Context** so selected-month totals respond to them. Use COUNTD(player_id) for distinct players. A person appearing in several months must not be counted repeatedly in the total. Avoid summing an LOD value repeated across rows; use one mark per player or an appropriate aggregation.

Suggested sheets: wagers/payouts/player-net bars; player-net distribution; cumulative wager-concentration curve; monthly comp-cost bars with comp/theo line; tier/region cohort comparison. guest_segment_month.csv is a faster option for monetary cohort charts, but its player_months measure is not a unique-player total across months.

## Dashboard 4: action plan

Use action_catalog.csv for a simple priced action table, or use the working web budget planner and export its scenario JSON.

```text
30-day unit cost
([unit_cost_cents] + [recurring_cost_cents_per_day] *
 MAX(0, 30 - [lead_days])) / 100
```

The purchased-machine capital cost is paid in full. A lease with 14 lead days has only 16 operating days in the horizon. Limit funded types to three; respect quantities and policy conflicts. A promotion's break-even additional wagering is its full incremental cost divided by expected hold, assuming no F&B upside. This is a requirement, not a forecast of promotional lift.

## Built-in Tableau forecast (optional)

Tableau Public can forecast time series with exponential smoothing: continuous date plus a measure, then **Analysis → Forecast → Show Forecast**. Keep this as a labeled exploration until it has the same honest time-based baseline comparison. Showing an attractive forecast alone does not meet the challenge's validation requirement. The validated Python forecast is available to use immediately.

Official help: https://help.tableau.com/current/pro/desktop/en-us/forecasting.htm

## Gemini-generated management explanation

The API integration is ready in the local companion page. Follow [GEMINI_GUIDE.md](GEMINI_GUIDE.md) to configure a key privately, generate a real briefing, and connect the resulting `tableau_support/gemini_insights.csv`. In a new sheet using that source only, filter Topic to one value and put Explanation on Text. Add evidence IDs, model, generation timestamp and scope to Tooltip. Label the explanation as Gemini-generated and state that existing chart filters are separate from the declared briefing scope. The CSV contains no key. Refresh the source after generating more topics, then republish the workbook. The companion is lightweight and can run while large Tableau workbooks are closed.

## Publishing

Save your workbook to Tableau Public and test its link in a private browser window. Publish only the intended challenge data and derived analysis. Keep the Gemini key and `.runtime` files out of Tableau. If desktop workbook automation is unavailable, the exported CSVs and these sheet recipes are the handoff; no `.twb` workbook is claimed to have been created automatically.
