"""Ask a SAT solver for a drawing of n lines with at least k triangles.

The search covers every simple drawing of n pseudolines: curves that each run
from left to right, where every two cross exactly once and no three meet at a
point. Straight lines are a special case, so a drawing found here may still
need to be straightened, but if no drawing exists here then no straight one
does either.

A drawing is stored as a signotope. Number the lines by the order of their left
ends, top to bottom (for straight lines: by increasing slope). For each triple
a < b < c there is one fact, chi(a, b, c): the crossing of a and c lies above b.
Every assignment where each four lines a < b < c < d give the sequence
chi(abc), chi(abd), chi(acd), chi(bcd) at most one change of value is a
drawing, and every drawing arises this way (Felsner and Weil, 2001).

Three lines bound a triangular region with no line inside it exactly when every
other line has all three of its corners on the same side. That is the rule the
solver uses. The checker below counts triangles a different way, from the order
in which each line meets the others, so the two must agree.
"""
from __future__ import annotations

import argparse
import json
import time
from fractions import Fraction
from functools import cmp_to_key
from itertools import combinations
from pathlib import Path

# ---------------------------------------------------------------- the encoding


def above(chi, vertex, line):
    """Literal for: the crossing of the two lines in `vertex` lies above `line`."""
    x, y = vertex
    if x < line < y:
        return chi[(x, line, y)]
    if line > y:
        return -chi[(x, y, line)]
    return -chi[(line, x, y)]


def signotope_clauses(n, chi):
    """No four lines may change sign twice: forbid true-false-true and
    false-true-false on any three of their four triples, in order."""
    clauses = []
    for a, b, c, d in combinations(range(n), 4):
        s = [chi[(a, b, c)], chi[(a, b, d)], chi[(a, c, d)], chi[(b, c, d)]]
        for p, q, r in combinations(range(4), 3):
            clauses.append([-s[p], s[q], -s[r]])
            clauses.append([s[p], -s[q], s[r]])
    return clauses


def build(n, at_least, per_line_cap=True, encoding="seqcounter", structure=False, fold=1):
    """Return (clauses, chi variables, triangle variables, variable count).

    With structure=True two facts that hold for every solution are added, to
    help the solver; see `structure_clauses`. With fold=k the search is
    limited to drawings that look the same after a turn by 1/k of a circle;
    see `fold_clauses`.
    """
    from pysat.card import EncType
    from pysat.formula import IDPool

    pool = IDPool()
    triples = list(combinations(range(n), 3))
    chi = {t: pool.id(("chi",) + t) for t in triples}
    tri = {t: pool.id(("tri",) + t) for t in triples}
    clauses = signotope_clauses(n, chi)
    for x, y, z in triples:
        t = tri[(x, y, z)]
        for line in range(n):
            if line in (x, y, z):
                continue
            first = above(chi, (x, y), line)
            second = above(chi, (x, z), line)
            third = above(chi, (y, z), line)
            for u, v in ((first, second), (second, third)):
                clauses.append([-t, -u, v])
                clauses.append([-t, u, -v])
    kind = getattr(EncType, encoding)
    clauses.extend(at_least_clauses(list(tri.values()), at_least, pool, kind))
    if fold > 1:
        clauses.extend(fold_clauses(n, fold, chi, tri))
    if structure:
        clauses.extend(structure_clauses(n, at_least, tri, pool, kind))
    elif per_line_cap:
        # Each line is cut into n - 2 bounded pieces and each piece borders at
        # most one triangle, so no line touches more than n - 2 triangles.
        for line in range(n):
            mine = [tri[t] for t in triples if line in t]
            clauses.extend(at_most_clauses(mine, n - 2, pool, kind))
    return clauses, chi, tri, pool.top


def turned(n, steps):
    """What `rotate` applied `steps` times does, as a recipe: for each triple
    t, the turned sign is signs[source] flipped or not. Also returns where
    each line goes."""
    recipe = {t: (t, False) for t in combinations(range(n), 3)}
    for _ in range(steps):
        def old(i):
            return n - 1 if i == 0 else i - 1
        recipe = {(a, b, c): (recipe[tuple(sorted((old(a), old(b), old(c))))][0],
                              recipe[tuple(sorted((old(a), old(b), old(c))))][1] != (a == 0))
                  for a, b, c in combinations(range(n), 3)}
    return recipe


def fold_clauses(n, fold, chi, tri):
    """The drawing equals itself turned by 1/fold of a circle.

    2n single turns make a full circle (n of them make a half turn), so a
    turn by 1/fold of a circle is 2n/fold single turns. Each line then moves
    2n/fold places along the cyclic order, and each triangle goes to a
    triangle."""
    if (2 * n) % fold:
        raise ValueError("fold must divide 2n")
    steps = 2 * n // fold
    clauses = []
    for t, (source, flip) in turned(n, steps).items():
        x, y = chi[t], chi[source]
        if flip:
            clauses += [[x, y], [-x, -y]]
        else:
            clauses += [[-x, y], [x, -y]]
        image = tuple(sorted((v - steps) % n for v in t))
        clauses += [[-tri[t], tri[image]], [tri[t], -tri[image]]]
    return clauses


def full_line_bounds(n, at_least):
    """How many full lines a drawing with at least `at_least` triangles has,
    and the least each line must touch. Returns (fewest, most, floor): at
    least `fewest` and at most `most` lines are full, and every line touches
    at least floor triangles, plus one more if it is full.

    Each triangle touches three lines, so the per-line counts add up to at
    least 3k. A line touches at most n - 3 triangles unless it is full, when
    it touches n - 2. So n(n - 3) + F >= 3k, which gives the fewest full
    lines. For even n, Bartholdi, Blanc and Loisel (2008, proof of Theorem
    1.1) show that every full line forces an unused piece on a neighbouring
    line and no unused piece is forced by more than two lines; there are at
    most n(n - 2) - 3k unused pieces, so at most twice that many full lines.
    The floor is what is left for one line when every other line takes as
    much as it can."""
    fewest = max(0, 3 * at_least - n * (n - 3))
    most = n if n % 2 else min(n, 2 * (n * (n - 2) - 3 * at_least))
    floor = 3 * at_least - (n - 1) * (n - 3) - most
    return fewest, most, floor


def structure_clauses(n, at_least, tri, pool, kind):
    """Facts every drawing with at least `at_least` triangles must satisfy,
    written out so the solver does not have to discover them.

    Call a line full when all n - 2 of its bounded pieces border a triangle
    (each piece borders at most one). The counting facts are in
    `full_line_bounds`; a SAT solver cannot add up per-line totals by
    itself, so without them it can spend hours on cases that counting rules
    out at once.

    Turning the plane: moving the last line to the front (see `rotate`)
    gives another drawing with the same triangles, and repeating it brings
    any line to the front. So when some line must be full, line 0 may be
    taken to be one.
    """
    fewest, most, floor = full_line_bounds(n, at_least)
    if fewest > most or floor + 1 > n - 1:
        return [[]]
    lines = [[v for t, v in tri.items() if line in t] for line in range(n)]
    full = [pool.id(("full", line)) for line in range(n)]
    clauses = []
    for line in range(n):
        # touches <= n - 3 + full and >= floor + full
        clauses.extend(at_most_clauses(lines[line] + [-full[line]], n - 2, pool, kind))
        clauses.extend(at_least_clauses(lines[line] + [-full[line]], floor + 1, pool, kind))
    clauses.extend(at_least_clauses(full, fewest, pool, kind))
    clauses.extend(at_most_clauses(full, most, pool, kind))
    if fewest > 0:
        clauses.append([full[0]])
        clauses.extend(at_least_clauses(lines[0], n - 2, pool, kind))
    return clauses


def at_least_clauses(lits, bound, pool, kind):
    """Clauses saying at least `bound` of `lits` are true, including the cases
    the library refuses: nothing to say, or more than there are."""
    from pysat.card import CardEnc

    if bound <= 0:
        return []
    if bound > len(lits):
        return [[]]
    if bound == len(lits):
        return [[x] for x in lits]
    return CardEnc.atleast(lits=lits, bound=bound, vpool=pool, encoding=kind).clauses


def at_most_clauses(lits, bound, pool, kind):
    from pysat.card import CardEnc

    if bound >= len(lits):
        return []
    if bound < 0:
        return [[]]
    if bound == 0:
        return [[-x] for x in lits]
    return CardEnc.atmost(lits=lits, bound=bound, vpool=pool, encoding=kind).clauses


# ------------------------------------------------------------ the checker


def rotate(n, signs):
    """Move the last line to the front: the drawing seen after turning the
    plane until that line's direction passes the vertical. Triples that
    contain the moved line change sign; the triangles stay the same."""
    def old(i):
        return n - 1 if i == 0 else i - 1
    moved = {}
    for a, b, c in combinations(range(n), 3):
        key = tuple(sorted((old(a), old(b), old(c))))
        moved[(a, b, c)] = signs[key] != (a == 0)
    return moved


def mirror(n, signs):
    """The drawing reflected left to right: slopes change sign, so line i
    becomes line n - 1 - i, and above stays above."""
    return {(a, b, c): signs[(n - 1 - c, n - 1 - b, n - 1 - a)] for a, b, c in combinations(range(n), 3)}


def text(signs):
    return "".join("1" if signs[t] else "0" for t in sorted(signs))


def same_drawing(n, first, second):
    """True when `second` is `first` turned, mirrored, or both. These are the
    only ways two numberings of one drawing can differ."""
    target = text(second)
    for start in (first, mirror(n, first)):
        current = start
        for _ in range(2 * n):
            if text(current) == target:
                return True
            current = rotate(n, current)
    return False


def projective_triangles(n, signs):
    """Triangles once the line at infinity is added as a line of its own.

    Besides the bounded triangles, an unbounded region becomes a triangle
    when it is a wedge between two neighbouring ends whose lines meet each
    other before meeting any other line. Choosing a different line to send
    to infinity leaves this number unchanged, so two drawings with different
    numbers cannot be one drawing seen through different charts."""
    orders = crossing_orders(n, signs)
    wedges = 0
    for i in range(n - 1):
        for end in (0, -1):
            if orders[i][end] == i + 1 and orders[i + 1][end] == i:
                wedges += 1
    wedges += orders[0][0] == n - 1 and orders[n - 1][-1] == 0
    wedges += orders[n - 1][0] == 0 and orders[0][-1] == n - 1
    return len(triangles(n, signs)) + wedges


def is_signotope(n, signs):
    """signs maps each sorted triple to True or False."""
    for a, b, c, d in combinations(range(n), 4):
        s = [signs[(a, b, c)], signs[(a, b, d)], signs[(a, c, d)], signs[(b, c, d)]]
        if sum(s[i] != s[i + 1] for i in range(3)) > 1:
            return False
    return True


def crossing_orders(n, signs):
    """For each line, the other lines in the order it meets them, left to right.

    With three lines a < b < c, if chi(abc) is false every line meets the other
    two in increasing number order; if it is true, in decreasing order.
    """
    orders = []
    for i in range(n):
        def before(j, k, i=i):
            key = tuple(sorted((i, j, k)))
            first = min(j, k)
            increasing = not signs[key]
            return -1 if (j == first) == increasing else 1
        orders.append(sorted((j for j in range(n) if j != i), key=cmp_to_key(before)))
        for j, k in combinations(orders[i], 2):
            if before(j, k) != -1:
                raise ValueError("crossing order is not consistent")
    return orders


def triangles(n, signs):
    """Triples whose three lines meet each other consecutively on all three lines."""
    position = [{j: p for p, j in enumerate(order)} for order in crossing_orders(n, signs)]
    found = []
    for x, y, z in combinations(range(n), 3):
        if (abs(position[x][y] - position[x][z]) == 1
                and abs(position[y][x] - position[y][z]) == 1
                and abs(position[z][x] - position[z][y]) == 1):
            found.append((x, y, z))
    return found


def signotope_from_lines(lines):
    """Number straight lines by slope and read off chi; lines must be non-vertical,
    pairwise non-parallel, with no three through a point."""
    slopes = []
    for a, b, c in lines:
        if b == 0:
            raise ValueError("vertical line")
        slopes.append(Fraction(-a, b))
    order = sorted(range(len(lines)), key=lambda i: slopes[i])
    if len(set(slopes)) != len(lines):
        raise ValueError("parallel lines")
    ordered = [lines[i] for i in order]

    def meet(p, q):
        (a1, b1, c1), (a2, b2, c2) = p, q
        det = a1 * b2 - a2 * b1
        return Fraction(b1 * c2 - b2 * c1, det), Fraction(a2 * c1 - a1 * c2, det)

    def height(line, x):
        a, b, c = line
        return Fraction(-(a * x + c), b)

    signs = {}
    for i, j, k in combinations(range(len(lines)), 3):
        x, y = meet(ordered[i], ordered[k])
        h = height(ordered[j], x)
        if y == h:
            raise ValueError("three lines through one point")
        signs[(i, j, k)] = y > h
    return order, signs


# ------------------------------------------------------------- the search


def solve(n, at_least, solver="cadical195", per_line_cap=True, encoding="seqcounter", structure=False,
          fold=1):
    """Run one search to the end and check any drawing it returns.

    CaDiCaL ignores interrupts, so time limits are enforced from outside by
    killing the process; see `run_protocol`.
    """
    from pysat.solvers import Solver

    started = time.time()
    clauses, chi, tri, top = build(n, at_least, per_line_cap, encoding, structure, fold)
    built = time.time() - started
    with Solver(name=solver, bootstrap_with=clauses) as engine:
        answer = engine.solve()
        model = engine.get_model() if answer else None
    result = {
        "n": n, "at_least": at_least, "solver": solver, "encoding": encoding,
        "per_line_cap": per_line_cap, "structure": structure, "fold": fold, "variables": top, "clauses": len(clauses),
        "status": "found" if answer else "impossible",
        "seconds_to_build": round(built, 2), "seconds_to_solve": round(time.time() - started - built, 2),
    }
    if model is not None:
        true = set(v for v in model if v > 0)
        signs = {t: v in true for t, v in chi.items()}
        result["triangles"] = check(n, signs, at_least)
        result["signs"] = text(signs)
    return result


def check(n, signs, at_least):
    """Recount a solver's drawing without using any of its clauses."""
    if not is_signotope(n, signs):
        raise ValueError("not a drawing: four lines change sign twice")
    found = len(triangles(n, signs))
    if found < at_least:
        raise ValueError(f"only {found} triangles, fewer than {at_least}")
    return found


def signs_from_text(n, text):
    """Inverse of the 'signs' string stored in result files."""
    triples = list(combinations(range(n), 3))
    if len(text) != len(triples):
        raise ValueError("wrong length")
    return {t: bit == "1" for t, bit in zip(triples, text)}


def run_protocol(protocol_path, out_dir, workers):
    """Run every task in a frozen protocol, each in its own process with a
    wall-clock limit, and write one JSON file per task plus a summary."""
    import subprocess
    import sys
    from concurrent.futures import ThreadPoolExecutor

    protocol = json.loads(Path(protocol_path).read_text(encoding="utf-8"))
    out = Path(out_dir)
    if out.exists():
        raise SystemExit(f"{out} already exists")
    out.mkdir(parents=True)
    tasks = protocol["tasks"]

    def one(task):
        target = out / f"{task['name']}.json"
        command = [sys.executable, str(Path(__file__).resolve()), "one",
                   "--n", str(task["n"]), "--at-least", str(task["at_least"]),
                   "--solver", task.get("solver", "cadical195"),
                   "--encoding", task.get("encoding", "seqcounter"), "--out", str(target)]
        if task.get("structure"):
            command.append("--structure")
        if task.get("fold", 1) > 1:
            command += ["--fold", str(task["fold"])]
        began = time.time()
        try:
            subprocess.run(command, check=True, capture_output=True, timeout=task["seconds"])
            result = json.loads(target.read_text(encoding="utf-8"))
        except subprocess.TimeoutExpired:
            result = {key: task[key] for key in task if key != "name"}
            result["status"] = "unknown (time limit)"
            target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        result["wall_seconds"] = round(time.time() - began, 1)
        line = {"name": task["name"], **{k: v for k, v in result.items() if k != "signs"}}
        with open(out / "progress.jsonl", "a", encoding="utf-8") as log:
            log.write(json.dumps(line) + "\n")
        return line

    with ThreadPoolExecutor(max_workers=workers) as pool:
        lines = list(pool.map(one, tasks))
    (out / "summary.json").write_text(json.dumps(lines, indent=2) + "\n", encoding="utf-8")
    return lines


def write_cnf(path, n, at_least, encoding="seqcounter", structure=False, fold=1):
    """Write the formula in the standard DIMACS format, for solvers and proof
    checkers outside Python. Returns (variables, clauses)."""
    clauses, _, _, top = build(n, at_least, True, encoding, structure, fold)
    with open(path, "w", encoding="ascii") as out:
        out.write(f"c kobon_sat n={n} at_least={at_least} encoding={encoding} structure={structure} fold={fold}\n")
        out.write(f"p cnf {top} {len(clauses)}\n")
        for clause in clauses:
            out.write(" ".join(map(str, clause)) + " 0\n")
    return top, len(clauses)


def table(protocol_path, run_dir):
    """Markdown table of a finished run, one row per task, against the
    protocol's expectations."""
    protocol = json.loads(Path(protocol_path).read_text(encoding="utf-8"))
    rows = ["| Task | Lines | At least | Structure | Solver | Encoding | Result | Expected | Seconds |",
            "| --- | ---: | ---: | --- | --- | --- | --- | --- | ---: |"]
    for task in protocol["tasks"]:
        path = Path(run_dir) / f"{task['name']}.json"
        if not path.exists():
            result, seconds = "not run", ""
        else:
            record = json.loads(path.read_text(encoding="utf-8"))
            result = record["status"]
            if "triangles" in record:
                result += f" ({record['triangles']})"
            seconds = record.get("seconds_to_solve", task["seconds"])
        rows.append(f"| {task['name']} | {task['n']} | {task['at_least']} | "
                    f"{'yes' if task.get('structure') else 'no'} | {task.get('solver', 'cadical195')} | "
                    f"{task.get('encoding', 'seqcounter')} | {result} | {task.get('expect', '')} | {seconds} |")
    return "\n".join(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    single = commands.add_parser("one", help="one search, no time limit")
    single.add_argument("--n", type=int, required=True)
    single.add_argument("--at-least", type=int, required=True)
    single.add_argument("--solver", default="cadical195")
    single.add_argument("--encoding", default="seqcounter")
    single.add_argument("--no-line-cap", action="store_true")
    single.add_argument("--structure", action="store_true", help="add the facts in structure_clauses")
    single.add_argument("--fold", type=int, default=1, help="only drawings with this turning symmetry")
    single.add_argument("--out", required=True, help="new JSON file for the result")
    batch = commands.add_parser("protocol", help="every task in a protocol file, with time limits")
    batch.add_argument("protocol")
    batch.add_argument("--out", required=True, help="new folder for the results")
    batch.add_argument("--workers", type=int, default=4)
    dimacs = commands.add_parser("cnf", help="write one formula as a DIMACS file")
    dimacs.add_argument("--n", type=int, required=True)
    dimacs.add_argument("--at-least", type=int, required=True)
    dimacs.add_argument("--encoding", default="seqcounter")
    dimacs.add_argument("--structure", action="store_true")
    dimacs.add_argument("--fold", type=int, default=1)
    dimacs.add_argument("--out", required=True)
    report = commands.add_parser("table", help="markdown table of a finished protocol run")
    report.add_argument("protocol")
    report.add_argument("run")
    args = parser.parse_args()
    if args.command == "cnf":
        if Path(args.out).exists():
            raise SystemExit(f"{args.out} already exists")
        print(write_cnf(args.out, args.n, args.at_least, args.encoding, args.structure, args.fold))
        return
    if args.command == "table":
        print(table(args.protocol, args.run))
        return
    if args.command == "protocol":
        for line in run_protocol(args.protocol, args.out, args.workers):
            print(json.dumps(line))
        return
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f"{out} already exists")
    out.parent.mkdir(parents=True, exist_ok=True)
    result = solve(args.n, args.at_least, args.solver, not args.no_line_cap, args.encoding, args.structure,
                   args.fold)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "signs"}, indent=2))


if __name__ == "__main__":
    main()
