"""Strict data-only input contract matching the published hill overview."""
import json
from math import gcd
from pathlib import Path

MAX_COEFFICIENT = 10**30
MAX_BYTES = 65536


def canonical(line):
    """Primitive integer coefficients, first nonzero normal coefficient positive."""
    a, b, c = line
    divisor = gcd(gcd(abs(a), abs(b)), abs(c))
    sign = 1 if (a if a else b) > 0 else -1
    return tuple(sign * x // divisor for x in line)


def validate_lines(lines, n=18):
    if type(n) is not int or not 3 <= n <= 100:
        raise ValueError('n must be an integer from 3 through 100')
    if not isinstance(lines, list) or len(lines) != n:
        raise ValueError(f'exactly {n} lines required')
    seen = set()
    result = []
    for line in lines:
        if not isinstance(line, list) or len(line) != 3:
            raise ValueError('each line must be a triple')
        if any(type(x) is not int or abs(x) > MAX_COEFFICIENT for x in line):
            raise ValueError('coefficients must be integers with magnitude <= 10^30')
        if line[0] == line[1] == 0:
            raise ValueError('line normal cannot be zero')
        key = canonical(line)
        if key in seen:
            raise ValueError('proportional duplicate lines')
        seen.add(key)
        result.append(tuple(line))
    return result


def _object(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError('duplicate JSON key')
        data[key] = value
    return data


def _constant(value):
    raise ValueError(f'invalid JSON constant: {value}')


def load_solution(path, n=18):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('solution must be a regular, non-symlink file')
    with path.open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('solution exceeds 65536 bytes')
    try:
        data = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_object,
                          parse_constant=_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError('invalid UTF-8 JSON') from exc
    if not isinstance(data, dict) or set(data) != {'lines'}:
        raise ValueError('only the lines field is allowed')
    return validate_lines(data['lines'], n)
