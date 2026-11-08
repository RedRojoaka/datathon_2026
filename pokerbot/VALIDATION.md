# SteadyAce validation

Validated November 8, 2026. Team **DataLarp**; bot **SteadyAce**.

## Compatibility and code placement

- **31 tests passed** in both the original editable bundle and the public source copy.
- The three strategy functions are directly inside `agent.py`'s marked `YOUR CODE HERE` section. Both identity TODOs are complete.
- The server-plumbing section is byte-identical to the starter. The organizer's `game.py`, `evaluator.py`, `judge_engine.py`, original tests, Dockerfiles, build checker, and smoke test are unchanged.
- Fast Omaha scoring matched the organizer's evaluator on 1,500 randomly generated complete and partial boards, plus explicit short-deck wheel, flush, trips, and Omaha-card-count cases.
- Regression cases cover positive/negative-EV all-in responses, sunk costs, short-stack prices, equal capped raise targets, raise caps, free checks, ties, repeated action histories, and fresh-half memory.
- The root submission entry point reports DataLarp and starts the same server.

## Full-length duplicate matches

The final code played **21 matches / 42,000 hands**: seven opponents, seeds **101, 202, 303**, 1,000 deals per half, two halves per match. Both bots were restarted in fresh processes for every half. There were **21 wins, zero chops, zero losses**. Every win had an official 95% confidence interval entirely above zero.

| Opponent | Wins / matches | Official bb/deal range over three seeds |
| --- | ---: | ---: |
| random | 3 / 3 | +7.444 to +8.886 |
| always_half | 3 / 3 | +13.319 to +14.931 |
| always_pot | 3 / 3 | +7.572 to +9.739 |
| calling_station | 3 / 3 | +7.074 to +7.851 |
| surprise | 3 / 3 | +16.331 to +17.679 |
| selective | 3 / 3 | +4.913 to +5.319 |
| equity | 3 / 3 | +1.818 to +2.443 |

There were **zero bot errors, forfeits, or time-bank exhaustions** over all 42 final halves. Maximum charged thinking time was **0.203388 seconds per half**, versus the 8-second limit. Maximum total request wall time was **3.281329 seconds per half**. The judge subtracts its 1 ms grace from each request when computing charged time, so these are different measures.

The four official baselines are unchanged. Extra local policies are defined in `practice_bot.py`: `surprise` usually calls but abruptly pot-raises selected hands and rivers; `selective` raises stronger heuristic hands; `equity` uses the same tested simulation helper with a simpler equity-only policy. The latter is a useful comparison, not an independent implementation of poker evaluation.

## Runtime environment

The final matches ran inside the built **Linux ARM64** Docker image, on **one CPU with 4 GB RAM**, no external network, a read-only filesystem, dropped capabilities, and writable temporary storage. A read-only project mount supplied the judge and practice harness excluded from the small runtime image. The runtime source hashes are recorded in [the summary](results/validation/summary.json) and were checked against the final files.

The native organizer build and restricted smoke test passed. Its startup health check answered in about **0.5 seconds**, below the 15-second limit. Added bot files occupy well below 1 MB on top of the base image, far below the 3 GB allowance. The base includes PyTorch; our bot does not load it.

The **Linux AMD64 build and restricted smoke test also passed**, with the startup health check answering in about **0.8 seconds**. Its log is recorded in `results/docker-build-amd64.txt`. This architecture check uses local emulation, so its timing does not represent a native tournament server.

## Evidence and reproduction

- [Machine-readable match summary and source hashes](results/validation/summary.json).
- Every full result, individual half result, and human-readable judge report is saved in `results/validation/`.
- [Native Docker build and smoke-test log](results/docker-build-native.txt).
- [AMD64 Docker build and smoke-test log](results/docker-build-amd64.txt).

```sh
python -m pytest -q pokerbot/test_agent.py pokerbot/test_strategy.py
./tools/check_build.sh
python pokerbot/benchmark.py --seeds 101 202 303 --deals 1000
```

Run those commands from the shared repository root with the poker environment activated. The match runner uses local HTTP and makes no paid API calls.

These results support compatibility and an advantage against the listed practice policies. They do not establish a solved strategy or guarantee a tournament win. The tournament uses different opponents, a secret seed, and different hardware.
