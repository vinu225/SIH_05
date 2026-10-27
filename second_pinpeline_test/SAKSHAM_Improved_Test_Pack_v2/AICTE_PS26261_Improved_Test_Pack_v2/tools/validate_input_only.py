#!/usr/bin/env python3
"""Validate the input-only archive without requiring or exposing the answer key."""
import argparse,csv,hashlib,json
from pathlib import Path

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default='.'); args=ap.parse_args()
    root=Path(args.root).resolve(); inp=root/'input_data'; problems=[]
    cases=json.loads((inp/'cases.json').read_text(encoding='utf-8'))['cases']
    ids=[c['case_id'] for c in cases]
    if len(cases)!=30 or len(set(ids))!=30: problems.append(f'case count/uniqueness failed: {len(cases)} cases')
    if any(any(k.startswith('expected_') for k in c) for c in cases): problems.append('expected outcome fields found in input cases')
    for c in cases:
        for rel in c.get('document_files',[]):
            p=(inp/rel).resolve()
            if not p.is_file() or inp.resolve() not in p.parents: problems.append(f"missing or unsafe path: {c['case_id']} -> {rel}")
    manifest=inp/'manifest_sha256.csv'
    with manifest.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    for row in rows:
        p=inp/row['relative_path']
        if not p.is_file(): problems.append('manifest file missing: '+row['relative_path'])
        elif sha(p)!=row['sha256']: problems.append('hash mismatch: '+row['relative_path'])
    actual={p.relative_to(inp).as_posix() for p in inp.rglob('*') if p.is_file() and p.name!='manifest_sha256.csv'}
    listed={r['relative_path'] for r in rows}
    if actual!=listed: problems.append(f'manifest coverage mismatch: unlisted={sorted(actual-listed)}, absent={sorted(listed-actual)}')
    print(f'Input-only validation: {len(cases)} cases, {len(rows)} manifest entries, {len(problems)} issue(s).')
    for p in problems: print('FAIL:',p)
    return 1 if problems else 0
if __name__=='__main__': raise SystemExit(main())
