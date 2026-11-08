# The Gilded Ace · Decision Room

A working Dashboard Royale analysis and executive dashboard. Demand forecasting is the main story; machine, guest, loyalty and budget views support the decision.

From the `royale-lab` directory:

```sh
python3 serve.py
```

Open **http://127.0.0.1:8501**. Generated data and the dashboard are already in `dist/`. There is no Node.js build step, CDN dependency, login requirement for local use, or API charge. Do not open `index.html` directly: chart inputs are loaded over HTTP.

If you downloaded the source-only submission archive or its GitHub copy, `dist/` is not included. Obtain the original challenge data and use the rebuild instructions below before starting the server. The source archive contains the code, Tableau helper CSVs, supporting documents, and a blank credential template; it excludes private credentials, local runtime state, and large generated datasets.

To rebuild after changing the analysis:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 build_analysis.py
python3 -m unittest discover -s tests -v
python3 serve.py
```

Python 3.11+ is required for the build. The prebuilt dashboard server uses only the Python standard library. Stop it with Ctrl+C. Use `python3 serve.py --port 8502` if the default port is busy.

- [Setup and analysis workflow](docs/START_HERE.md)
- [Tableau Public instructions and calculated fields](docs/TABLEAU_GUIDE.md)
- [Presentation options for team discussion](docs/PRESENTATION_OPTIONS.md)
- [AI-use disclosure](docs/AI_DISCLOSURE.md)
- [Gemini setup and Tableau integration](docs/GEMINI_GUIDE.md)
- [Publishing Tableau, first Gemini briefing, and safe GitHub upload](docs/PUBLISH_AND_SUBMIT.md)
- Generated CSVs and the Claims & Evidence appendix: `dist/downloads/`

The casino, data and action budget are fictional. July 2025 is the challenge's planning horizon, not today's calendar month. Contribution uses supplied costs; it is not full net profit.

## Gemini management briefing

The integration generates grounded explanations for four topics: forecast, machine health, guests/loyalty, and staffing/promotion decisions. It exports genuine responses to `tableau_support/gemini_insights.csv` for a small text worksheet in Tableau. The lightweight briefing page does not load the large chart datasets or Plotly. Create a key in the credited project at https://aistudio.google.com/apikey, then run:

```sh
python3 gemini_setup.py
python3 serve.py --enable-gemini
```

The setup prompt hides the key and stores it in the ignored local `.env` file. Open **http://127.0.0.1:8501/ai.html** and explicitly generate a topic. Opening the page makes no generation requests. A successful response saves its text, evidence IDs, scope, model and timestamp. Existing cached responses remain readable without a key. The static hosted copy is a reading/export view; new generations use the local Python server.

The key stays on the Python server. Only declared evidence IDs can be requested. An enduring SQLite allowance in `.runtime/gemini.sqlite` reserves $0.0037 before every generation, including failed attempts. It stops at 500 attempts ($1.85 maximum token reserve at the documented model prices); repeated evidence is cached. Four topics reserve at most $0.0148. Counted input is capped at 4,000 tokens and combined output/thinking at 1,000 tokens. No automatic retries, paid tools, batch jobs, or fallback models are enabled.

Keep `.runtime/` across restarts and deployments; do not delete it to reset the allowance. This local safeguard covers only this server, not other apps/keys sharing your account. Confirm credit eligibility, set an AI Studio project cap and disable prepaid automatic reload before enabling. No API call or credit usage was performed during implementation or automated testing.

## Source map

| File | Purpose |
| --- | --- |
| `build_analysis.py` | Validate inputs, build artifacts, export Tableau tables and evidence |
| `forecasting.py` | Pre-May model selection, frozen May–June test, July refit |
| `analysis.py` | Exposure/accounting logic, variance screening, action constraints |
| `web/` | Dashboard source; edit here, then rebuild |
| `dist/` | Generated dashboard and downloads; ready to serve |
| `serve.py` | Local server and optional evidence-explanation endpoint |
| `gemini_guard.py` | Persistent request allowance and bounded Gemini REST calls |
| `gemini_setup.py` | Hidden local API key setup; `.env` loading |
| `gemini_briefing.py` | Grouped evidence briefings and genuine-response Tableau exports |
| `package_submission.py` | Refresh archives and include recorded Gemini usage |
| `tests/` | Accounting, leakage, budget and API-allowance checks |

Input defaults to `../data`. To use another copy: `python3 build_analysis.py --data /path/to/dashboard-royale/data`. CSV exports at different grains are separate fact tables; avoid joining them row by row.

When testing against a separate data checkout, set `ROYALE_DATA=/path/to/dashboard-royale/data` for the test command. The repository-level README provides the complete source-only setup and the published Tableau links.
