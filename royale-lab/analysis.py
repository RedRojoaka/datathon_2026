"""Accounting, exposure adjustments, and catalogue-constrained action budgets."""
from __future__ import annotations

import math
import numpy as np
import pandas as pd


def numeric(df):
    df = df.copy()
    for column in df:
        if column == "bet_options_cents":
            continue
        if any(column.endswith(s) for s in ("_usd", "_cents", "_ratio")) or column in [
            "configured_rtp", "payout_multiplier_variance", "sum_bet_squared"]:
            df[column] = pd.to_numeric(df[column], errors="raise").astype(float)
    return df


def prepare_daily(daily, raw, math_table, locations):
    daily = numeric(daily)
    raw = numeric(raw)
    math_table = numeric(math_table)
    daily["gaming_date"] = pd.to_datetime(daily.gaming_date)
    raw["gaming_date"] = pd.to_datetime(raw.gaming_date)
    # Machine meters provide actual scheduled exposure, including DST and install days.
    exposure = raw.merge(math_table[["config_id", "payout_multiplier_variance"]],
                         on="config_id", how="left", validate="many_to_one")
    if exposure.payout_multiplier_variance.isna().any():
        raise ValueError("Missing game variance")
    exposure["payout_variance_usd2"] = exposure.sum_bet_squared * exposure.payout_multiplier_variance / 10000
    cols = ["machine_id", "gaming_date", "scheduled_seconds", "available_seconds", "payout_variance_usd2"]
    result = daily.merge(exposure[cols], on=["machine_id", "gaming_date"], validate="one_to_one")
    result = result[result.active].copy()
    result["scheduled_hours"] = result.scheduled_seconds / 3600
    result["downtime_hours"] = (result.scheduled_seconds - result.available_seconds).clip(lower=0) / 3600
    result["expected_contribution_usd"] = result.theo_usd - (
        result.lease_cost_usd + result.service_cost_usd + result.power_cost_usd + result.repair_cost_usd)
    result["coin_in_per_available_hour_usd"] = result.coin_in_usd / result.available_hours.replace(0, np.nan)
    result["theo_per_available_hour_usd"] = result.theo_usd / result.available_hours.replace(0, np.nan)
    # Pool comparable zone x configuration x weekday exposure; assume displaced demand
    # would not migrate to another machine. This is a gross opportunity scenario.
    keys = ["zone_id", "config_id", "local_weekday"]
    peers = result.groupby(keys, dropna=False)[["coin_in_usd", "theo_usd", "available_hours"]].sum()
    peers["peer_coin_rate"] = peers.coin_in_usd / peers.available_hours.replace(0, np.nan)
    peers["peer_theo_rate"] = peers.theo_usd / peers.available_hours.replace(0, np.nan)
    result = result.merge(peers[["peer_coin_rate", "peer_theo_rate"]], on=keys,
                          how="left", validate="many_to_one")
    result["opportunity_coin_in_usd"] = result.downtime_hours * result.peer_coin_rate
    result["opportunity_theo_usd"] = result.downtime_hours * result.peer_theo_rate
    result = result.merge(locations[["location_id", "x_m", "y_m"]], on="location_id",
                          how="left", validate="many_to_one")
    return result


SUM_COLUMNS = ["coin_in_usd", "payout_usd", "house_win_usd", "theo_usd", "available_hours",
               "scheduled_hours", "occupied_hours", "downtime_hours", "faults_opened",
               "payout_variance_usd2", "contribution_after_supplied_costs_usd", "expected_contribution_usd",
               "opportunity_coin_in_usd", "opportunity_theo_usd", "carded_coin_in_usd"]


def machine_summary(daily):
    totals = daily.groupby("machine_id")[SUM_COLUMNS].sum()
    metadata = daily.sort_values("gaming_date").groupby("machine_id").agg(
        zone_name=("zone_name", "last"), bank_id=("bank_id", "last"),
        manufacturer=("manufacturer", "last"), theme=("theme", "last"),
        volatility_class=("volatility_class", "last"), active_days=("gaming_date", "nunique"))
    result = totals.join(metadata).reset_index()
    result["observed_hold"] = result.house_win_usd / result.coin_in_usd.replace(0, np.nan)
    result["availability"] = result.available_hours / result.scheduled_hours.replace(0, np.nan)
    result["theo_per_available_hour_usd"] = result.theo_usd / result.available_hours.replace(0, np.nan)
    result["coin_in_per_available_hour_usd"] = result.coin_in_usd / result.available_hours.replace(0, np.nan)
    result["luck_residual_usd"] = result.house_win_usd - result.theo_usd
    result["luck_standard_error_usd"] = np.sqrt(result.payout_variance_usd2)
    result["luck_z"] = result.luck_residual_usd / result.luck_standard_error_usd.replace(0, np.nan)
    result["luck_p_two_sided"] = result.luck_z.map(lambda z: math.erfc(abs(z) / math.sqrt(2)) if pd.notna(z) else 1.)
    result["luck_p_bonferroni"] = (result.luck_p_two_sided * len(result)).clip(upper=1)
    result["inspection_signal"] = (result.luck_p_bonferroni < .05) & (result.luck_z < 0)
    result["raw_earnings_rank"] = result.house_win_usd.rank(method="min").astype(int)
    result["theo_productivity_rank"] = result.theo_per_available_hour_usd.rank(method="min").astype(int)
    return result


def player_summary(players):
    players = numeric(players)
    totals = players.groupby("player_id", as_index=False)[[
        "tracked_coin_in_usd", "tracked_payout_usd", "tracked_net_usd", "theo_usd", "comp_cost_usd"]].sum()
    total_coin = totals.tracked_coin_in_usd.sum()
    count = max(1, math.ceil(len(totals) * .01))
    summary = {"unique_tracked_players": len(totals),
               "tracked_coin_in_usd": float(total_coin),
               "tracked_payout_usd": float(totals.tracked_payout_usd.sum()),
               "tracked_player_net_usd": float(totals.tracked_net_usd.sum()),
               "ahead_share": float((totals.tracked_net_usd > 0).mean()),
               "top_1pct_wager_share": float(totals.nlargest(count, "tracked_coin_in_usd").tracked_coin_in_usd.sum() / total_coin),
               "note": "Unique players and ahead share are recomputed across the selected complete months; tracked play only. Concentration describes wagers, not a targeting recommendation."}
    return summary


def action_cost(action, quantity, horizon=30):
    if not isinstance(quantity, (int, np.integer)) or quantity < 0 or quantity > int(action["quantity_limit"]):
        raise ValueError("Quantity exceeds catalogue limit or is not a nonnegative integer")
    operating_days = max(0, horizon - int(action["lead_days"]))
    return int(quantity) * (int(action["unit_cost_cents"]) +
                            int(action["recurring_cost_cents_per_day"]) * operating_days) / 100


def validate_plan(plan, catalogue, budget=100000):
    """Validate action types, catalogue quantities, policy conflicts and target overlap."""
    lookup = {a["action_type_id"]: a for a in catalogue}
    ids = [item["action_type_id"] for item in plan if item["quantity"] > 0 and item["action_type_id"] != "A-HOLD"]
    if len(ids) != len(set(ids)):
        raise ValueError("Combine duplicate action types into one row")
    if len(ids) > 3:
        raise ValueError("At most three funded action types")
    if {"A-COMP-PILOT", "A-COMP-CHANGE"}.issubset(ids):
        raise ValueError("Comp pilot and floor-wide comp change are incompatible")
    total, used = 0., set()
    for item in plan:
        action = lookup[item["action_type_id"]]
        total += action_cost(action, item["quantity"])
        if item["quantity"] and action["unit"] in ["machine", "bank", "zone", "manufacturer", "technician_shift"]:
            targets = item.get("targets", [])
            if len(set(targets)) != item["quantity"]:
                raise ValueError("Specify one distinct target per unit")
        # For a bank relocation, callers expand to member machine IDs first.
        if action.get("incompatibility_group") == "same_machine" and item["quantity"]:
            targets = set(item.get("machine_targets", item.get("targets", [])))
            if targets & used:
                raise ValueError("Conflicting moves or replacements target the same machine")
            used |= targets
    if total > budget:
        raise ValueError("Plan exceeds the operations budget")
    return total
