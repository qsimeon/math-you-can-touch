"""Independent agreement is required before a local result may be displayed."""
import hashlib
from pathlib import Path
from .geometry import triangles_by_adjacency
from .oracle import triangles_by_interior
from .io import load_solution, validate_lines


def source_fingerprint():
    """Identity of both algorithms and their input boundary, excluding presentation."""
    root = Path(__file__).parent
    digest = hashlib.sha256()
    for name in ['io.py', 'geometry.py', 'oracle.py', 'verify.py']:
        digest.update(name.encode() + b'\0' + (root/name).read_bytes() + b'\0')
    return digest.hexdigest()


def verify_lines(lines, n=18):
    valid = validate_lines([list(row) for row in lines], n)
    primary = triangles_by_adjacency(valid)
    independent = triangles_by_interior(valid)
    if primary != independent:
        raise ValueError('independent verifiers disagree on triangle indices')
    return {'n':n, 'score':len(primary), 'triangle_line_indices':[list(t) for t in primary],
            'verified':True, 'verification':'two local exact-arithmetic algorithms agree',
            'verifier_identity':source_fingerprint(), 'official_evaluator_run':False,
            'claim':'This arrangement achieves this count. No optimality or novelty claim.'}


def verify_file(path, n=18):
    result = verify_lines(load_solution(path,n),n)
    result['solution_sha256'] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return result
