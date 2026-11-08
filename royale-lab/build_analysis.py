"""Rebuild every chart input, Tableau export and evidence note from the supplied data."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import zipfile

import numpy as np
import pandas as pd
from plotly.offline import get_plotlyjs

from analysis import numeric, prepare_daily, machine_summary, player_summary, action_cost, validate_plan, SUM_COLUMNS
from forecasting import run_forecast
from gemini_briefing import briefing_context

ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parent / "data"


def records(df):
    return json.loads(df.to_json(orient="records", date_format="iso", double_precision=6))


def packed(df):
    """Dictionary encode text columns, preserving names and missing values."""
    frame = df.copy()
    dictionaries = {}
    for column in frame:
        if pd.api.types.is_datetime64_any_dtype(frame[column]):
            frame[column] = frame[column].dt.strftime("%Y-%m-%d")
        if pd.api.types.is_object_dtype(frame[column]) or pd.api.types.is_string_dtype(frame[column]):
            values, unique = pd.factorize(frame[column].fillna("Unknown"), sort=True)
            dictionaries[column] = unique.tolist()
            frame[column] = values
    return {"columns": frame.columns.tolist(), "dictionaries": dictionaries,
            "rows": json.loads(frame.to_json(orient="values", double_precision=4))}


def verify_sources(data_dir):
    manifest = json.loads((data_dir / "manifest.json").read_text())
    by_path = {item["path"]: item for item in manifest["files"]}
    used = ["1_prepared_views/prepared_daily_view", "1_prepared_views/property_day", "1_prepared_views/player_period",
            "2_machine_decision/machine_day", "2_machine_decision/game_math", "2_machine_decision/floor_locations",
            "2_machine_decision/action_catalog", "4_context/events", "2_machine_decision/floor_walkways"]
    audit = []
    for stem in used:
        relative = stem + ".parquet"
        file = data_dir / relative
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        if digest != by_path[relative]["sha256"]:
            raise ValueError(f"Input does not match the supplied manifest: {relative}")
        audit.append({"file": relative, "sha256": digest, "rows": by_path[relative].get("rows")})
    return manifest, audit


def build(data_dir=INPUT, output=ROOT / "dist"):
    data_dir, output = Path(data_dir), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    downloads = output / "downloads"
    downloads.mkdir(exist_ok=True)
    assets = output / "assets"
    assets.mkdir(exist_ok=True)
    manifest, audit = verify_sources(data_dir)
    read = lambda name: pd.read_parquet(data_dir / (name + ".parquet"))
    daily_source = read("1_prepared_views/prepared_daily_view")
    property_daily = numeric(read("1_prepared_views/property_day"))
    property_daily["gaming_date"] = pd.to_datetime(property_daily.gaming_date)
    players = numeric(read("1_prepared_views/player_period"))
    daily = prepare_daily(daily_source, read("2_machine_decision/machine_day"),
                          read("2_machine_decision/game_math"), read("2_machine_decision/floor_locations"))
    machines = machine_summary(daily)
    catalogue = read("2_machine_decision/action_catalog")
    catalogue["incompatibility_group"] = catalogue.incompatibility_group.fillna("")
    catalogue["cost_30_days_usd"] = catalogue.apply(lambda row: action_cost(row, 1), axis=1)
    events = read("4_context/events")
    for c in ["start_date", "end_date", "announced_date"]:
        events[c] = events[c].astype(str)
    walkways = read("2_machine_decision/floor_walkways")
    closures = walkways[walkways.closed_from_utc.notna()].copy()
    for c in ["closed_from_utc", "closed_to_utc"]:
        closures[c] = closures[c].dt.strftime("%Y-%m-%d")
    forecast, holdout, future = run_forecast(property_daily)
    unique_players = player_summary(players)

    # Accounting checks run on unrounded data, before producing artifacts.
    checks = {}
    def check(name, condition):
        checks[name] = bool(condition)
        if not condition:
            raise AssertionError(name)
    check("machine_day_unique", not daily.duplicated(["machine_id", "gaming_date"]).any())
    check("player_month_unique", not players.duplicated(["player_id", "period_month"]).any())
    check("machine_accounting", np.allclose(daily.coin_in_usd - daily.payout_usd, daily.house_win_usd, atol=.005))
    check("player_sign", np.allclose(players.tracked_payout_usd - players.tracked_coin_in_usd, players.tracked_net_usd, atol=.005))
    check("exposure_bounds", ((daily.available_hours >= 0) & (daily.available_hours <= daily.scheduled_hours + 1e-7)).all())
    check("inactive_rows_excluded", len(daily_source) - len(daily) == int((~daily_source.active).sum()))
    for col in ["coin_in_usd", "payout_usd", "house_win_usd", "theo_usd"]:
        a = daily.groupby("gaming_date")[col].sum().sort_index()
        b = property_daily.set_index("gaming_date")[col].sort_index()
        check("reconciles_property_" + col, np.allclose(a, b, atol=.005))
    check("property_contribution_no_double_comp", np.allclose(
        property_daily.house_win_usd + property_daily.pos_cash_usd - property_daily.pos_cogs_usd -
        property_daily.machine_supplied_costs_usd - property_daily.tech_labor_cost_usd,
        property_daily.contribution_after_supplied_costs_usd, atol=.005))
    check("forecast_test_after_training", forecast["train_end"] < forecast["test_start"])
    check("future_nonnegative", (future.forecast_coin_in_usd >= 0).all())

    # Property contribution includes F&B and tech labor; machine contribution does not.
    property_daily["expected_contribution_usd"] = (property_daily.theo_usd + property_daily.pos_cash_usd -
        property_daily.pos_cogs_usd - property_daily.machine_supplied_costs_usd - property_daily.tech_labor_cost_usd)
    by_day = daily.groupby("gaming_date")[["scheduled_hours", "downtime_hours", "opportunity_coin_in_usd", "opportunity_theo_usd"]].sum()
    property_daily = property_daily.merge(by_day, on="gaming_date", validate="one_to_one")
    property_daily["month"] = property_daily.gaming_date.dt.strftime("%Y-%m")
    property_daily["comp_reinvestment_ratio"] = property_daily.comp_cost_usd / property_daily.theo_usd.replace(0, np.nan)
    month_sums = ["coin_in_usd", "payout_usd", "house_win_usd", "theo_usd", "comp_cost_usd", "pos_cash_usd", "pos_cogs_usd", "contribution_after_supplied_costs_usd", "expected_contribution_usd", "available_machine_hours", "scheduled_hours", "downtime_hours", "opportunity_theo_usd"]
    monthly = property_daily.groupby("month", as_index=False)[month_sums].sum()
    monthly["days"] = property_daily.groupby("month").size().to_numpy()
    monthly["daily_coin_in_usd"] = monthly.coin_in_usd / monthly.days
    monthly["comp_reinvestment_ratio"] = monthly.comp_cost_usd / monthly.theo_usd
    monthly["availability_ratio"] = monthly.available_machine_hours / monthly.scheduled_hours
    # Exact, order-defined bridge between the last two months' daily wagering.
    # This separates exposure, utilization and intensity without a causal claim.
    recent = []
    for month in [monthly.iloc[-2].month, monthly.iloc[-1].month]:
        block = property_daily[property_daily.month == month]
        recent.append({"month": month,
                       "daily_coin": float(block.coin_in_usd.mean()),
                       "daily_available": float(block.available_machine_hours.mean()),
                       "occupancy": float(block.occupied_machine_hours.sum() / block.available_machine_hours.sum()),
                       "wager_intensity": float(block.coin_in_usd.sum() / block.occupied_machine_hours.sum())})
    previous, current = recent
    bridge = {
        "from_month": previous["month"], "to_month": current["month"],
        "start_daily_coin_in_usd": previous["daily_coin"],
        "end_daily_coin_in_usd": current["daily_coin"],
        "exposure_effect_usd": (current["daily_available"] - previous["daily_available"]) * previous["occupancy"] * previous["wager_intensity"],
        "occupancy_effect_usd": current["daily_available"] * (current["occupancy"] - previous["occupancy"]) * previous["wager_intensity"],
        "intensity_effect_usd": current["daily_available"] * current["occupancy"] * (current["wager_intensity"] - previous["wager_intensity"]),
        "assumptions": "Sequential bridge: available hours per day, then occupied/available hours, then wagers/occupied hour. Contributions depend on this order. Weekday mix, events and other confounding can affect each factor; these are descriptive accounting effects, not causal treatment effects.",
    }
    check("demand_bridge_reconciles", abs(bridge["start_daily_coin_in_usd"] + bridge["exposure_effect_usd"] + bridge["occupancy_effect_usd"] + bridge["intensity_effect_usd"] - bridge["end_daily_coin_in_usd"]) < .01)
    june = daily[daily.gaming_date >= "2025-06-01"]
    june_rates = {"downtime_hours_per_day": float(june.downtime_hours.sum() / 30),
                  "opportunity_theo_per_day_usd": float(june.opportunity_theo_usd.sum() / 30)}
    tech = catalogue[catalogue.action_type_id == "A-TECH-SHIFT"].iloc[0]
    promo = catalogue[catalogue.action_type_id == "A-PROMO"].iloc[0]
    promo_ready = pd.Timestamp("2025-07-01") + pd.Timedelta(days=int(promo.lead_days))
    weekend_choices = []
    for _, first in future.iterrows():
        if first.gaming_date < promo_ready or first.gaming_date.day_of_week != 5:
            continue
        weekend = future[future.gaming_date.between(first.gaming_date, first.gaming_date + pd.Timedelta(days=1))]
        if len(weekend) == 2:
            weekend_choices.append(weekend)
    # A declared planning choice, not a treatment-effect optimizer: use the first
    # eligible complete Saturday/Sunday weekend; baseline demand is not event lift.
    promo_weekend = weekend_choices[0]
    tech_days = max(0, 30 - int(tech.lead_days))
    tech_opportunity = june_rates["opportunity_theo_per_day_usd"] * tech_days
    tech_cost, promo_cost = action_cost(tech, 1), action_cost(promo, 1)
    comparison = {
        "technician": {"action_type_id": "A-TECH-SHIFT", "cost_usd": tech_cost,
                       "lead_days": int(tech.lead_days), "benefit_days": tech_days,
                       "gross_recovery_scenario_usd": tech_opportunity,
                       "break_even_recovery_fraction": tech_cost / tech_opportunity,
                       "break_even_theo_per_day_usd": tech_cost / tech_days,
                       "net_at_full_gross_recovery_usd": tech_opportunity - tech_cost},
        "promotion": {"action_type_id": "A-PROMO", "cost_usd": promo_cost,
                      "lead_days": int(promo.lead_days), "event_days": len(promo_weekend),
                      "dates": promo_weekend.gaming_date.dt.strftime("%Y-%m-%d").tolist(),
                      "baseline_wagers_usd": float(promo_weekend.forecast_coin_in_usd.sum()),
                      "break_even_additional_wagers_usd": promo_cost / forecast["assumed_theo_hold"],
                      "break_even_lift_fraction": promo_cost / promo_weekend.expected_theo_usd.sum()},
        "note": "One catalogue unit each. Technician: July 8–30 recovery at June peer rates, optimistically 100% incremental and fully recoverable. Promotion: first eligible complete Saturday/Sunday weekend, July 19–20, with unchanged June expected hold. No extra F&B margin, comp expense or cannibalization is included; add these to a final experiment budget. These are break-even requirements, not causal forecasts."
    }

    inspection = machines[machines.inspection_signal].sort_values("luck_z")
    inspection_targets = inspection.head(5).machine_id.tolist()
    plan = ([{"action_type_id": "A-INSPECT", "quantity": len(inspection_targets), "targets": inspection_targets}]
            if inspection_targets else [])
    cost = validate_plan(plan, records(catalogue))
    recommendations = [{"id": "R-FORECAST", "title": "Use forecast peaks to plan coverage; test promotions before scaling",
        "action": "Operational scheduling guidance; no incremental funded action assumed",
        "cost_usd": 0, "evidence": ["F-01", "F-02"],
        "effect": "The forecast estimates baseline wagering demand, not the causal lift from staffing or a promotion.",
        "measurement": "Compare forecast MAE, available hours and contribution per available hour; randomize any promotion pilot.",
        "uncertainty": "Only six months; event uplift and operational capacity are not identified by the demand model."}]
    if inspection_targets:
        recommendations.append({"id": "R-INSPECT", "title": "Verify the strongest negative payout residual",
            "action": f"A-INSPECT: {', '.join(inspection_targets)}", "cost_usd": cost, "evidence": ["M-01"],
            "effect": "Information from paytable/configuration inspection; no assumed cash recovery.",
            "measurement": "Record inspection findings, compare configured/verified paytable, and monitor subsequent residuals on new data.",
            "uncertainty": "Normal approximation and independent-spin variance assumptions; a signal is not proof of a fault or misconduct."})
    recommendations.append({"id": "R-HOLD", "title": "Preserve the remaining budget pending evidence",
        "action": "A-HOLD", "cost_usd": 0, "unspent_usd": 100000 - cost, "evidence": ["B-01", "D-01"],
        "effect": "Avoid committing funds to unmeasured uplift. Revisit after an inspection or controlled experiment.",
        "measurement": "Require a priced target, lead time, break-even benefit and an outcome measurement plan before spending.",
        "uncertainty": "The catalogue supplies costs, not treatment effects. Lost-play estimates can include substitution to other machines."})

    # Tableau exports are intentionally separate fact tables; no many-to-many joins.
    tableau_columns = ["machine_id", "gaming_date", "month", "local_weekday", "zone_id", "zone_name", "bank_id",
                       "location_id", "manufacturer", "theme", "config_id", "configured_rtp", "volatility_class",
                       "coin_in_usd", "payout_usd", "house_win_usd", "theo_usd", "available_hours", "scheduled_hours",
                       "occupied_hours", "downtime_hours", "faults_opened", "payout_variance_usd2",
                       "contribution_after_supplied_costs_usd", "expected_contribution_usd",
                       "opportunity_coin_in_usd", "opportunity_theo_usd", "carded_coin_in_usd", "x_m", "y_m"]
    export_frames = {
        "machine_day": daily[tableau_columns], "machine_summary": machines, "property_day": property_daily,
        "property_month": monthly, "player_month": players, "action_catalog": catalogue,
        "forecast_holdout": holdout, "forecast_july": future,
        "forecast_metrics": pd.DataFrame(forecast["metrics"]), "events": events,
    }
    guest_month = players.groupby(["period_month", "opening_tier", "home_region", "age_band"], dropna=False).agg(
        player_months=("player_id", "size"), tracked_coin_in_usd=("tracked_coin_in_usd", "sum"),
        tracked_payout_usd=("tracked_payout_usd", "sum"), tracked_net_usd=("tracked_net_usd", "sum"),
        theo_usd=("theo_usd", "sum"), comp_cost_usd=("comp_cost_usd", "sum"),
        tracked_contribution_usd=("tracked_contribution_usd", "sum")).reset_index()
    export_frames["guest_segment_month"] = guest_month
    export_frames["demand_bridge"] = pd.DataFrame([bridge])
    for name, frame in export_frames.items():
        frame.to_csv(downloads / (name + ".csv"), index=False, float_format="%.6f")

    summary = {
        "coin_in_usd": float(property_daily.coin_in_usd.sum()),
        "house_win_usd": float(property_daily.house_win_usd.sum()),
        "theo_usd": float(property_daily.theo_usd.sum()),
        "property_contribution_usd": float(property_daily.contribution_after_supplied_costs_usd.sum()),
        "downtime_hours": float(daily.downtime_hours.sum()),
        "active_machine_days": len(daily), "off_floor_rows_excluded": len(daily_source) - len(daily),
        "tracked": unique_players, "june_opportunity": june_rates,
    }
    selected_metric = next(m for m in forecast["metrics"] if m["selected"])
    baseline_metric = next(m for m in forecast["metrics"] if m["model"] == "mean")
    improvement = 1 - selected_metric["test_mae_usd"] / baseline_metric["test_mae_usd"]
    top = machines.sort_values("luck_z").iloc[0]
    evidence = [
        {"id": "F-01", "claim": f"{forecast['selected_label']} was selected using only pre-May validation.",
         "source": "property_day → forecasting.run_forecast → forecast_metrics.csv",
         "result": f"May–June MAE ${selected_metric['test_mae_usd']:,.0f}; constant-mean MAE ${baseline_metric['test_mae_usd']:,.0f}; relative reduction {improvement:.1%}.",
         "alternative": "A constant mean can be sufficient if weekday patterns weaken.",
         "limitation": "One final 61-day holdout; models and tuning rules are declared in source."},
        {"id": "F-02", "claim": "July forecast is a baseline-demand planning scenario.",
         "source": "property_day → model refit through June 30 → forecast_july.csv",
         "result": f"July 1–30 expected wagers ${future.forecast_coin_in_usd.sum():,.0f}; expected contribution after supplied costs ${future.expected_contribution_usd.sum():,.0f}.",
         "alternative": "Changes in events, availability or game mix can shift demand and expected hold.",
         "limitation": "Future actuals are unavailable. Contribution uses June expected hold, F&B margin and cost assumptions; it is not realized or full net profit."},
        {"id": "F-03", "claim": "Recent demand changes can be separated into exposure, occupancy and wagering intensity.",
         "source": "property_day → daily coin-in = available hours/day × occupied/available hours × wagers/occupied hour",
         "result": f"May→June change ${current['daily_coin']-previous['daily_coin']:,.0f}/day: exposure ${bridge['exposure_effect_usd']:,.0f}, occupancy ${bridge['occupancy_effect_usd']:,.0f}, intensity ${bridge['intensity_effect_usd']:,.0f}.",
         "alternative": "Weekday composition, event timing, guest/game mix and changing demand can drive the components.",
         "limitation": bridge["assumptions"]},
        {"id": "B-02", "claim": "Compare one technician package with a two-day promotion using explicit break-even requirements.",
         "source": "action_catalog + June peer-rate downtime opportunity + forecast_july; one unit each",
         "result": f"Technician: ${tech_cost:,.0f} cost versus ${tech_opportunity:,.0f} gross recovery scenario over {tech_days} days, requiring {tech_cost/tech_opportunity:.1%} recovery. Promotion July 19–20: ${promo_cost:,.0f} cost requires ${comparison['promotion']['break_even_additional_wagers_usd']:,.0f} incremental wagers, or {comparison['promotion']['break_even_lift_fraction']:.1%} above baseline weekend demand.",
         "alternative": "A technician could create other benefits not priced here. A promotion can shift existing visits rather than add demand, and extra comps can raise its cost.",
         "limitation": comparison["note"]},
        {"id": "M-01", "claim": "Payout variation is assessed against configured game variance before considering replacement.",
         "source": "machine_day.sum_bet_squared × game_math.payout_multiplier_variance / 10,000; aggregated by machine",
         "result": f"Most negative residual: {top.machine_id}, ${top.luck_residual_usd:,.0f}; z={top.luck_z:.2f}; Bonferroni-adjusted p={top.luck_p_bonferroni:.4g} across {len(machines)} machines.",
         "alternative": "Random variation, approximation error or configuration/data mismatch can explain an unusual residual.",
         "limitation": "Independent spins and published variance are assumed; 95% screening controls multiplicity approximately, not causality. Filtered chart signals are exploratory."},
        {"id": "D-01", "claim": "Downtime is an exposure loss; its financial value requires a counterfactual.",
         "source": "machine_day scheduled/available seconds; prepared_daily_view zone × config × weekday peer rates",
         "result": f"{daily.downtime_hours.sum():,.1f} unavailable machine-hours; gross expected-win opportunity scenario ${daily.opportunity_theo_usd.sum():,.0f}.",
         "alternative": "Guests may substitute to another machine, and busy-period rates may differ from healthy-period rates.",
         "limitation": "This is not observed lost revenue. Use 0–100% realization/recovery sensitivities; machine pooling includes own healthy exposure."},
        {"id": "G-01", "claim": "Tracked player outcomes use payouts minus wagers and distinct players across months.",
         "source": "player_period → group by player_id after month filters → sum monetary fields",
         "result": f"{unique_players['unique_tracked_players']:,} tracked players; net gaming result ${unique_players['tracked_player_net_usd']:,.0f}; top 1% wager share {unique_players['top_1pct_wager_share']:.1%}.",
         "alternative": "Carded behavior may differ from uncarded behavior; one person may also play without a card.",
         "limitation": "Guest analysis uses complete months and no machine/zone attribution. Concentration does not justify encouraging heavy losers to gamble more."},
        {"id": "C-01", "claim": "Comp reinvestment is redeemed economic cost divided by theo; costs are subtracted once.",
         "source": "property_day.comp_cost_usd / theo_usd; property contribution uses pos_cogs_usd once",
         "result": f"January ratio {monthly.iloc[0].comp_reinvestment_ratio:.2%}; June {monthly.iloc[-1].comp_reinvestment_ratio:.2%}.",
         "alternative": "Redemption timing, wager mix and guest mix can shift ratios without a policy effect.",
         "limitation": "A before/after comparison does not measure causal loyalty-program lift."},
        {"id": "B-01", "claim": "Fund at most three catalogue action types, respecting lead times, limits and conflicts.",
         "source": "action_catalog → analysis.action_cost / validate_plan → interactive scenario planner",
         "result": f"Draft inspection cost ${cost:,.0f}; preserved budget ${100000-cost:,.0f}.",
         "alternative": "A controlled promotion or staffing intervention may be worthwhile if credible benefit exceeds break-even.",
         "limitation": "Action uplift is unknown. The planner exposes assumptions instead of claiming an optimal causal allocation."},
    ]
    machine_cols = ["machine_id", "gaming_date", "zone_name", "bank_id", "manufacturer", "theme",
                    "coin_in_usd", "payout_usd", "house_win_usd", "theo_usd", "available_hours", "scheduled_hours",
                    "occupied_hours", "downtime_hours", "faults_opened", "payout_variance_usd2",
                    "contribution_after_supplied_costs_usd", "expected_contribution_usd",
                    "opportunity_coin_in_usd", "opportunity_theo_usd", "carded_coin_in_usd", "x_m", "y_m"]
    guest_cols = ["player_key", "period_month", "opening_tier", "home_region", "age_band",
                  "tracked_coin_in_usd", "tracked_payout_usd", "tracked_net_usd", "theo_usd", "comp_cost_usd", "tracked_contribution_usd"]
    web_players = players.copy()
    web_players["player_key"] = pd.factorize(players.player_id, sort=True)[0]
    payload = {"meta": {"title": "The Gilded Ace · Decision Room", "release": manifest["version"],
                         "data_start": "2025-01-01", "data_end": "2025-06-30", "planning_as_of": "2025-06-30",
                         "synthetic": True, "currency": "USD", "zone_names": sorted(daily.zone_name.unique().tolist()),
                         "months": sorted(players.period_month.unique().tolist()), "input_audit": audit,
                         "checks": checks, "interval_note": forecast["interval_note"]},
               "summary": summary, "daily": packed(daily[machine_cols]), "guests": packed(web_players[guest_cols]),
               "property": records(property_daily), "monthly": records(monthly), "machines": records(machines),
               "forecast": forecast, "holdout": records(holdout), "future": records(future),
               "demand_bridge": bridge,
               "staffing_promotion_comparison": comparison,
               "actions": records(catalogue), "events": records(events), "closures": records(closures),
               "recommendations": recommendations, "draft_plan": plan, "evidence": evidence}
    (output / "data.json").write_text(json.dumps(payload, separators=(",", ":"), allow_nan=False))
    _, briefing_topics = briefing_context(payload)
    (output / "ai_topics.json").write_text(json.dumps({"topics": briefing_topics}, separators=(",", ":")))
    (downloads / "input_audit.json").write_text(json.dumps({"release": manifest["version"], "inputs": audit, "checks": checks}, indent=2))
    (downloads / "forecast_methodology.json").write_text(json.dumps(forecast, indent=2))
    (downloads / "staffing_promotion_comparison.json").write_text(json.dumps(comparison, indent=2))
    (downloads / "draft_recommendations.json").write_text(json.dumps(recommendations, indent=2))
    evidence_md = "# Claims & Evidence appendix\n\nFictional casino; synthetic challenge data. Draft findings for team review.\n\n"
    for item in evidence:
        evidence_md += f"## {item['id']}: {item['claim']}\n\n- Query / transformation: {item['source']}\n- Result: {item['result']}\n- Alternative: {item['alternative']}\n- Limitation: {item['limitation']}\n\n"
    (downloads / "CLAIMS_AND_EVIDENCE.md").write_text(evidence_md)
    for file in (ROOT / "web").iterdir():
        if file.is_file():
            shutil.copy2(file, output / file.name)
    (assets / "plotly.min.js").write_text(get_plotlyjs())
    for doc in (ROOT / "docs").glob("*.md"):
        shutil.copy2(doc, downloads / doc.name)
    with zipfile.ZipFile(downloads / "tableau_exports.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name in export_frames:
            archive.write(downloads / (name + ".csv"), arcname=name + ".csv")
        for doc in downloads.glob("*.md"):
            archive.write(doc, arcname=doc.name)
    result = {"output": str(output), "checks": checks, "selected_model": forecast["selected_label"],
              "test_mae_usd": selected_metric["test_mae_usd"], "baseline_mae_usd": baseline_metric["test_mae_usd"],
              "july_coin_in_usd": float(future.forecast_coin_in_usd.sum()),
              "july_expected_contribution_usd": float(future.expected_contribution_usd.sum()),
              "inspection_targets": inspection_targets}
    print(json.dumps(result, indent=2))
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=INPUT)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    build(args.data, args.output)
