# Publish Tableau, generate a Gemini briefing, and upload source to GitHub

## 1. Publish the completed Tableau workbooks

Work on one workbook at a time if memory is tight. Start by restoring the intended default date/cohort selections. Keep the fictional-data note, analysis period and scenario assumptions visible.

1. Save a local backup using **File → Save As**. Choose **Tableau Packaged Workbook (.twbx)** when offered; this bundles the workbook with its local data. Use meaningful names: `Gilded_Ace_01_Demand`, `Gilded_Ace_02_Machines`, `Gilded_Ace_03_Guests`, `Gilded_Ace_04_Budget`.
2. Select the completed dashboard tab before publishing.
3. Use **Server → Tableau Public → Save to Tableau Public**. Some Public editions expose **Save to Tableau Public** in the File menu instead.
4. Sign in to your Tableau Public account, enter a descriptive workbook name and save. The publishing process creates an extract of supported local file connections. If Tableau offers to create an extract, accept. If an error persists, record its exact wording rather than removing sources from your finished workbook.
5. The published workbook opens in your browser. Open the intended dashboard, click **Share**, then **Copy Link**. Save a link for every dashboard; one workbook may contain multiple dashboards.
6. Repeat for your other workbooks. Every worksheet inside a workbook is saved with that workbook; individual KPI publishing is unnecessary.
7. Paste each copied link into a private/incognito browser window. Confirm the actual dashboard renders without sign-in. Test the date controls, bank/machine drilldown, guest filters, scenario parameters and model-validation visibility. Restore defaults before your final save.

Tableau Public publishes workbook data publicly. Only synthetic challenge data and reviewed derived outputs belong in these workbooks. The API key, .env and runtime database must never be added as data sources. A workbook hidden from a profile is not a private access control.

Use the published Tableau links for judges. The existing owner-private Sites companion does not provide anonymous judge access.

Official help: https://help.tableau.com/current/pro/desktop/en-us/publish_workbooks_tableaupublic.htm
Packaged files: https://help.tableau.com/current/pro/desktop/en-us/save_savework_packagedworkbooks.htm

## 2. Configure Gemini without putting the key in chat or code

1. Visit https://aistudio.google.com/apikey and sign in to the account with your credits.
2. Identify the project holding the $10 credit. A key belongs to a project, so select that project when creating a key. Import an existing project through AI Studio's Projects page if necessary. Do not assume a new default project's balance includes the hackathon credit.
3. Create/copy a key for that project. Confirm the credit and billing settings. Disable prepaid automatic reload if enabled; an available $5 project cap is an extra safeguard. This project performs no upgrade or credit purchase.
4. Open VS Code's **Terminal → New Terminal** and run:

   ```sh
   cd /Users/alejandrorojo/Documents/Datathon_2026/dashboard-royale/royale-lab
   python3 gemini_setup.py
   ```

5. At `Gemini API key:`, paste the key and press Enter. The prompt hides every character. It saves an ignored `.env` with user-only permissions and makes no API call. Enter it at the prompt, not as a shell command.
6. Start the local server:

   ```sh
   python3 serve.py --enable-gemini
   ```

7. Leave the terminal running and open http://127.0.0.1:8501/ai.html. If an old server is running in another terminal, stop that server with Ctrl+C first. Alternatively use `python3 serve.py --enable-gemini --port 8502` and open http://127.0.0.1:8502/ai.html.
8. Select **Staffing & promotion decisions**, review the supplied evidence and click **Generate with Gemini** once. Opening the page or switching topics does not generate text. Read the resulting explanation against the evidence. If a request fails, record the displayed error; the app never retries automatically.

The configured model is `gemini-3.5-flash-lite`. At the configured $0.30/M input and $2.50/M output/thinking prices, each attempt reserves at most $0.0037; four topics reserve at most $0.0148. A persistent 500-attempt limit bounds the local token reserve to $1.85 at those prices. Preserve `.runtime/gemini.sqlite` locally across restarts; ignore it in Git. Other account usage and provider price/credit changes are separate from the application's limit.

Official key help: https://ai.google.dev/gemini-api/docs/api-key
Pricing: https://ai.google.dev/gemini-api/docs/pricing

## 3. Add the genuine briefing to Dashboard 4

After a successful generation, the server creates `tableau_support/gemini_insights.csv` and `submission/GEMINI_BRIEF.md` / `GEMINI_USAGE.json`.

1. Open your Dashboard 4 workbook.
2. Choose **Data → New Data Source → Text File** and open `royale-lab/tableau_support/gemini_insights.csv`.
3. Create a new blank worksheet, select **gemini_insights** in the Data pane and name the sheet **Gemini Management Briefing**. Do not mix fields from this source with the scenario source on one worksheet.
4. Drag **Topic → Filters** and select **budget**. Keep this filter on **Only This Worksheet**.
5. Choose **Text** on the Marks card; drag **Explanation → Text**. Leave Rows and Columns empty.
6. Add **Evidence Ids**, **Scope**, **Model**, and **Generated At Utc** to Tooltip.
7. Choose **Entire View** in the fit dropdown; use approximately 11 pt text. If hashes appear, enlarge the text cell with **Format → Cell Size → Taller** and give the sheet sufficient space in the dashboard.
8. Add the sheet to Dashboard 4. Title it **Gemini-generated management explanation** and add a visible note: **Full-analysis briefing; dashboard filters and scenario sliders are not automatically sent to Gemini.**
9. Save the local workbook, republish the same Tableau Public workbook, and check the published dashboard in a private browser window. Tableau Public displays the saved text; it does not make fresh API calls. Regenerate/refresh the CSV and republish to update it later.

The GitHub/Sites static pages cannot run the local Python API server. Demonstrate a live generation at localhost, or identify an existing response honestly as cached.

## 4. Prepare the GitHub source snapshot

The workspace contains nested Git repositories: Datathon_2026, the supplied dashboard-royale bundle, and the royale-lab companion. Keep their history/remotes unchanged. The simplest beginner workflow is a fresh GitHub repository populated from the source archive.

After reviewing your real briefing, run from royale-lab:

```sh
python3 package_submission.py
```

`submission/SOURCE_CODE.zip` contains code, `.gitignore`, a blank `.env.example`, web source, documentation, tests, small Tableau helper CSVs and supporting submission documents. It excludes actual `.env`, runtime databases, Git metadata, large raw/generated data and packaged Tableau workbooks. The combined `SUBMISSION_MATERIALS.zip` is for submission attachments, not the source repository's main contents.

1. Copy `SOURCE_CODE.zip` to Downloads and double-click it to extract.
2. Open the extracted `royale-lab` folder. In Finder, **Command+Shift+.** toggles hidden files; confirm `.gitignore` and `.env.example` are present.
3. On GitHub, create an empty public repository such as **gilded-ace-dashboard-royale**. Leave README, license and .gitignore initialization unchecked because the source already contains README/ignore files. Choose a license only when you have decided which license applies to your work.
4. Use **uploading an existing file** or **Add file → Upload files**. Upload the extracted folder's contents, including `.gitignore` and `.env.example`, to the repository root. Upload the actual source files rather than only the ZIP.
5. Enter a commit message such as **Add Dashboard Royale analysis and Gemini integration** and commit the upload. The web uploader creates the GitHub commit; no terminal Git commands are required.
6. Add the four public Tableau links and your video link to the GitHub README through its edit button, then commit that edit. Keep copied narrative consistent with the final submission.
7. Check that `.env`, `.runtime`, key files and credentials do not appear in GitHub. The blank `.env.example` is intentional. The reviewed Gemini explanation/usage metadata contain no credential by design and can be shared.

Do not upload the complete Datathon_2026 folder, supplied data bundle, virtual environment, videos or local credentials. Keep final Tableau `.twbx` files locally; link to the public workbooks in the README. GitHub Releases are an option for large reviewed workbook downloads. Browser uploads allow 25 MiB per file; normal Git blocks individual files over 100 MiB.

The source-only README explains how to rebuild using the supplied challenge data. A fresh source clone needs that rebuild before `serve.py` can run.

## Ignore rules and checks

Ignore rules are already added at the workspace root and royale-lab root. They cover `.env` variants, key-save temporary files, `.runtime`, SQLite files, common credential JSON names, private-key files, local credential stores, Python/Node environments, caches and Tableau recovery/extract files. Final `.twb` / `.twbx` files are not blanket-ignored.

Check rule behavior from royale-lab without displaying any secret:

```sh
git check-ignore -v .env .env.local .runtime/gemini.sqlite
git status --short --ignored
```

`.gitignore` protects untracked files from normal Git staging. It does not erase a previous commit or stop a browser upload or explicit `git add -f`. The source ZIP includes only allowed files and carries none of the existing Git history. If a real credential has ever been published, revoke/rotate it first; merely adding an ignore rule does not fix that exposure.

GitHub ignore help: https://docs.github.com/en/get-started/git-basics/ignoring-files
File limits: https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github
