"""Extra local opponents. Never loaded by the submitted bot."""

import os
import uvicorn

import agent as server
from equity import sample_worlds
from evaluator import omaha_score
from game import Action, Street

MODE = os.environ.get("PRACTICE_MODE", "surprise")


def choose(obs, memory):
    raises = [a for a in (Action.RAISE_POT, Action.RAISE_HALF) if a in obs.legal_actions]
    if MODE == "surprise":
        # Mostly calls, but sometimes abruptly starts pot-raising to the cap.
        jam = (sum(obs.hole_cards) + 19 * obs.hand_index) % 7 == 0
        return raises[0] if raises and (jam or obs.street == Street.RIVER) else Action.CHECK_CALL
    if MODE == "selective":
        if obs.street == Street.PREFLOP:
            premium = sum(c >> 2 for c in obs.hole_cards) >= 24
            strength = 0.65 if premium else 0.4
        else:
            # Exact partial-board scoring via our already-validated helper.
            from equity import batch_score
            category = int(batch_score([obs.hole_cards], [obs.board])[0]) >> 20
            strength = 0.8 if category >= 4 else 0.5 if category >= 2 else 0.2
    elif MODE == "equity":
        key = (obs.hand_index, obs.hole_cards, obs.board)
        if memory.get("practice_key") != key:
            memory["practice_key"] = key
            memory["practice_equity"] = float(sample_worlds(obs.hole_cards, obs.board, obs.hand_index)[0].mean())
        strength = memory["practice_equity"]
    else:
        raise ValueError(f"unknown practice mode: {MODE}")
    if raises and strength > 0.62:
        return raises[0]
    if obs.to_call and strength < max(0.32, obs.to_call / (obs.pot + obs.to_call) + 0.06):
        return Action.FOLD
    return Action.CHECK_CALL


server.choose_action = choose
server.PARTICIPANT = "Local practice"
server.AGENT_NAME = MODE
if __name__ == "__main__":
    uvicorn.run(server.app, host="127.0.0.1", port=int(os.environ.get("PORT", "5009")),
                log_level="warning", access_log=False)
