#!/usr/bin/env python3
from __future__ import annotations
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import experiment_structural_closure_v06 as v06
SUITE=ROOT/'benchmarks/runtime-traces/sealed/repo-behavior-witness-suite-a-v0.3.json'

def main():
    manifest=json.loads(SUITE.read_text(encoding='utf-8'))
    if manifest.get('status')!='sealed_before_first_evaluation':
        raise RuntimeError('suite not sealed')
    if len(manifest.get('tasks',[]))!=6:
        raise RuntimeError('expected six tasks')
    r=v06.evaluate(v06.build_cache(manifest),20)
    out={
      'experiment':'repo-behavior-witness-suite-a-v0.3',
      'status':'first_unseen_evaluation_result',
      'tasks':r['tasks'],'hard_gate':r['hard_gate'],
      'frontier_hits':r['frontier_hits'],'witness_hits':r['witness_hits'],
      'false_direct':r['false_direct'],
      'worst_case_unique_source_lines':r['worst_case_unique_source_lines'],
      'mean_unique_source_lines':r['mean_unique_source_lines'],
      'mean_extension_lines':r['mean_extension_lines'],
      'task_rows':r['task_rows'],
      'frozen_policy':{'frontier_top_k':8,'exact_quota':4,'spans':[4,16,24],'max_windows':5,'merge_gap':0,'structural_closure_cap_lines':20},
      'claim_boundary':'First evaluation of fresh Suite A v0.3 with previously frozen v0.6.0 policy.'
    }
    print(json.dumps(out,indent=2,ensure_ascii=False))
if __name__=='__main__': main()
