# Gemini integration — quick setup and Tableau handoff

The project includes a working Gemini REST API integration for management explanations. It uses the audited forecast, machine, guest and budget evidence. The key stays on your Python server. Setup and opening the page do not send generation requests.

## 1. Create a key in the credited project

1. Open https://aistudio.google.com/apikey and sign in.
2. Click **Create API key**. Choose the Google Cloud project associated with your **$10 Gemini credits**. If you are unsure which project owns the credit, check AI Studio's billing/credits page before generating anything.
3. Copy the newly created key. New keys use Google's current authorization-key setup.
4. Disable prepaid automatic reload if enabled. Set an AI Studio project spending cap of **$5** if available as an additional safeguard. Google's caps can lag; the local request allowance below is the primary application control.

No billing upgrades or credit purchases are performed by this project. Other applications sharing the account are outside this application's allowance.

Official key instructions: https://ai.google.dev/gemini-api/docs/api-key

## 2. Store the key locally

Run these commands in Terminal or VS Code's integrated terminal:

```sh
cd /Users/alejandrorojo/Documents/Datathon_2026/dashboard-royale/royale-lab
python3 gemini_setup.py
```

Paste the key at the hidden prompt and press Enter. The characters will not appear while you enter them. The command saves the key in an ignored `.env` file with permissions limited to your user. It does not make an API request. The server reads this file automatically; there is no extra shell export or package installation.

Keep the key out of chat, Tableau, screenshots, public repositories and browser code. `.env` is intentionally excluded from source archives and Git.

## 3. Start the briefing page

```sh
python3 serve.py --enable-gemini
```

Open **http://127.0.0.1:8501/ai.html**. If the port is busy, use `python3 serve.py --enable-gemini --port 8502` and open the same path on port 8502. The terminal must stay running while generating explanations. Ctrl+C stops the server.

The AI page is lightweight: it loads a small evidence payload and no Plotly library or large machine/player tables. You can keep your completed Tableau workbooks closed while using it.

## 4. Generate a real explanation

Choose a topic, inspect its evidence, then click **Generate with Gemini**:

- Demand & forecast
- Machine health
- Tracked guests & loyalty
- Staffing & promotion decisions

One click requests at most one new response. Opening the page and changing topics do not generate responses. An existing response for the same facts/model is reused. No placeholder explanations are presented as generated output. Failures do not retry automatically.

Each response preserves its scope, evidence IDs, model and timestamp. The page shows the evidence and alternative explanations for review. It uses the fixed declared analysis, not whatever filter is currently selected in your Tableau workbook.

## 5. Bring the generated explanation into Tableau

After at least one successful generation, these files are created:

- `tableau_support/gemini_insights.csv` — local Tableau source
- `dist/downloads/gemini_insights.csv` and `.json` — downloadable/cached presentation outputs
- `submission/GEMINI_BRIEF.md` — generated text and provenance
- `submission/GEMINI_USAGE.json` — conservative local usage record

In Tableau:

1. Select **Data → New Data Source → Text File**.
2. Open `tableau_support/gemini_insights.csv`.
3. Create a **new blank worksheet** and select **gemini_insights** in the Data pane.
4. Rename it **Gemini Management Briefing**.
5. Drag **Topic → Filters**, choosing one topic such as `forecast`.
6. Right-click that filter → **Show Filter**; choose a single-value dropdown if desired.
7. Select **Text** on the Marks card and drag **Explanation → Text**.
8. Add **Evidence Ids**, **Scope**, **Model** and **Generated At Utc** to Tooltip.
9. Use approximately 11 pt left-aligned text and allow enough space for a short paragraph.
10. Add the sheet to your dashboard with a title such as **Gemini-generated management explanation**.
11. Add this visible scope note: **Full-analysis briefing; chart filters are not automatically sent to Gemini.**

The CSV has only one row per generated topic, so it adds little data volume. It contains text and provenance, never an API key. Existing charts, financial measures and forecast validation stay as they are.

After generating additional topics, refresh the CSV source in Tableau. If you are using an extract, refresh that extract too. Republish the workbook to update its Tableau Public copy; Public does not call your local Python server or regenerate explanations automatically.

The web page also offers **Download Tableau CSV**, **Download briefing**, and **Copy explanation**.

## Optional: generate all four topics from Terminal

After configuring the key:

```sh
python3 gemini_briefing.py --topic all
```

This performs at most four new bounded generation requests, sequentially, reusing any existing responses. It stops on a failure. Export an existing cache without sending any API calls:

```sh
python3 gemini_briefing.py --cached-only
```

## Cost allowance

Configured model: **gemini-3.5-flash-lite**. Verified standard prices: **$0.30 per million input tokens** and **$2.50 per million output/thinking tokens**.

- Every input is counted before generation; maximum 4,000 tokens.
- Maximum combined response/thinking output: 1,000 tokens.
- Maximum reserved token cost per attempted generation: **$0.0037**.
- Four topics reserve at most **$0.0148** at those prices.
- Maximum 500 generation attempts across this server and CLI: **$1.85** maximum token reserve at configured prices.
- The allowance persists in `.runtime/gemini.sqlite` across restarts. Failed/ambiguous attempts retain their full reservation.
- No automatic retries, fallback models, search tools, paid grounding, or agent loops.

Keep `.runtime` intact; deleting it resets the local counter. This control covers this application only. Provider prices, credit eligibility and any use from other applications remain account-level considerations. The local reserve is intentionally conservative, not a Google billing statement.

Prices: https://ai.google.dev/gemini-api/docs/pricing
Billing caps and latency: https://ai.google.dev/gemini-api/docs/billing

## Hosted versus local behavior

The existing Sites deployment is static. It can show the evidence and any generated briefings included in a later published build, but new API generations run through the local Python server. The published Tableau workbook displays the generated CSV text. It does not need or store your API key.

For a hackathon demo, show a real generation on the local page, then show that explanation in Tableau. That demonstrates the API integration without adding a new cloud backend.

## Troubleshooting: HTTP 402 (Payment Required)

Google documents 402 as a depleted Prepay balance. The application cannot fix billing by changing a prompt or retrying. No automatic retry or credit purchase occurs.

1. Open the API keys page in Google AI Studio. Note the project shown beside the key you entered locally; keep the key private.
2. Select that same project in AI Studio and open **Billing**. Check its **Gemini Prepay/Available credits** balance and any **No credits**, **Set up Prepay**, or account-status banner.
3. Confirm that the existing $10 is eligible for Gemini API usage and connected to this project's billing account. Promotional/Cloud credits are distinct from Gemini prepaid funds. Under Google's Prepay rules, even eligible promotional credits require a positive Prepay balance before they can be applied. Google Cloud welcome/free-trial credits may be ineligible entirely.
4. If the key belongs to the wrong project, create/select a key in the credited project, stop the server with Ctrl+C, run `python3 gemini_setup.py` again, and restart with `python3 serve.py --enable-gemini`. A shell-exported `GEMINI_API_KEY` overrides `.env`; if you previously exported an older key, run `unset GEMINI_API_KEY` in that terminal before restarting.
5. If the correct project has no usable balance, check with the hackathon credit provider before buying anything. This project's $10 limit does not authorize additional purchases or auto-reload. A free-tier project supporting this model is a possible alternative if available to your account; do not change the billing of a shared project just to test it.
6. If the correct project has a positive prepaid balance but still reports 402, inspect the billing-status banners and contact Google billing support or the credit provider. Billing changes can take time to propagate. Retry once only after the billing issue is resolved.

The local reservation is deliberately retained after a failed generation; it is not proof that Google charged your account. Keep `.runtime` intact. The app does not export a fabricated explanation when generation fails.

Official references: https://ai.google.dev/gemini-api/docs/api-errors and https://ai.google.dev/gemini-api/docs/billing

## Submission and disclosure

After generating and reviewing at least one real response, run:

```sh
python3 package_submission.py
```

This refreshes the source archive and submission package, includes generated briefings if present, and adds the successful briefing usage record to the packaged AI disclosure. The source disclosure template keeps the distinction between implementation/testing and actual later API usage.

The integration was tested with isolated simulated responses before a real key was configured. A live provider connection can be confirmed only after you create and enter your key and successfully generate a response.
