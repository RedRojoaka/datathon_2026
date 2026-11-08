# Datathon 2026 — Dashboard Royale and Heads Up

| Project | Source and instructions |
| --- | --- |
| Heads Up poker bot — **DataLarp / SteadyAce** | [Poker bot setup](pokerbot/README.md), [strategy](pokerbot/STRATEGY.md), [validation](pokerbot/VALIDATION.md), [submission](pokerbot/SUBMISSION.md) |
| Dashboard Royale — **The Gilded Ace** | Dashboard links and analysis below; source in [`royale-lab/`](royale-lab/) |

The poker project is kept in `pokerbot/`. The root `agent.py` and `requirements.txt` are its required tournament entry files. Its Docker image includes only poker runtime files. In the original workspace, edit `heads-up-bundle/agent.py` and run `python3 refresh_poker_source.py` to refresh the public source copy.

## The Gilded Ace — Decisions Beyond the Bottom Ten

Dashboard Royale entry for Datathon 2026. Four Tableau dashboards combine demand forecasting, exposure-adjusted machine analysis, tracked-player outcomes, loyalty costs, and a priced July operating plan. The casino and its data are fictional/synthetic; January–June 2025 is the observed period and July 1–30, 2025 is the planning horizon.

## Open the dashboards

No Tableau installation or API key is needed to view the published dashboards.

| Dashboard | Public interactive view |
| --- | --- |
| 1 — Demand & July Outlook | [Executive outlook and forecast validation](https://public.tableau.com/app/profile/alejandro.rojo4194/viz/Datathon_26_Dashboard_1_v3/ExecutiveOutlook) |
| 2 — Machine Performance | [Machine performance and availability](https://public.tableau.com/app/profile/alejandro.rojo4194/viz/Datathon_26_Dashboard_1_v2/Dashboard2) |
| 3 — Tracked Guests & Loyalty | [Tracked guest outcomes, concentration, and comps](https://public.tableau.com/app/profile/alejandro.rojo4194/viz/Dashboard_3_17941211263630/TrackedGuestsLoyalty) |
| 4 — Budget Decisions | [Budget scenarios, proposed action, and saved Gemini explanation](https://public.tableau.com/app/profile/alejandro.rojo4194/viz/Dashboard_4_TD2026/BudgetandActions) |

**Video:** recording pending. The [two-minute recording checklist](VIDEO_RECORDING.md) and [narration script](royale-lab/submission/VIDEO_SCRIPT.md) are ready. Add the final judge-accessible video link here before submitting on Devpost.

## Findings and proposed action

- The weekday-average demand model achieved May–June holdout MAE of **$68,699/day**, compared with **$218,258/day** for a constant training mean: a **68.5% reduction**. Model selection used earlier validation folds; test outcomes did not select the model.
- The July 1–30 outlook is **$40.71M in wagers** and **$3.60M expected contribution after supplied costs**. These use declared June assumptions; contribution is not full net profit.
- The top 1% of tracked players accounted for **22.9% of tracked wagers** over January–June. Tracked-player results do not represent all uncarded activity.
- The proposed plan funds **one $1,200 inspection of M-1158**, preserving **$98,800**. An unusual payout residual warrants investigation, not an accusation or automatic replacement. Inspection provides information; cash recovery is unknown.
- The alternative technician package costs **$11,520** versus about **$9,056** of optimistic gross recovery opportunity in its benefit horizon. The **$15,000** promotion requires about **4.9% additional weekend wagering** before extra costs. These are conditional break-even requirements, not predicted intervention effects.

## Evidence, source, and disclosure

- [Claims & Evidence appendix](royale-lab/submission/CLAIMS_AND_EVIDENCE.md)
- [Forecast methodology and validation](royale-lab/submission/forecast_methodology.json)
- [Input audit and source hashes](royale-lab/submission/input_audit.json)
- [AI-use disclosure, including recorded Gemini use](royale-lab/submission/AI_DISCLOSURE.md)
- [Actual saved Gemini briefing](royale-lab/submission/GEMINI_BRIEF.md)
- [Gemini local allowance record](royale-lab/submission/GEMINI_USAGE.json) — conservative reservations, not a provider billing statement
- [Main write-up draft](royale-lab/submission/WRITEUP_DRAFT.md) — 336 words at preparation
- [Download source archive](submission/SOURCE_CODE.zip)
- [Download combined submission materials](submission/SUBMISSION_MATERIALS.zip)

The Python pipeline computes financial figures and forecasts. Gemini explains supplied evidence and exports reviewed text to Tableau; it does not calculate the forecast or estimate causal lift. Its API key and local runtime database are excluded. The saved briefing can be read without making a new API request.

## Reproduce the analysis

Requirements: Python 3.11+, Git, and the original challenge data. This repository contains a source snapshot; large raw datasets, generated `dist/` files, and manually saved Tableau workbook files are not bundled. The public links above provide the completed interactive Tableau presentation.

From a fresh clone of this repository, obtain the [official Dashboard Royale bundle](https://github.com/tamu-datathon-org/dashboard-royale) and build:

```sh
git clone --depth 1 https://github.com/tamu-datathon-org/dashboard-royale.git challenge-data
cd royale-lab
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 build_analysis.py --data ../challenge-data/data
python3 prepare_tableau_support.py
ROYALE_DATA=../challenge-data/data python3 -m unittest discover -s tests -v
python3 serve.py
```

Open **http://127.0.0.1:8501** for the companion dashboard. Ctrl+C stops the server. Rebuilding and running this default server make no Gemini generation calls. Input hashes are checked against the supplied manifest; the included input audit records the data used for the submitted analysis. Future challenge-data releases can produce different results.

For optional new Gemini generations, follow [the key setup and billing guide](royale-lab/docs/GEMINI_GUIDE.md). Keep credentials in the ignored local `.env`, use an eligible free-tier project where available, and preserve the local allowance database. Never put an API key into Tableau or browser code.

## Repository layout

| Path | Contents |
| --- | --- |
| `royale-lab/` | Analysis, forecast, API server, web source, tests, helper CSVs, and documentation |
| `royale-lab/submission/` | Evidence, disclosure, genuine Gemini output, methodology, and presentation drafts |
| `submission/` | Source and combined submission archives |
| `refresh_github_source.py` | Refreshes the source snapshot from the original author's local working folder; makes no API calls or Git changes |
| `test.py` | Original repository file, retained |

In the original author workspace, the local challenge checkouts are ignored and retain their own Git repositories. After editing `dashboard-royale/royale-lab`, run `python3 refresh_github_source.py` from the repository root, review the diff, and stage only the intended source snapshot. Fresh clones can edit `royale-lab/` directly; they do not need the refresh helper.

Challenge data, catalogue prices, and participant requirements originate from the official Dashboard Royale bundle. Only the intended synthetic challenge analysis and reviewed derived outputs are shared here.
