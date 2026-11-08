"""Differential scoring, all-in decisions, and half-isolation regression tests."""

from dataclasses import replace
from itertools import combinations
from pathlib import Path
import importlib.util
import random
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent as strategy
from equity import batch_score, sample_worlds
from evaluator import cards_from_str, category_of, omaha_score, score_five
from game import Action, AgentConfig, Game, ObservedAction, Street, make_deal


@pytest.mark.parametrize("nboard", [3, 4, 5])
def test_fast_scoring_matches_organizer(nboard):
    rng = random.Random(f"score-{nboard}")
    draws = np.array([rng.sample(range(36), 5 + nboard) for _ in range(500)])
    fast = batch_score(draws[:, :5], draws[:, 5:])
    for row, score in zip(draws, fast):
        if nboard == 5:
            reference = omaha_score(row[:5], row[5:])
        else:
            reference = max(score_five(h + b) for h in combinations(row[:5], 2)
                            for b in combinations(row[5:], 3))
        assert score == reference


@pytest.mark.parametrize("hole,board,category", [
    ("Th 7s 7d 8c 9c", "Ah Kh Qh Jh 6c", 3),  # one heart is not a flush
    ("Ah Kh 8d 8c 6s", "6h 9h Jh 7c 7s", 6),
    ("As 6s Kd Qc Th", "7s 8s 9s Ad Ac", 8),  # short-deck wheel
    ("As Ac Kc Qc Jc", "Ad 6c 7d 9s Th", 4),  # trips outrank straights
])
def test_omaha_and_short_deck_edge_cases(hole, board, category):
    holes = np.array([cards_from_str(hole)])
    boards = np.array([cards_from_str(board)])
    score = int(batch_score(holes, boards)[0])
    assert score == omaha_score(holes[0], boards[0])
    assert category_of(score) == category


def memory():
    value = {}
    strategy.new_half(AgentConfig(), value)
    return value


def all_in_observation():
    # Real engine sequence, including two equal, stack-capped raise sizes.
    game = Game(make_deal("all-in", 0), 0)
    while not game.is_terminal:
        obs = game.observation(game.to_act)
        if obs.opp_stack == 0 and obs.to_call:
            return obs
        game.apply(Action.RAISE_POT if Action.RAISE_POT in obs.legal_actions else Action.CHECK_CALL)
    raise AssertionError("sequence should expose an all-in response")


def fake_worlds(monkeypatch, equity):
    monkeypatch.setattr(strategy, "sample_worlds",
                        lambda *args: (np.full(256, equity), np.linspace(0, 1, 256)))


def test_all_in_calls_positive_ev_without_trying_to_raise(monkeypatch):
    obs = all_in_observation()
    fake_worlds(monkeypatch, strategy.call_price(obs) + 0.08)
    assert strategy.choose_action(obs, memory()) == Action.CHECK_CALL


def test_all_in_folds_negative_ev_even_after_investing(monkeypatch):
    obs = all_in_observation()
    fake_worlds(monkeypatch, max(0, strategy.call_price(obs) - 0.10))
    assert strategy.choose_action(obs, memory()) == Action.FOLD


def test_same_equity_calls_small_price_and_folds_large_price(monkeypatch):
    obs = all_in_observation()
    fake_worlds(monkeypatch, 0.25)
    cheap = replace(obs, to_call=2, pot=100)
    costly = replace(obs, to_call=50, my_stack=50, pot=100)
    assert strategy.choose_action(cheap, memory()) == Action.CHECK_CALL
    assert strategy.choose_action(costly, memory()) == Action.FOLD


def test_raises_cap_and_identical_all_in_raise_targets(monkeypatch):
    fake_worlds(monkeypatch, 0.99)
    game = Game(make_deal("cap", 0), 0)
    seen_equal = False
    while not game.is_terminal:
        obs = game.observation(game.to_act)
        if len(set(obs.raise_to.values())) == 1 and len(obs.raise_to) == 2:
            seen_equal = True
        assert strategy.choose_action(obs, memory()) in obs.legal_actions
        game.apply(Action.RAISE_POT if Action.RAISE_POT in obs.legal_actions else Action.CHECK_CALL)
    assert seen_equal
    obs = replace(obs, legal_actions=(Action.FOLD, Action.CHECK_CALL), raise_to={},
                  raises_this_street=4, opp_stack=10)
    assert strategy.choose_action(obs, memory()) == Action.CHECK_CALL


def test_no_free_folds(monkeypatch):
    fake_worlds(monkeypatch, 0.0)
    game = Game(make_deal("free", 0), 0)
    game.apply(Action.CHECK_CALL)
    obs = game.observation(game.to_act)
    assert obs.to_call == 0
    assert strategy.choose_action(obs, memory()) != Action.FOLD


def test_undercall_uses_actual_chips_available():
    obs = replace(all_in_observation(), to_call=80, my_stack=20, pot=100)
    assert strategy.call_price(obs) == pytest.approx(20 / 120)


def test_monte_carlo_gives_half_credit_for_ties():
    # Some opponent hands hold Ac plus another king and tie our ace trips.
    # Direct outcomes must include 0.5 rather than rounding ties to a win/loss.
    outcomes, _ = sample_worlds(tuple(cards_from_str("As Kc Qd 8h 7s")),
                               tuple(cards_from_str("6c 6d 6h Ad Ah")), samples=4096)
    assert 0.5 in outcomes
    assert set(outcomes) <= {0.0, 0.5, 1.0}


def test_visible_cards_only_and_reproducible_sampling():
    deal = make_deal("worlds", 0)
    a = sample_worlds(deal.hole_cards[0], deal.flop, 10)
    b = sample_worlds(deal.hole_cards[0], deal.flop, 10)
    assert all(np.array_equal(x, y) for x, y in zip(a, b))


def test_repeated_history_counts_an_aggressive_hand_once(monkeypatch):
    fake_worlds(monkeypatch, 0.5)
    game = Game(make_deal("count", 0), 0)
    game.apply(Action.RAISE_POT)
    obs = game.observation(1)
    mem = memory()
    strategy.choose_action(obs, mem)
    strategy.choose_action(obs, mem)
    while not game.is_terminal:
        game.apply(Action.CHECK_CALL)
    strategy.on_hand_end(game.hand_result(1), mem)
    assert mem["aggressive_hands"] == 1
    assert mem["hands_played"] == 1


def test_unknown_sudden_raiser_keeps_a_broad_component():
    obs = all_in_observation()
    weights = strategy._weights(obs, memory(), np.array([0.0, 0.3, 0.8, 1.0]))
    assert np.all(weights > 0), "do not assume that every sudden jam is the nuts"
    assert weights[-1] > weights[0]


def test_all_mutable_state_resets_between_halves():
    obs = all_in_observation()
    mem = memory()
    action = strategy.choose_action(obs, mem)
    mem.clear()  # server does this before new_half
    strategy.new_half(AgentConfig(), mem)
    assert mem["hands_played"] == mem["aggressive_hands"] == 0
    assert mem["cache"] == {} and mem["current"] is None
    assert strategy.choose_action(obs, mem) == action


def test_repository_root_entrypoint():
    # Exercise the actual public submission entry, rather than only its module.
    path = Path(__file__).resolve().parents[1] / "agent.py"
    spec = importlib.util.spec_from_file_location("root_poker_entrypoint", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from fastapi.testclient import TestClient
    assert TestClient(module.app).get("/").json()["participant"] == "DataLarp"
