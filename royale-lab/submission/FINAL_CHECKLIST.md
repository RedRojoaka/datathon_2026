# Final submission — stop adding features

The challenge requirements are in the supplied dashboard-royale/GUIDE.md, section 8. Model complexity and chart count are not scoring goals.

## Essential remaining work after Dashboards 3 and 4

1. Save a local packaged backup of each Tableau workbook.
2. Publish the workbooks and collect their public URLs, or submit interactive workbook files with opening instructions if using the file option. Test links in a private browser window.
3. Confirm the final recommendation, targets, cost, uncertain effect, and measurement plan. The supplied write-up currently proposes one $1,200 inspection of M-1158 and $98,800 preserved; edit it if your final decision differs.
4. Record a walkthrough of no more than two minutes using VIDEO_SCRIPT.md.
5. Paste the main write-up from WRITEUP_DRAFT.md, after reviewing it against the final visuals. The main text must remain under 400 words.
6. Attach the source code/transformation steps, Claims & Evidence appendix, and AI-use disclosure. Tableau workbook files preserve the calculations and dashboard definitions you created manually.
7. Complete the event's Devpost submission and check its published deadline and required upload fields. No deadline is inferred here.

## Four final functionality checks

- Change the historical analysis period.
- Drill into one bank or guest cohort.
- Find the time-based model validation.
- Trace the inspection recommendation to its evidence and limitation.

## Things you can skip

- More forecast models or another round of visual redesign.
- Databricks.
- A separate Evidence & Methods dashboard, if the required appendix and disclosure are attached or publicly linked.
- Combining all workbooks into one large workbook. Separate links are acceptable to organize as one project; ensure judges can find all of them.

## Links to fill in

- Executive outlook: https://public.tableau.com/app/profile/alejandro.rojo4194/viz/Datathon_26_Dashboard_1_v3/ExecutiveOutlook
- Machine performance: https://public.tableau.com/app/profile/alejandro.rojo4194/viz/Datathon_26_Dashboard_1_v2/Dashboard2
- Tracked guests and loyalty: https://public.tableau.com/app/profile/alejandro.rojo4194/viz/Dashboard_3_17941211263630/TrackedGuestsLoyalty
- Operations decisions and Gemini briefing: https://public.tableau.com/app/profile/alejandro.rojo4194/viz/Dashboard_4_TD2026/BudgetandActions
- Video: recording pending; add the final judge-accessible video URL before submission.
- Source code: https://github.com/RedRojoaka/datathon_2026 — reviewed source snapshot is being prepared; confirm the files have been pushed before submitting this link.

The generated submission archive does not include your manually created Tableau workbooks or video. Add their final links or files. The existing Sites preview is private and is not a substitute for a judge-accessible link.

## Reproduction

SOURCE_CODE.zip contains the Python and dashboard source, documentation, tests and Tableau helper tables. Extract royale-lab into the original supplied dashboard-royale bundle, then follow royale-lab/README.md. Alternatively pass the supplied data directory explicitly to build_analysis.py. Rebuild the analysis, then run prepare_tableau_support.py. Raw source data are supplied by the challenge and are not duplicated in the source archive.

No Gemini calls were made during implementation/testing. If you later enable Gemini, update AI_DISCLOSURE.md before submission. Do not claim it was used if it remained disabled.

## Requested Gemini feature

Gemini integration is included and a real budget briefing has been generated, reviewed, exported to tableau_support/gemini_insights.csv, and added to Dashboard 4. The saved text and provenance are in GEMINI_BRIEF.md, with the conservative local allowance record in GEMINI_USAGE.json. The refreshed package includes actual usage in its AI disclosure. A new provider call is not needed to demonstrate this saved explanation. Mocked test responses are never shipped as genuine briefings. New users should follow docs/GEMINI_GUIDE.md if they choose to configure their own key for new generations.
