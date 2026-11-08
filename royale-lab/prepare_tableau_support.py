"""Produce small Tableau helper tables from the audited existing analysis artifacts.

No external requests. Run again after rebuilding the primary analysis artifacts.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOWNLOADS = ROOT / "dist/downloads"
OUTPUT = ROOT / "tableau_support"


def write_csv(name, rows):
    with (OUTPUT / name).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUTPUT.mkdir(exist_ok=True)
    data = json.loads((ROOT / "dist/data.json").read_text())
    comparison = data["staffing_promotion_comparison"]
    hold = data["forecast"]["assumed_theo_hold"]
    people = {}
    with (DOWNLOADS / "player_month.csv").open() as handle:
        for row in csv.DictReader(handle):
            key = row["player_id"]
            people[key] = people.get(key, 0.) + float(row["tracked_coin_in_usd"])
    values = sorted(people.values(), reverse=True)
    total = sum(values)
    expected = data["summary"]["tracked"]["tracked_coin_in_usd"]
    assert abs(total - expected) < .02
    cumulative = [0.]
    for value in values:
        cumulative.append(cumulative[-1] + value)
    curve = []
    for percentile in range(101):
        n = math.ceil(len(values) * percentile / 100)
        curve.append({"percentile": percentile, "player_share": n / len(values),
                      "cumulative_wager_share": cumulative[n] / total,
                      "players_included": n, "total_tracked_players": len(values),
                      "period_label": "January–June 2025; all tracked players"})
    assert abs(curve[-1]["cumulative_wager_share"] - 1) < 1e-10
    assert abs(curve[1]["cumulative_wager_share"] - data["summary"]["tracked"]["top_1pct_wager_share"]) < 1e-10
    write_csv("player_concentration.csv", curve)

    tech, promo = comparison["technician"], comparison["promotion"]
    scenarios = [
        {"action_name": "Extra technician shift", "action_type_id": "A-TECH-SHIFT",
         "cost_usd": tech["cost_usd"], "lead_days": tech["lead_days"],
         "benefit_days": tech["benefit_days"], "benefit_start": "2025-07-08", "benefit_end": "2025-07-30",
         "benefit_at_100pct_effect_usd": tech["gross_recovery_scenario_usd"],
         "break_even_effect": tech["break_even_recovery_fraction"],
         "effect_label": "Fraction of gross downtime opportunity recovered as incremental contribution",
         "expected_hold": hold,
         "assumption_note": "June peer-rate opportunity over 23 days; all recovered play treated as incremental. Full recovery is optimistic and excludes other possible staffing benefits."},
        {"action_name": "Two-day promotion weekend", "action_type_id": "A-PROMO",
         "cost_usd": promo["cost_usd"], "lead_days": promo["lead_days"],
         "benefit_days": promo["event_days"], "benefit_start": promo["dates"][0], "benefit_end": promo["dates"][-1],
         "benefit_at_100pct_effect_usd": promo["baseline_wagers_usd"] * hold,
         "break_even_effect": promo["break_even_lift_fraction"],
         "effect_label": "Incremental two-day wagers above forecast baseline, at unchanged expected hold",
         "expected_hold": hold,
         "assumption_note": "First complete eligible July weekend; no added F&B upside, comp expense or visit displacement. Extra costs raise break-even; this is not a predicted causal lift."}
    ]
    for row in scenarios:
        assert abs(row["break_even_effect"] * row["benefit_at_100pct_effect_usd"] - row["cost_usd"]) < .01
    write_csv("decision_comparison.csv", scenarios)

    actions = {a["action_type_id"]: a for a in data["actions"]}
    recommendations = {r["id"]: r for r in data["recommendations"]}
    plan = []
    for item in data["draft_plan"]:
        action = actions[item["action_type_id"]]
        recommendation = recommendations.get("R-INSPECT", {})
        plan.append({"action_name": action["name"], "action_type_id": item["action_type_id"],
                     "quantity": item["quantity"], "targets": ", ".join(item["targets"]),
                     "planned_cost_usd": item["quantity"] * action["cost_30_days_usd"],
                     "effect": recommendation.get("effect", "Requires team review"),
                     "uncertainty": recommendation.get("uncertainty", "Requires team review"),
                     "measurement": recommendation.get("measurement", "Requires team review"),
                     "evidence_ids": ", ".join(recommendation.get("evidence", [])),
                     "status": "Draft; team review required"})
    plan.append({"action_name": "Preserve remaining budget", "action_type_id": "A-HOLD",
                 "quantity": 0, "targets": "Unallocated July operating budget", "planned_cost_usd": 0,
                 "effect": "Preserve funds pending stronger evidence; not additional income.",
                 "uncertainty": "Promotion lift and additional technician benefits have not been identified causally.",
                 "measurement": "Require a costed intervention and control/measurement plan before committing funds.",
                 "evidence_ids": "B-01, B-02", "status": "Draft; team review required"})
    assert sum(r["planned_cost_usd"] for r in plan) <= 100000
    write_csv("recommended_plan.csv", plan)
    (OUTPUT / "README.md").write_text(
        "# Tableau helper sources\n\n"
        "Run `python3 prepare_tableau_support.py` from royale-lab after rebuilding the main analysis. "
        "These tables derive from the existing audited artifacts; no external API calls are made.\n\n"
        "- player_concentration.csv: full Jan–June 2025 tracked-player wagering curve, 101 points. "
        "It is fixed to the full period and does not respond to guest month/cohort filters. "
        "Use AVG(player_share) and AVG(cumulative_wager_share), and percentile on Detail.\n"
        "- decision_comparison.csv: one catalogue unit each for technician and promotion. "
        "The effect percentages have different denominators. Use separate scenario parameters; "
        "never imply the required effects are estimated causal effects.\n"
        "- recommended_plan.csv: draft inspection and preserved-budget rows from the existing analysis. "
        "Review with the team; inspection value is information, not assumed recovered cash.\n\n"
        "Source data are fictional/synthetic. Publish this challenge analysis with its evidence and AI disclosure.\n"
    )
    print(json.dumps({"output": str(OUTPUT), "concentration_points": len(curve),
                      "top_1pct_wager_share": curve[1]["cumulative_wager_share"],
                      "decision_rows": len(scenarios), "plan_cost_usd": sum(r["planned_cost_usd"] for r in plan),
                      "remaining_budget_usd": 100000 - sum(r["planned_cost_usd"] for r in plan)}, indent=2))


if __name__ == "__main__":
    main()
