# Start here

## Run the dashboard

1. Open Terminal in `dashboard-royale/royale-lab`.
2. Run `python3 serve.py`.
3. Open `http://127.0.0.1:8501` in Chrome or Safari.
4. Begin with Executive briefing, then Demand & forecast.

The generated dashboard runs without internet. Its charts use a locally bundled Plotly library. Gemini is disabled. A static hosted copy has the same analytics and downloads, with no live AI endpoint. A private hosted preview is for team review; the final challenge submission needs a judge-accessible public link or an interactive file with instructions.

## Rebuild and validate

From the same directory:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 build_analysis.py
python3 -m unittest discover -s tests -v
```

The supplied bundle remains the source data. Its manifest hashes are verified for every input used here. The build stops if an input changes or accounting does not reconcile. For a newer official release, replace the data and manifest together and review changed findings before presenting.

## What is being forecast?

Daily property wagering (coin-in), not individual losses or random payout outcomes. Models:

- Constant historical mean: the baseline.
- Weekday averages: seven means learned from earlier dates.
- Weekday plus linear trend: ordinary least squares with weekday indicators and a calendar trend.

Model choice uses two 30-day fixed-origin folds beginning March 1 and April 1. The lowest pooled absolute error wins. January–April are then used to make every May–June test prediction, without updating on holdout outcomes. July 1–30 forecasts refit the selected method through June 30.

Nominal 90% daily bands use the finite-sample 90th percentile of absolute errors from the pre-May tuning folds. These are empirical planning bands, not guaranteed coverage: observations are temporally dependent and only two folds are available. Actual May–June coverage is displayed. Summing daily endpoints does not produce a 90% monthly interval. No later-published tourism/survey series or observed future payout variables are forecast inputs.

July contribution = forecast wagering × June expected hold + June average daily F&B margin − June average daily supplied machine/technician costs. These are explicitly held-constant assumptions. The output excludes missing rent, taxes, depreciation and other costs. No future actuals are present.

## How to use the analysis together

1. Review the forecast model and its errors before choosing a business narrative.
2. Select an operational question: coverage on peak days, promotion timing, or downtime recovery.
3. Inspect its evidence and alternative explanations.
4. Enter a proposed catalogue action and targets in Budget lab.
5. Start at zero assumed uplift; calculate break-even before choosing a plausible effect.
6. Define a measurement plan. Prefer an experiment/control group for causal claims.
7. Agree on the narrative, chart style and recommendation, then record them in the write-up.

Use staffing for coverage and availability, rather than assuming more headcount generates revenue. Do not treat forecast demand as measured promotional lift. Preserve unspent budget if an action lacks evidence. Do not target heavy losing players to increase losses.

## Filter meanings

- Executive historical floor snapshot and Machine health: exact gaming-date range, zone, bank, manufacturer. The gaming day starts at 06:00 Las Vegas time.
- Forecast, property monthly bars and budget scenarios: property-wide; their fixed training/test/planning windows are stated on screen.
- Guests & loyalty: independent complete-month filters and opening-tier/region/age cohorts. No attribution to a machine or zone is implied.
- Machine location uses each day's placement. Summary labels show the latest selected placement only.
- Available/scheduled ratios use sums, with raw scheduled seconds handling the 23-hour DST gaming day and partial exposure.

## Tableau Public

Use `dist/downloads/` CSVs. Begin with `property_day.csv`, `forecast_july.csv`, and `forecast_holdout.csv` as separate data sources. Follow TABLEAU_GUIDE.md. Tableau does not need an API key. Its built-in forecast can be explored as a separate comparison, but the Python-exported forecast already has a documented holdout test.

## Before submitting

- Confirm the dashboard opens for a judge who is not signed into your private accounts.
- Exercise date filters, a bank drilldown, a guest cohort, model validation and one recommendation's evidence.
- Review the draft inspection recommendation and scenario assumptions with your team.
- Supply a ≤2 minute video, ≤400 word main write-up, source, AI-use disclosure and evidence appendix.
- Keep findings explicitly fictional and distinguish scenarios, observations and causal effects.

## Official references

- Challenge: ../GUIDE.md and ../reference/DATA_DICTIONARY.md in the supplied bundle.
- Tableau text connections: https://help.tableau.com/current/pro/desktop/en-us/examples_text.htm
- Tableau forecasting: https://help.tableau.com/current/pro/desktop/en-us/forecasting.htm
- Gemini prices: https://ai.google.dev/gemini-api/docs/pricing
- Gemini billing caps and delays: https://ai.google.dev/gemini-api/docs/billing
- Forecast evaluation: https://otexts.com/fpp3/accuracy.html
