#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import experiment_structural_closure_v06 as v06
MANIFEST=ROOT/'benchmarks/runtime-traces/audits/repo-behavior-witness-suite-a-v0.2.1-corrected.json'

def main():
    m=json.loads(MANIFEST.read_text(encoding='utf-8'))
    if m.get('status')!='corrected_after_ground_truth_audit_not_unseen':
        raise RuntimeError('unexpected audit status')
    r=v06.evaluate(v06.build_cache(m),20)
    print(json.dumps({
      'experiment':'repo-behavior-witness-suite-a-v0.2.1-corrected-audit',
      'status':'audit_only_not_unseen',
      'policy_changed':False,
      'tasks':r['tasks'],'hard_gate':r['hard_gate'],'frontier_hits':r['frontier_hits'],
      'witness_hits':r['witness_hits'],'false_direct':r['false_direct'],
      'task_rows':r['task_rows'],
      'claim_boundary':'Ground-truth correction audit only. This rerun is not fresh unseen evidence.'
    }, indent=2))
if __name__=='__main__': main()
