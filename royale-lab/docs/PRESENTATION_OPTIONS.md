# Presentation decisions to make together

Current preference: **executive briefing**, emphasizing **demand forecasts for staffing and promotions**. The first working design uses an ivory background, dark green navigation and gold accents. All chart data are calculated locally; no illustrative placeholder values are used.

Team steering: compare staffing and promotion break-even side by side. Budget lab now compares one catalogue technician package with the first complete eligible two-day promotion weekend. Each has an independent assumption slider, explicit cost, benefit horizon, break-even requirement and caveats. Staffing means the supplied technician-shift action, not a generic new headcount model.

| Dashboard | Current chart | Other appropriate choices | Analytical question |
| --- | --- | --- | --- |
| Executive briefing | July forecast with bands, retained-contribution comparison, zone productivity | Single financial waterfall; daily-demand calendar; three decision cards | What should the manager do next, and why? |
| Demand & forecast | Historical/forecast line, untouched test view, weekday bars, validation table | Weekday × week heatmap; error-by-weekday bars; staffing coverage overlay | Which peaks are predictable and where are misses material? |
| Machine health | Theo/actual productivity scatter, downtime by zone, contextual low-earner table, machine history | Floor-position map; before/after move small multiples; downtime heatmap | Is low earning explained by luck, exposure, location or something to inspect? |
| Guests & loyalty | Wagers/payouts/net bars, concentration curve, comp/theo trend, result distribution | Tier small multiples; player-net boxplots; cohort retention only with a stated observation definition | What did tracked players experience, and what did benefits cost? |
| Budget lab | Catalogue-constrained planner, sensitivity controls, benefit/cost waterfall | Break-even curve; tornado chart; experiment scorecard | Which assumptions make an action worth its cost? |
| Evidence | Claim → transformation → result → alternative → limitation | Numbered evidence drawer beside each chart; methods appendix | Can someone reproduce and challenge the conclusion? |

## Good next choices for the team

1. Should the main narrative be “staff for predictable peaks” or “test promotions on quieter days”? Forecasting alone cannot identify promotion lift.
2. Which staffing question matters: shift coverage, technician availability, or daily scheduling? Hourly analysis would be an optional extension, not something daily forecasts identify.
3. Should the main view show an overview of the full six months, the most recent month, or a manager-selectable window? Forecast training/test periods remain fixed for validation.
4. For Tableau, do you prefer one executive canvas with supporting sheets, or three linked dashboards (demand, floor, guests)?
5. Which proposed intervention can your team defend with a cost, target, uncertain effect and control/measurement plan?

## Interpretation standards

- Forecast baseline demand separately from assumed intervention lift.
- Label contribution “after supplied costs”; it is not full profit.
- Keep tracked player net opposite in sign to house gaming win.
- Date filters must not silently turn a held-out test into training data.
- Show ratios of sums, missing data and exposure clearly.
- Use concentration to describe risk, not to target heavy losing guests.
- Treat unusual payouts as inspection leads, not accusations.

## Optional extensions after team feedback

- Hour-of-day demand and shift coverage using machine_hour and shift_roster. This could answer staffing questions more precisely than a daily forecast.
- Descriptive analysis around the documented walkway closure, with comparisons to unaffected zones. A before/after difference still needs competing explanations.
- A manually configured and validated exponential-smoothing forecast in Tableau as a comparison to weekday averages.
- A randomized or matched promotion pilot, estimating incremental contribution net of all promotional/comp costs; the existing data alone do not establish this effect.
