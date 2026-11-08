"""
agent.py - YOUR poker bot. This one file is a complete web server.

Run it:
    python agent.py                  # listens on port 5008
    PORT=5010 python agent.py        # or pick a port

Play a match against a baseline (three windows):
    python agent.py                                 # your bot on port 5008
    python baseline-bots/baseline_random.py         # opponent on port 5009
    python judge_engine.py                          # judge: both halves (uses those two ports)

Check that the tournament can run it:
    python -m pytest -q              # tests in test_agent.py
    ./tools/check_build.sh           # builds and smoke-tests it like the tournament

Team: DataLarp. Bot: SteadyAce.
The strategy is implemented between the marked lines below. equity.py is
the fast, local simulation helper; no external API or trained model is used.

Everything under "SERVER PLUMBING" talks to the judge. You normally never
need to change it, and if you break it the judge can't talk to your bot.
"""

import os
import traceback

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from evaluator import card_rank, card_suit, cards_to_str, omaha_score, warmup  # handy helpers, see evaluator.py
from game import Action, AgentConfig, HandResult, Observation, Street

# Build omaha_score's lookup table now, while the server starts, instead of
# during your first decision (where it would eat into your time bank).
# Do any other slow setup (loading a model, ...) here too: the server must
# answer within 15 seconds of starting.
warmup()

# rename as your team/bot's name
PARTICIPANT = "DataLarp"
AGENT_NAME = "SteadyAce"


# ===== YOUR CODE HERE =====

import numpy as np

from equity import sample_worlds


def new_half(config: AgentConfig, memory: dict) -> None:
    memory.update(hands_played=0, aggressive_hands=0, betting_hands=0,
                  folds_to_bet=0, current=None, cache={})


def _weights(obs, memory, strength):
    raises = [a for a in obs.action_history
              if not a.is_me and a.action in (Action.RAISE_HALF, Action.RAISE_POT)]
    current_raises = sum(a.street == obs.street for a in raises)
    if not raises:
        return np.ones(len(strength))
    # A hand-level rate avoids double-counting the same history on each request.
    aggression = (memory["aggressive_hands"] + 3) / (memory["hands_played"] + 6)
    selectivity = min(0.85, max(0.10, 1.10 - aggression))
    if not current_raises:
        selectivity *= 0.35  # earlier aggression is weaker evidence on a new board
    cutoff = min(0.80, 0.55 + 0.10 * max(0, current_raises - 1))
    return (1 - selectivity) + selectivity * (strength >= cutoff) / (1 - cutoff)


def call_price(obs):
    """Break-even equity. Previously committed chips are sunk costs."""
    call = min(obs.to_call, obs.my_stack)
    return call / (obs.pot + call) if call else 0.0


def choose_action(obs: Observation, memory: dict) -> Action:
    state = memory.get("current")
    if state is None or state["hand"] != obs.hand_index:
        state = {"hand": obs.hand_index, "opp_raised": False, "we_raised": False}
        memory["current"] = state
        memory["cache"] = {}
    state["opp_raised"] |= any(
        not a.is_me and a.action in (Action.RAISE_HALF, Action.RAISE_POT)
        for a in obs.action_history)
    # Protect the engine's legal-action contract, including the raise cap.
    if len(obs.legal_actions) == 1:
        return obs.legal_actions[0]

    key = (obs.hole_cards, obs.board)
    if key not in memory["cache"]:
        memory["cache"][key] = sample_worlds(obs.hole_cards, obs.board, obs.hand_index)
    outcomes, strength = memory["cache"][key]
    weights = _weights(obs, memory, strength)
    equity = float(np.average(outcomes, weights=weights))
    all_in = obs.opp_stack == 0 or obs.to_call >= obs.my_stack
    # Future bets reduce equity realization, especially out of position.
    realization = 1.0 if all_in or obs.street == Street.RIVER else (0.96 if obs.is_button else 0.92)
    required = call_price(obs)
    if obs.to_call and equity * realization < required + (0.005 if all_in else 0.015):
        return Action.FOLD if Action.FOLD in obs.legal_actions else Action.CHECK_CALL
    if all_in:
        return Action.CHECK_CALL  # there is nobody left to raise

    # Value comes first. No unconditional all-in or automatic category rule:
    # a full house can lose to a flush, and a straight can lose to trips.
    value_threshold = (0.59, 0.61, 0.63, 0.64)[int(obs.street)]
    if obs.raises_this_street >= 2:
        value_threshold += 0.04
    if equity > value_threshold:
        preferred = Action.RAISE_POT if equity > 0.74 else Action.RAISE_HALF
        alternatives = (preferred, Action.RAISE_HALF, Action.RAISE_POT)
        for action in alternatives:
            if action in obs.legal_actions:
                # raise_to is a STREET TOTAL, not additional chips.
                extra = obs.raise_to[action] - obs.my_bet
                response = min(obs.opp_stack, max(0, extra - obs.to_call))
                called_ev = equity * (obs.pot + extra + response) - extra
                call_ev = equity * (obs.pot + obs.to_call) - obs.to_call
                if called_ev > call_ev + 0.25:
                    state["we_raised"] = True
                    return action

    # A small, deterministic mixed bluff only after evidence of actual folds.
    # Half-pot break-even fold rate is B/(P+B), about 1/3; use a safety margin.
    if (obs.to_call == 0 and obs.street == Street.RIVER
            and Action.RAISE_HALF in obs.legal_actions
            and memory["betting_hands"] >= 20 and equity < 0.25):
        folds = memory["folds_to_bet"] / memory["betting_hands"]
        bet = obs.raise_to[Action.RAISE_HALF] - obs.my_bet
        if folds > bet / (obs.pot + bet) + 0.15:
            mix = (sum((i + 1) * c for i, c in enumerate(obs.hole_cards)) + obs.hand_index * 17) % 100
            if mix < 12:
                state["we_raised"] = True
                return Action.RAISE_HALF
    return Action.CHECK_CALL


def on_hand_end(result: HandResult, memory: dict) -> None:
    memory["hands_played"] += 1
    state = memory.get("current")
    if state is not None and state["hand"] == result.hand_index:
        memory["aggressive_hands"] += int(state["opp_raised"])
        if state["we_raised"]:
            memory["betting_hands"] += 1
            memory["folds_to_bet"] += int(not result.went_to_showdown and result.winner == "me")
        memory["current"] = None
        memory["cache"] = {}

# ===== END OF YOUR CODE =====


# ===== SERVER PLUMBING (you normally don't need to edit below) =====
# The judge calls these routes:
#   GET  /           -> who you are (also used as the health check)
#   POST /new-half   -> start a fresh half: memory is wiped
#   POST /act        -> the judge sends any finished hands plus an Observation;
#                       on_hand_end() runs for each hand, then you answer an action
#   POST /hand-end   -> the judge sends the last finished hands of a half
#
# Why "async def"? The routes run on one thread and call your functions
# directly, so your functions never run twice at once. Your own functions
# stay normal "def" (don't make them async).
#
# Keep your per-half state in `memory`. In the tournament every half runs in
# a fresh server process, so everything starts over. When you test locally,
# though, one process can play both halves and only `memory` is wiped, NOT
# other global variables. Using `memory` makes your bot behave the same way
# in both places.

app = FastAPI()
MEMORY: dict = {}                                   # your memory for this half
STATUS = {"started": False}                         # has /new-half been called?
TOKEN = os.environ.get("AGENT_TOKEN") or None       # set by the tournament


async def _read_request(request: Request, path: str) -> tuple[dict, JSONResponse | None]:
    """Check the token (and that the half has started) BEFORE reading the body.

    Checking first means a request without the right token costs your bot
    almost nothing, so nobody else can slow it down by sending junk.
    Returns (body, None) when the request is fine, or ({}, error response).
    """
    if TOKEN and request.headers.get("x-agent-token") != TOKEN:
        return {}, JSONResponse({"error": "bad or missing X-Agent-Token"}, status_code=401)
    if not STATUS["started"] and path != "/new-half":
        return {}, JSONResponse({"error": "call /new-half first"}, status_code=409)
    try:
        body = await request.json()
    except ValueError:
        body = None
    if not isinstance(body, dict):
        return {}, JSONResponse({"error": "the request body must be a JSON object"}, status_code=400)
    return body, None


def _error_info(exc: Exception) -> dict:
    """Describe an exception from your code (call this inside `except`)."""
    return {"error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()}


def _crash(exc: Exception, hand_end_errors: list | None = None) -> JSONResponse:
    """Report an exception from your code to the judge (with traceback)."""
    return JSONResponse({**_error_info(exc), "hand_end_errors": hand_end_errors or []},
                        status_code=500)


def _deliver_results(raw_results) -> list:
    """Call on_hand_end() for each finished hand the judge sent.
    Returns a list of error reports (one per hand that crashed)."""
    errors = []
    for raw in raw_results or []:
        try:
            on_hand_end(HandResult.from_dict(raw), MEMORY)
        except Exception as exc:
            errors.append(_error_info(exc))
    return errors


@app.get("/")
async def info():
    """Health check: tells the judge who this bot is."""
    return {"participant": PARTICIPANT, "agent_name": AGENT_NAME}


@app.post("/new-half")
async def route_new_half(request: Request):
    """Wipe memory and call your new_half(). The body is {"config": {...}}."""
    body, refused = await _read_request(request, "/new-half")
    if refused:
        return refused
    MEMORY.clear()
    STATUS["started"] = True
    try:
        new_half(AgentConfig.from_dict(body.get("config", {})), MEMORY)
    except Exception as exc:
        return _crash(exc)
    return {"ok": True}


@app.post("/act")
async def route_act(request: Request):
    """Deliver finished hands, then turn the JSON into an Observation, call
    choose_action(), and send the answer back."""
    body, refused = await _read_request(request, "/act")
    if refused:
        return refused
    hand_end_errors = _deliver_results(body.get("hand_results"))
    try:
        obs = Observation.from_dict(body["observation"])
        action = choose_action(obs, MEMORY)
    except Exception as exc:
        return _crash(exc, hand_end_errors)
    # Send the action's name; anything strange is passed on for the judge to reject.
    if isinstance(action, Action):
        answer = action.name
    elif action is None or isinstance(action, (str, int, float, bool)):
        answer = action
    else:
        answer = repr(action)
    return {"action": answer, "hand_end_errors": hand_end_errors}


@app.post("/hand-end")
async def route_hand_end(request: Request):
    """Call on_hand_end() for the last finished hands of a half."""
    body, refused = await _read_request(request, "/hand-end")
    if refused:
        return refused
    return {"ok": True, "hand_end_errors": _deliver_results(body.get("results"))}


if __name__ == "__main__":
    # The tournament sets PORT as an environment variable, so each bot is compliant to our evaluation platform
    # Locally it defaults to 5008 for your own testing convenience
    port = int(os.environ.get("PORT", "5008"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info", access_log=False)
