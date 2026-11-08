# Tableau helper sources

Run `python3 prepare_tableau_support.py` from royale-lab after rebuilding the main analysis. These tables derive from the existing audited artifacts; no external API calls are made.

- player_concentration.csv: full Jan–June 2025 tracked-player wagering curve, 101 points. It is fixed to the full period and does not respond to guest month/cohort filters. Use AVG(player_share) and AVG(cumulative_wager_share), and percentile on Detail.
- decision_comparison.csv: one catalogue unit each for technician and promotion. The effect percentages have different denominators. Use separate scenario parameters; never imply the required effects are estimated causal effects.
- recommended_plan.csv: draft inspection and preserved-budget rows from the existing analysis. Review with the team; inspection value is information, not assumed recovered cash.

Source data are fictional/synthetic. Publish this challenge analysis with its evidence and AI disclosure.
