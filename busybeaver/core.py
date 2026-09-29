"""Deterministic bounded simulation for fully labeled two-state/two-symbol tables."""
import hashlib
import itertools
import json
import time
from pathlib import Path

ACTIONS = tuple((write, move, next_state)
                for write in (0, 1)
                for move in ('L', 'R')
                for next_state in ('A', 'B', 'H'))
SLOTS = (('A', 0), ('A', 1), ('B', 0), ('B', 1))
STATUSES = frozenset({'HALTED', 'NONHALTING_BY_TRANSLATION_CYCLE', 'UNKNOWN_AT_LIMIT'})


def validate_table(table):
    """Return a canonical immutable table or reject anything outside the frozen model."""
    if not isinstance(table, (list, tuple)) or len(table) != 2:
        raise ValueError('table must have exactly two state rows')
    canonical = []
    for row in table:
        if not isinstance(row, (list, tuple)) or len(row) != 2:
            raise ValueError('each state row must have exactly two symbol actions')
        actions = []
        for action in row:
            if not isinstance(action, (list, tuple)) or len(action) != 3:
                raise ValueError('each action must be [write, move, next]')
            write, move, next_state = action
            if type(write) is not int or write not in (0, 1):
                raise ValueError('write must be integer 0 or 1')
            if move not in ('L', 'R'):
                raise ValueError('move must be L or R')
            if next_state not in ('A', 'B', 'H'):
                raise ValueError('next state must be A, B, or H')
            actions.append((write, move, next_state))
        canonical.append(tuple(actions))
    return tuple(canonical)


def table_as_json(table):
    return [[list(action) for action in row] for row in validate_table(table)]


def enumerate_tables():
    """Yield each of the frozen model's 12^4 labeled tables once, in product order."""
    for actions in itertools.product(ACTIONS, repeat=4):
        yield (actions[:2], actions[2:])


def normalized_configuration(state, head, ones):
    return state, tuple(sorted(position - head for position in ones))


def _cycle_result(step, state, head, ones, seen):
    normalized = normalized_configuration(state, head, ones)
    earlier = seen.get(normalized)
    if earlier is None:
        seen[normalized] = (step, head)
        return None
    previous_step, previous_head = earlier
    return {
        'status': 'NONHALTING_BY_TRANSLATION_CYCLE',
        'steps': step,
        'repeat': {
            'previous_step': previous_step,
            'current_step': step,
            'period': step - previous_step,
            'previous_head': previous_head,
            'current_head': head,
            'shift': head - previous_head,
            'state': state,
            'normalized_ones': list(normalized[1]),
        },
    }


def _halt_result(step, ones):
    return {'status': 'HALTED', 'steps': step, 'ones': len(ones)}


def _unknown_result(step_limit):
    return {'status': 'UNKNOWN_AT_LIMIT', 'steps': step_limit}


def simulate_set(table, *, step_limit=100, trace=False):
    """Simulate with a sparse set of one positions and optional post-step trace."""
    table = validate_table(table)
    if type(step_limit) is not int or step_limit < 1:
        raise ValueError('step_limit must be a positive integer')
    state, head, ones = 'A', 0, set()
    seen = {normalized_configuration(state, head, ones): (0, 0)}
    history = [{'step': 0, 'state': state, 'head': head, 'ones': []}] if trace else None
    for step in range(1, step_limit + 1):
        write, move, next_state = table[0 if state == 'A' else 1][1 if head in ones else 0]
        if write:
            ones.add(head)
        else:
            ones.discard(head)
        head += -1 if move == 'L' else 1
        if trace:
            history.append({'step': step, 'state': next_state, 'head': head, 'ones': sorted(ones)})
        if next_state == 'H':
            result = _halt_result(step, ones)
            if trace:
                result['trace'] = history
            return result
        state = next_state
        result = _cycle_result(step, state, head, ones, seen)
        if result is not None:
            if trace:
                result['trace'] = history
            return result
    result = _unknown_result(step_limit)
    if trace:
        result['trace'] = history
    return result


def simulate_dict(table, *, step_limit=100):
    """Independent simulation using a sparse position-to-symbol dictionary."""
    table = validate_table(table)
    if type(step_limit) is not int or step_limit < 1:
        raise ValueError('step_limit must be a positive integer')
    state, head, tape = 'A', 0, {}
    seen = {('A', ()): (0, 0)}
    for step in range(1, step_limit + 1):
        write, move, next_state = table[0 if state == 'A' else 1][tape.get(head, 0)]
        if write:
            tape[head] = 1
        else:
            tape.pop(head, None)
        head += -1 if move == 'L' else 1
        if next_state == 'H':
            return _halt_result(step, tape)
        state = next_state
        normalized = (state, tuple(sorted(position - head for position, value in tape.items() if value)))
        earlier = seen.get(normalized)
        if earlier is not None:
            previous_step, previous_head = earlier
            return {
                'status': 'NONHALTING_BY_TRANSLATION_CYCLE',
                'steps': step,
                'repeat': {
                    'previous_step': previous_step,
                    'current_step': step,
                    'period': step - previous_step,
                    'previous_head': previous_head,
                    'current_head': head,
                    'shift': head - previous_head,
                    'state': state,
                    'normalized_ones': list(normalized[1]),
                },
            }
        seen[normalized] = (step, head)
    return _unknown_result(step_limit)


def compare_simulations(table, *, step_limit=100):
    first = simulate_set(table, step_limit=step_limit)
    second = simulate_dict(table, step_limit=step_limit)
    if first != second:
        raise AssertionError(f'simulator disagreement: set={first!r}, dict={second!r}')
    return first


def source_identity():
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob('*.py')):
        digest.update(path.name.encode('utf-8') + b'\0' + path.read_bytes() + b'\0')
    return digest.hexdigest()


def replay_record(record, *, step_limit=100):
    if not isinstance(record, dict) or 'table' not in record or 'result' not in record:
        raise ValueError('record must contain table and result')
    result = simulate_dict(record['table'], step_limit=step_limit)
    if result != record['result']:
        raise AssertionError(f"record {record.get('index', '<unknown>')} does not replay")
    return result


def run_experiment(destination, *, step_limit=100, deadline_seconds=120):
    """Execute the complete frozen enumeration on one worker and write auditable artifacts."""
    if type(step_limit) is not int or step_limit < 1:
        raise ValueError('step_limit must be a positive integer')
    if not isinstance(deadline_seconds, (int, float)) or not 0 < deadline_seconds <= 120:
        raise ValueError('deadline_seconds must be positive and at most 120')
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / 'ledger.jsonl').exists():
        raise FileExistsError(f'experiment ledger already exists: {destination / "ledger.jsonl"}')
    started = time.monotonic()
    source_hash = source_identity()
    counts = {'HALTED': 0, 'NONHALTING_BY_TRANSLATION_CYCLE': 0, 'UNKNOWN_AT_LIMIT': 0}
    champion_table = champion_result = None
    processed = 0
    agreement = {'compared': 0, 'mismatches': 0, 'invariants': {
        'enumerated_tables': 12 ** 4,
        'single_worker': True,
        'all_records_replayable': True,
        'all_simulations_agree': True,
    }}
    with (destination / 'ledger.jsonl').open('w', encoding='utf-8') as ledger:
        for index, table in enumerate(enumerate_tables()):
            if time.monotonic() - started >= deadline_seconds:
                raise TimeoutError(f'deadline reached after {processed} of {12 ** 4} tables')
            result = compare_simulations(table, step_limit=step_limit)
            record = {'index': index, 'table': table_as_json(table), 'result': result,
                      'source_sha256': source_hash}
            ledger.write(json.dumps(record, separators=(',', ':')) + '\n')
            counts[result['status']] += 1
            processed += 1
            agreement['compared'] += 1
            if result['status'] == 'HALTED':
                if champion_result is None or (result['steps'], result['ones']) > (champion_result['steps'], champion_result['ones']):
                    champion_table, champion_result = table, result
    if processed != 12 ** 4:
        raise AssertionError('incomplete enumeration')
    if sum(counts.values()) != processed:
        raise AssertionError('classification counts do not cover the ledger')
    replayed = 0
    with (destination / 'ledger.jsonl').open(encoding='utf-8') as ledger:
        for line in ledger:
            replay_record(json.loads(line), step_limit=step_limit)
            replayed += 1
    if replayed != processed:
        raise AssertionError('ledger replay did not cover every table')
    champion_trace = simulate_set(champion_table, step_limit=step_limit, trace=True)
    if champion_trace['status'] != 'HALTED' or champion_trace['steps'] != champion_result['steps']:
        raise AssertionError('champion trace replay failed')
    summary = {
        'model': 'fully labeled deterministic 2-state/2-symbol tables; blank 0 tape; A at head 0',
        'total': processed,
        'halted': counts['HALTED'],
        'nonhalting': counts['NONHALTING_BY_TRANSLATION_CYCLE'],
        'unknown': counts['UNKNOWN_AT_LIMIT'],
        'step_limit': step_limit,
        'max_halted_steps': champion_result['steps'],
        'max_halted_ones': max(record['result']['ones'] for record in _halt_records(destination / 'ledger.jsonl')),
        'elapsed_seconds': round(time.monotonic() - started, 6),
        'deadline_seconds': deadline_seconds,
        'source_sha256': source_hash,
        'workers': 1,
    }
    (destination / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    agreement['replayed'] = replayed
    agreement['source_sha256'] = source_hash
    agreement['verdict'] = 'PASS'
    (destination / 'agreement.json').write_text(json.dumps(agreement, indent=2) + '\n', encoding='utf-8')
    sources = [
        {'title': 'Eric W. Weisstein, “Busy Beaver”, MathWorld', 'url': 'https://mathworld.wolfram.com/BusyBeaver.html'},
        {'title': 'bbchallenge Wiki, “Wiki - bbchallenge”', 'url': 'https://wiki.bbchallenge.org/'},
    ]
    site_data = {
        'model': summary['model'],
        'summary': {key: summary[key] for key in ('total', 'halted', 'nonhalting', 'unknown', 'step_limit', 'max_halted_steps', 'max_halted_ones')},
        'champion': {'table': table_as_json(champion_table), 'trace': champion_trace['trace']},
        'sources': sources,
        'limitations': [
            'This is a bounded local teaching experiment, not a novelty claim or a proof of any Busy Beaver value.',
            'UNKNOWN_AT_LIMIT means only that 100 steps ended without a halt or an exact translation-cycle witness.',
            'Translation-cycle detection is a sufficient witness for some non-halting behaviors, not a complete non-halting decider.',
            'No BB(6) solution is claimed.',
        ],
    }
    (destination / 'site-data.json').write_text(json.dumps(site_data, indent=2) + '\n', encoding='utf-8')
    return summary


def _halt_records(ledger_path):
    with ledger_path.open(encoding='utf-8') as ledger:
        for line in ledger:
            record = json.loads(line)
            if record['result']['status'] == 'HALTED':
                yield record
