"""Small, exact short-deck Omaha evaluator with batched Monte Carlo equity.

NumPy is already in the organizer's CPU image. No training, native extension,
network, or saved model is required. All scoring follows evaluator.score_five.
"""

from itertools import combinations, combinations_with_replacement

import numpy as np

from evaluator import score_five

PAIRS = np.array(list(combinations(range(5), 2)))
TRIPLES = {n: np.array(list(combinations(range(n), 3))) for n in (3, 4, 5)}
RANK_KEYS = np.array([5 ** (c >> 2) for c in range(36)], dtype=np.int32)
SUIT_BITS = np.array([1 << (c & 3) for c in range(36)], dtype=np.int32)


def _build_rank_table():
    # Base-5 digits encode rank multiplicities (0..4), without sorting at runtime.
    table = np.zeros(5**9, dtype=np.int32)
    for ranks in combinations_with_replacement(range(9), 5):
        counts = [ranks.count(r) for r in range(9)]
        if max(counts) > 4:
            continue
        used = [0] * 9
        cards = []
        for i, rank in enumerate(ranks):
            cards.append(4 * rank + ((used[rank] + rank) % 4))
            used[rank] += 1
        # Distinct ranks could accidentally all have the same suit.
        if len(set(ranks)) == 5 and len({c & 3 for c in cards}) == 1:
            cards[-1] ^= 1
        table[sum(5**r for r in ranks)] = score_five(cards)
    table.flags.writeable = False
    return table


RANK_TABLE = _build_rank_table()


def batch_score(hole, board):
    """Score rows using exactly two hole cards and three visible board cards."""
    hole = np.asarray(hole, dtype=np.int32)
    board = np.asarray(board, dtype=np.int32)
    hp, bt = hole[:, PAIRS], board[:, TRIPLES[board.shape[1]]]
    hk = RANK_KEYS[hp].sum(axis=2)
    bk = RANK_KEYS[bt].sum(axis=2)
    scores = RANK_TABLE[hk[:, :, None] + bk[:, None, :]]
    hs = SUIT_BITS[hp[:, :, 0]] & SUIT_BITS[hp[:, :, 1]]
    bs = SUIT_BITS[bt[:, :, 0]] & SUIT_BITS[bt[:, :, 1]] & SUIT_BITS[bt[:, :, 2]]
    flush = (hs[:, :, None] & bs[:, None, :]) != 0
    # A straight becomes a straight flush (3 -> 8); other flushes go 0 -> 6.
    scores += flush * np.where((scores >> 20) == 3, 5 << 20, 6 << 20)
    return scores.max(axis=(1, 2))


def preflop_strength(holes):
    """Only used to order plausible opponent ranges, never as showdown equity."""
    ranks, suits = holes >> 2, holes & 3
    counts = (ranks[:, :, None] == np.arange(9)).sum(axis=1)
    suited = (suits[:, :, None] == np.arange(4)).sum(axis=1)
    pairs = ((counts == 2) * (np.arange(9) + 3)).sum(axis=1)
    # Multiple suited high cards and useful pairs help; trips waste hole cards.
    connected = ((counts[:, :-1] > 0) & (counts[:, 1:] > 0)).sum(axis=1)
    return (0.18 * ranks.sum(axis=1) + 0.6 * pairs + 0.7 * connected
            + 0.65 * (suited >= 2).sum(axis=1) - 2 * (counts >= 3).sum(axis=1))


def percentile(values):
    """Midrank percentiles: equal made hands receive exactly equal weights."""
    ordered = np.sort(values)
    return (np.searchsorted(ordered, values, side="left")
            + np.searchsorted(ordered, values, side="right")) / (2 * len(values))


def sample_worlds(hole, board, hand_index=0, samples=None):
    """Return (win + half tie, opponent strength percentile) for legal worlds.

    Uniformly sample *without replacement within each world*. Only the bot's
    visible cards seed these simulations; no match seed or hidden deal is used.
    """
    nboard = len(board)
    samples = samples or {0: 256, 3: 192, 4: 256, 5: 512}[nboard]
    visible = set(hole) | set(board)
    deck = np.array([c for c in range(36) if c not in visible], dtype=np.int32)
    seed = sum(1 << c for c in hole) ^ (sum(1 << c for c in board) << 1)
    seed ^= (hand_index + 1) << 40
    rng = np.random.default_rng(seed)
    # Sorting iid continuous keys gives a uniform permutation in each row.
    draws = deck[rng.random((samples, len(deck))).argsort(axis=1)[:, :10 - nboard]]
    opponent = draws[:, :5]
    full_board = np.empty((samples, 5), dtype=np.int32)
    full_board[:, :nboard] = board
    full_board[:, nboard:] = draws[:, 5:]
    hero = np.broadcast_to(np.array(hole, dtype=np.int32), (samples, 5))
    mine = batch_score(hero, full_board)
    theirs = batch_score(opponent, full_board)
    outcomes = (mine > theirs).astype(float) + 0.5 * (mine == theirs)
    if nboard == 0:
        strength = preflop_strength(opponent)
    elif nboard == 5:
        strength = theirs
    else:
        strength = batch_score(opponent, full_board[:, :nboard])
    return outcomes, percentile(strength)
