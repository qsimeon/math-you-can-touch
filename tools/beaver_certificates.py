"""Exact nonhalting certificates for two-state, two-symbol tables.

Two certificate kinds, each checkable without trusting the finder:

* ``halt-unreachable``: an over-approximation of the (state, symbol) slots the
  machine can ever read, starting in A on a blank tape. If no halting rule is in
  that set, the machine never halts.
* ``record-cycle``: two times t1 < t2 at which the head stands on a new farthest
  cell on one side, in the same state, with the tape matching over every cell the
  head visits between t1 and t2. The run from t1 to t2 then repeats forever,
  shifted along the tape, so the machine never halts.

A machine with neither certificate stays unresolved. A long run is not a proof.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from busybeaver.core import compare_simulations, enumerate_tables, table_as_json


def _row(state):
    return 0 if state == "A" else 1


def reachable_slots(table):
    """Slots (state, symbol) that can ever be read; an over-approximation."""
    states, symbols = {"A"}, {0}
    while True:
        slots = {(s, x) for s in states for x in symbols}
        actions = [table[_row(s)][x] for s, x in slots]
        new_states = states | {n for _, _, n in actions if n != "H"}
        new_symbols = symbols | {w for w, _, _ in actions}
        if (new_states, new_symbols) == (states, symbols):
            return slots
        states, symbols = new_states, new_symbols


def halt_unreachable(table):
    return all(table[_row(s)][x][2] != "H" for s, x in reachable_slots(table))


def _run(table, steps):
    """Yield (time, state, head, tape) after each step; stop at halt."""
    state, head, tape = "A", 0, {}
    yield 0, state, head, tape
    for time in range(1, steps + 1):
        write, move, nxt = table[_row(state)][tape.get(head, 0)]
        tape[head] = write
        head += 1 if move == "R" else -1
        if nxt == "H":
            return
        state = nxt
        yield time, state, head, tape


def find_record_cycle(table, max_steps=500):
    """Return {side, t1, t2} for the first record cycle found, else None."""
    records = {"R": [], "L": []}  # (time, state, head, snapshot, index into positions)
    positions = []
    high = low = 0
    for time, state, head, tape in _run(table, max_steps):
        positions.append(head)
        for side in ("R", "L"):
            new = (head > high) if side == "R" else (head < low)
            if time and not new:
                continue
            for t1, s1, p1, snap1 in reversed(records[side]):
                if s1 != state:
                    continue
                span = positions[t1:time + 1]
                if side == "R":
                    edge, shift = min(span), head - p1
                    cells = range(edge, p1 + 1)
                else:
                    edge, shift = max(span), head - p1
                    cells = range(p1, edge + 1)
                if all(snap1.get(c, 0) == tape.get(c + shift, 0) for c in cells):
                    return {"kind": "record-cycle", "side": side, "t1": t1, "t2": time}
            records[side].append((time, state, head, dict(tape)))
        high, low = max(high, head), min(low, head)
    return None


def check_record_cycle(table, certificate):
    """Re-simulate and confirm every condition of the record-cycle argument."""
    side, t1, t2 = certificate["side"], certificate["t1"], certificate["t2"]
    if not (type(t1) is int and type(t2) is int and 0 <= t1 < t2):
        return False
    frames = {}
    history = []
    for time, state, head, tape in _run(table, t2):
        history.append(head)
        if time in (t1, t2):
            frames[time] = (state, head, dict(tape))
    if t2 not in frames:
        return False  # halted before t2
    (s1, p1, tape1), (s2, p2, tape2) = frames[t1], frames[t2]
    sign = 1 if side == "R" else -1
    # Each head must be strictly beyond every earlier position on its side.
    if any(sign * h >= sign * p1 for h in history[:t1]) and t1:
        return False
    if any(sign * h >= sign * p2 for h in history[:t2]):
        return False
    if s1 != s2 or sign * (p2 - p1) <= 0:
        return False
    span = history[t1:t2 + 1]
    shift = p2 - p1
    cells = range(min(span), p1 + 1) if side == "R" else range(p1, max(span) + 1)
    return all(tape1.get(c, 0) == tape2.get(c + shift, 0) for c in cells)


def certify(table, max_steps=500):
    if halt_unreachable(table):
        return {"kind": "halt-unreachable"}
    return find_record_cycle(table, max_steps)


def check(table, certificate):
    if certificate["kind"] == "halt-unreachable":
        return halt_unreachable(table)
    if certificate["kind"] == "record-cycle":
        return check_record_cycle(table, certificate)
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-steps", type=int, default=500)
    parser.add_argument("--out", required=True, help="new output directory")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    outcomes = Counter()
    unresolved = []
    with (out / "certificates.jsonl").open("w", encoding="utf-8") as stream:
        for index, table in enumerate(enumerate_tables()):
            status = compare_simulations(table, step_limit=100)["status"]
            if status == "HALTED":
                if certify(table, args.max_steps) is not None:
                    raise AssertionError(f"halting table {index} received a certificate")
                outcomes["halted within 100 steps"] += 1
                continue
            if status != "UNKNOWN_AT_LIMIT":
                outcomes["repeating configuration (earlier checker)"] += 1
                continue
            cert = certify(table, args.max_steps)
            if cert is None:
                unresolved.append(index)
                outcomes["unresolved"] += 1
            elif not check(table, cert):
                raise AssertionError(f"certificate for table {index} failed its check")
            else:
                outcomes[cert["kind"]] += 1
            stream.write(json.dumps({"index": index, "table": table_as_json(table),
                                     "certificate": cert}) + "\n")
    summary = {"tables": sum(outcomes.values()), "outcomes": dict(outcomes),
               "unresolved_indices": unresolved, "max_steps": args.max_steps}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
