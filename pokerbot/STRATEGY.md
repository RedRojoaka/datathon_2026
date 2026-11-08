# How SteadyAce decides

The game is heads-up, 36-card, five-hole-card pot-limit Omaha. Every evaluation uses **exactly two hole cards and three board cards**. Flushes beat full houses; trips beat straights; A-6-7-8-9 is the lowest straight. Both players start each hand with 80 chips in the supplied rules.

## Equity and price

The bot samples possible opponent hands and missing board cards from the remaining deck. Cards are sampled without replacement within each simulated deal. It counts a win as 1, a tie as 0.5, and a loss as 0. The number of worlds is bounded: 256 preflop, 192 flop, 256 turn, and 512 river. Repeated decisions with the same visible cards reuse the simulations while updating the opponent-range weights.

The helper's NumPy evaluator is exact for each simulated hand. It is checked against the organizer's `omaha_score` and independent enumeration on partial boards. The equity estimate is approximate: 256 binary samples have a worst-case standard error around 3.1 percentage points before range weighting. It is not a certainty about the actual hidden hand.

For a call of C chips into the currently visible pot P, break-even equity is:

```text
required equity = C / (P + C)
call EV         = equity * (P + C) - C
```

P already includes the opponent's current bet. The bot does not count previously committed chips as a reason to keep calling. When further betting remains, it applies a small equity-realization discount, with a larger discount out of position.

## Sudden all-ins

When the opponent is all-in, the bot calls only when estimated, range-adjusted equity clears the call price plus a small margin. It never attempts to raise an all-in opponent. There is no additional future-betting discount because a call goes directly to showdown.

A large bet can indicate a strong hand, a bluff, or a mistake. A new opponent is modeled as a mixture of broad random hands and stronger hands. Frequently aggressive opponents move that mixture toward a broad range. Rare raisers receive more credit, while retaining a broad component to allow bluffs and mistakes. Counters count each aggressive **hand** once rather than repeatedly counting the same action history.

The checks cover good-priced calls, bad-priced folds, calls after already investing chips, short-stack prices, the four-raise cap, and half-pot/pot actions that become the same all-in amount. The policy always selects an engine-supplied legal action.

## Value and occasional bluffs

Strong estimated equity can trigger a half-pot or pot-sized value raise. The bot uses `obs.raise_to` as the total street bet, subtracts `my_bet` to find new chips at risk, and compares the estimated called-raise EV with calling. It requires stronger equity after repeated raises.

After at least 20 betting hands, a low-equity river hand can occasionally make a half-pot bluff against an opponent that has actually folded enough. The zero-equity bluff's break-even fold frequency is B/(P+B). The policy requires an extra margin above that rate and uses a small deterministic mixture. This estimate is based on hand-level folds after our bets; it is not a precise estimate for every river situation.

These are **game-theory-informed heuristics**, not a solved Nash-equilibrium/GTO strategy. The raise EV treats current range equity as an approximation for equity when called; real callers select stronger ranges. Range weights, value thresholds, and realization discounts are hand-written. No solver, search tree, neural network, or training run is claimed.

## Reliability and limits

All match-specific state is in `memory`, reset at each half. Immutable scoring tables are built at startup. There are no match-time file writes or network/API calls. The bot never reads the judge's secret match seed or attempts to reconstruct the opponent's cards from it. Showdown cards are not retained across halves.

Tests and baseline wins establish compatibility and an edge over those tested policies. They do not guarantee a tournament win. Better opponents can exploit the coarse range model, approximate equity, and value thresholds. The chosen design keeps the strategy compact and understandable under the eight-second time budget.
