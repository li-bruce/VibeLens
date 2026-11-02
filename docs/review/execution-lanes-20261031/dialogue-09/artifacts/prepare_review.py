"""Review the unchanged business scope and current normal upgrade candidate."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
path = ROOT / 'resume-first-integration-20261031/review.json'
(OUT / 'previous-candidate-review.json').write_bytes(path.read_bytes())
review = json.loads(path.read_text(encoding='utf-8'))
review['candidate_id'] = json.loads((OUT / 'inspect.result.json').read_text(encoding='utf-8'))['candidate_id']
review['decisions']['probes']['reason'] = (
    'Normal canonical control-context upgrade: three managed runtime files, no conflicts; '
    'viewer and native execution core unchanged. Business source, U001/U002 and all independent '
    'expectations preserved. Observation outputs and scratch route to review/retest-20261101-03. '
    'Retest current four reports, actual large-view controls, scoped visibility, stopped-recording '
    'filter/replay and observer exclusion before accept. Reuse unaffected prior Web evidence '
    'with provenance; retain 3D orthogonal/bus self-relation limitations.')
path.write_text(json.dumps(review, indent=2) + '\n', encoding='utf-8')
(OUT / 'current-candidate-review.json').write_bytes(path.read_bytes())
print(json.dumps({'candidate_id': review['candidate_id'], 'baseline_sha256': hashlib.sha256(
    (ROOT / 'resume-first-integration-20261031/baseline.json').read_bytes()).hexdigest()}))
