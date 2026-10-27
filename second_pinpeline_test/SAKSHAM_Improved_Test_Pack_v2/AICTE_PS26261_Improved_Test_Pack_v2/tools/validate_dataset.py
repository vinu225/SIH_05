#!/usr/bin/env python3
"""Validate structure, referenced files, manifest hashes, and key fixture properties."""
import argparse, csv, hashlib, json, sys
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',default='.',help='Improved pack root')
    args=ap.parse_args(); root=Path(args.root).resolve(); inp=root/'input_data'; ans=root/'answer_key'
    issues=[]; checks=[]
    def check(name,cond,detail=''):
        checks.append((name,bool(cond),detail))
        if not cond: issues.append((name,detail))
    try:
        cases=json.loads((inp/'cases.json').read_text(encoding='utf-8'))['cases']
        answer=json.loads((ans/'expected_outcomes.json').read_text(encoding='utf-8'))['cases']
        check('exactly 30 input cases',len(cases)==30,str(len(cases)))
        check('exactly 30 answer cases',len(answer)==30,str(len(answer)))
        ids=[c['case_id'] for c in cases]; aids=[c['case_id'] for c in answer]
        check('input case IDs unique',len(ids)==len(set(ids)))
        check('answer case IDs unique',len(aids)==len(set(aids)))
        check('input/answer case IDs equal',set(ids)==set(aids))
        check('input does not contain expected outcome fields',all(not any(k.startswith('expected_') for k in c) for c in cases))
        referenced=[]
        for c in cases:
            for f in c.get('document_files',[]):
                p=(inp/f).resolve()
                check(f"file exists for {c['case_id']}",p.is_file() and (inp in p.parents),f)
                referenced.append(f)
        check('all cases have at least one input file',all(c.get('document_files') for c in cases))
        # Input hash manifest. Manifest itself is excluded to avoid self-hashing recursion.
        manifest=inp/'manifest_sha256.csv'; manifest_ok=manifest.exists(); m_count=0
        if manifest_ok:
            with manifest.open(encoding='utf-8-sig',newline='') as f:
                rows=list(csv.DictReader(f))
            for row in rows:
                p=inp/row['relative_path']; m_count+=1
                check('manifest file exists',p.is_file(),row['relative_path'])
                if p.is_file(): check('manifest hash matches',sha(p)==row['sha256'],row['relative_path'])
            actual={p.relative_to(inp).as_posix() for p in inp.rglob('*') if p.is_file() and p.name!='manifest_sha256.csv'}
            listed={r['relative_path'] for r in rows}
            check('manifest coverage complete',actual==listed,f'unlisted={sorted(actual-listed)[:5]} missing={sorted(listed-actual)[:5]}')
        check('input hash manifest present',manifest_ok)
        # exact duplicate pair
        d1=inp/'synthetic_documents/applications/AICTE-SYN-015_attachment_A.txt'
        d2=inp/'synthetic_documents/applications/AICTE-SYN-015_attachment_B.txt'
        check('SYN-015 fixture contents byte-identical',d1.exists() and d2.exists() and sha(d1)==sha(d2))
        # actual QR asset exists
        check('SYN-020 QR PNG exists',(inp/'synthetic_documents/identity_and_authority_docs/AICTE-SYN-020_certificate_qr_reference.png').is_file())
        # actual raster evidence exists
        check('SYN-023-025 raster evidence exists',all((inp/'synthetic_documents/infrastructure_evidence'/f'synthetic_{name}_visual_evidence_{i:03d}.png').is_file() for i,name in [(23,'lab'),(24,'classroom'),(25,'library')]))
        # scanned image-only PDF assets
        check('two OCR scan PDF fixtures exist',all((inp/'synthetic_documents/scanned_ocr'/f).is_file() for f in ['AICTE-SYN-013_application_scan.pdf','AICTE-SYN-014_undertaking_scan.pdf']))
        print('Dataset validation summary:')
        for name,ok,detail in checks: print(('PASS' if ok else 'FAIL')+' | '+name+((' | '+detail) if detail else ''))
        print(f'\n{sum(1 for _,ok,_ in checks if ok)}/{len(checks)} checks passed; manifest entries={m_count}.')
        return 1 if issues else 0
    except Exception as e:
        print(f'FATAL: {e}',file=sys.stderr); return 2
if __name__=='__main__': raise SystemExit(main())
