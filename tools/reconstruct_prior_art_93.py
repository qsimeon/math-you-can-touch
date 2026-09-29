"""Reconstruct exact hill-legal lines from the pinned LineOrder SVG, without executing it.

This is data extraction followed by deterministic rational rounding, not a
claim that the rounded lines equal the original author's unpublished coordinates.
The output must pass both independent exact geometry checkers.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from kobon.io import canonical, validate_lines
from kobon.verify import verify_lines

SOURCE_SHA256 = "31b4603ac4db28ca9d6b03ab66a93d1e9d1e5405a4b246e6edef6c3976553544"
SCALE = 10**6


def endpoint_line(values):
    """Round slope and intercept to six decimals on the better-conditioned axis."""
    x1, y1, x2, y2 = map(Fraction, values)
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        raise ValueError("line endpoints coincide")
    if abs(dx) >= abs(dy):
        slope = dy / dx
        intercept = y1 - slope * x1
        coeffs = (round(slope * SCALE), -SCALE, round(intercept * SCALE))
    else:
        slope = dx / dy
        intercept = x1 - slope * y1
        coeffs = (-SCALE, round(slope * SCALE), round(intercept * SCALE))
    return list(canonical(coeffs))


def reconstruct(raw):
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("source SVG identity mismatch")
    root = ET.fromstring(raw)
    lines = [endpoint_line([elem.attrib[k] for k in ("x1", "y1", "x2", "y2")])
             for elem in root.findall("{http://www.w3.org/2000/svg}line")]
    validate_lines(lines, 18)
    return {"lines": lines}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    solution = reconstruct(args.source.read_bytes())
    report = verify_lines(solution["lines"])
    print(json.dumps({"solution": solution, "verification": report,
                      "rounding": "exact Fraction arithmetic; nearest integer, ties to even",
                      "scale": SCALE, "source_sha256": SOURCE_SHA256}, indent=2))


if __name__ == "__main__":
    main()
