#!/usr/bin/env python3
"""Build blind semantic-judge packets from task inputs only.

Input schema contains task_id, repository, commit_sha, and prompt. This module
has no label-manifest path and never reads expected files, symbols, witnesses,
or source hashes. Candidate generation and evidence realization reuse frozen
ACE-S v0.6.0 behavior.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import experiment_structural_closure_v06 as v06

FORBIDDEN={'expected_file','expected_symbol','witnesses','witness_id','source_blob_sha','ground_truth','benchmark_claim','source_blobs'}


def reject_labels(value, where='root'):
    if isinstance(value,dict):
        bad=FORBIDDEN.intersection(value)
        if bad:
            raise RuntimeError(f'forbidden label fields at {where}: {sorted(bad)}')
        for k,v in value.items(): reject_labels(v,f'{where}.{k}')
    elif isinstance(value,list):
        for i,v in enumerate(value): reject_labels(v,f'{where}[{i}]')


def build_task(task):
    repo=v06.fixed.base.ensure_repo(task['repository'],task['commit_sha'])
    exact_terms=v06.fixed.rank_v03.smart_query_terms(task['prompt'])
    exact_raw,_=v06.fixed.behavior_v03.decode_safe_grep(repo,exact_terms)
    exact_by=v06.fixed.base.parse_hits(exact_raw,exact_terms)
    exact_ranked=v06.fixed.rank_v041.certified_rank(exact_by,exact_terms)
    for i,row in enumerate(exact_ranked,1): row['rank']=i
    proof_path,proof_symbols=v06.proof_v06.safe_direct_proof(exact_by,task['prompt'])

    recall_terms=v06.fixed.frontier_v02.prefix_terms(exact_terms)
    recall_raw,_=v06.fixed.behavior_v03.decode_safe_grep(repo,recall_terms)
    recall_by=v06.fixed.base.parse_hits(recall_raw,recall_terms)
    recall_ranked=v06.fixed.rank_v03.smart_rank_files(recall_by,recall_terms)
    for i,row in enumerate(recall_ranked,1): row['rank']=i

    if proof_path is not None:
        frontier=[r for r in exact_ranked if r['path']==proof_path][:1]
        mode='DIRECT_CERTIFIED'
    else:
        frontier=v06.fixed.frontier_v02.compose_frontier(exact_ranked,recall_ranked,v06.EXACT_QUOTA)
        mode='NEEDS_SEMANTIC_JUDGE'

    terms=exact_terms+recall_terms
    cards=[v06.behavior_card(repo,row,terms,20) for row in frontier]
    return {
      'task_id':task['task_id'],
      'prompt':task['prompt'],
      'mode':mode,
      'proof_symbols':proof_symbols if mode=='DIRECT_CERTIFIED' else [],
      'candidates':[
        {'path':c['path'],'windows':c['windows'],'records':c['records']}
        for c in cards
      ]
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('input_json')
    args=ap.parse_args()
    data=json.loads(Path(args.input_json).read_text(encoding='utf-8'))
    reject_labels(data)
    tasks=data.get('tasks',[])
    out={
      'packet_schema':'luna-blind-semantic-packet-v0.1',
      'contract':'benchmarks/runtime-traces/contracts/luna-blind-semantic-v0.1.json',
      'frozen_policy':{'frontier_top_k':8,'exact_quota':4,'spans':[4,16,24],'max_windows':5,'merge_gap':0,'structural_closure_cap_lines':20},
      'tasks':[build_task(t) for t in tasks],
      'label_fields_present':False
    }
    reject_labels(out)
    print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
