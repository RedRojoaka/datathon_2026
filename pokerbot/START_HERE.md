# DataLarp — SteadyAce

SteadyAce is a small, offline poker bot for the Heads Up Short Deck PLO5 challenge. It estimates hand equity, compares it with the call price, raises for value, and keeps a modest opponent model. It uses Python and the NumPy already supplied in the tournament image.

## Where to edit

In the author's workspace, **edit `heads-up-bundle/agent.py` between the `YOUR CODE HERE` markers**. The three TODOs are complete: `PARTICIPANT = "DataLarp"`, `AGENT_NAME = "SteadyAce"`, and the three strategy functions are implemented. `equity.py` contains the simulation helper.

`heads-up-bundle/` is an ignored local challenge checkout with its own Git history. **`pokerbot/` is the public source copy** in the existing `RedRojoaka/datathon_2026` repository. After local edits, run this from the shared repository root:

```sh
python3 refresh_poker_source.py
```

In a fresh GitHub clone, edit `pokerbot/agent.py` and `pokerbot/equity.py` directly. You do not need the original local checkout.

The small root `agent.py` starts the server in `pokerbot/`. Root `requirements.txt`, `.dockerignore`, `docker/`, and `tools/` support the organizer's build. The image includes only poker runtime files. Dashboard code and data are excluded from the poker image.

## Run from the repository root

```sh
python3 -m venv pokerbot/.venv
source pokerbot/.venv/bin/activate
python -m pip install -r pokerbot/requirements-dev.txt
python -m pytest -q pokerbot/test_agent.py pokerbot/test_strategy.py
python agent.py
```

The server listens on port 5008. In another terminal with the same environment activated:

```sh
python pokerbot/baseline-bots/baseline_always_pot.py
```

In a third terminal:

```sh
python pokerbot/judge_engine.py --deals 1000 --seed 7
```

Control+C stops each server. No API key is required, and no Gemini credit is used.

For local development inside the original bundle, run its `agent.py` and tests from that directory. Refresh `pokerbot/` before testing the root submission entry point.

## Verify the actual submission

```sh
./tools/check_build.sh
python pokerbot/benchmark.py --seeds 101 202 303 --deals 1000
```

The benchmark starts and stops its own servers, uses both seats, restarts both bots between halves, and saves the judge's confidence intervals, timing, and error counts. It includes four official baselines and three extra practice policies. Rerunning it makes no paid requests.

Read [strategy and limitations](STRATEGY.md), [validation evidence](VALIDATION.md), and [submission instructions](SUBMISSION.md). The original participant README is preserved as `PARTICIPANT_BUNDLE.md` in the public copy. The final submission requires your public repository URL and a full, pushed, 40-character commit SHA.
