#!/usr/bin/env python3
"""Verify detached CMS fixture integrity/trust with OpenSSL. Not an embedded PDF signature parser."""
import argparse,subprocess,sys,tempfile
from pathlib import Path

def run(args): return subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
def verify(root, payload, sig, cafile):
    return run(['openssl','cms','-verify','-binary','-inform','DER','-in',str(sig),'-content',str(payload),'-CAfile',str(cafile),'-out',str(Path(tempfile.gettempdir())/'saksham-cms-verify-output.bin')])
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',default='.');a=ap.parse_args();root=Path(a.root).resolve(); s=root/'input_data/synthetic_documents/signature_fixtures'
    rootca=s/'test_root_A.pem'
    tests=[
      ('SYN-018 valid trusted detached CMS',s/'AICTE-SYN-018_document.pdf',s/'AICTE-SYN-018_signature.p7s',rootca,True),
      ('SYN-019 changed payload invalidates signature',s/'AICTE-SYN-019_document.pdf',s/'AICTE-SYN-019_signature.p7s',rootca,False),
      ('Untrusted signature rejected under trusted test root',s/'aux_document_C.pdf',s/'aux_signature_C.p7s',rootca,False),
      ('Same untrusted signature verifies under its own synthetic root',s/'aux_document_C.pdf',s/'aux_signature_C.p7s',s/'test_root_C.pem',True),
    ]
    errors=0
    for label,payload,sig,ca,expected in tests:
        if not all(p.is_file() for p in [payload,sig,ca]): print('FAIL missing fixture:',label); errors+=1; continue
        r=verify(root,payload,sig,ca); ok=(r.returncode==0)==expected
        print(('PASS' if ok else 'FAIL')+' | '+label+f' | exit={r.returncode}')
        if not ok: print((r.stderr or r.stdout).strip()); errors+=1
    print('NOTE: detached CMS only; these fixtures are not embedded PDF /ByteRange signatures and both certificate roots are synthetic. A valid signature under an untrusted root is not an issuer identity assertion.')
    return 1 if errors else 0
if __name__=='__main__': raise SystemExit(main())
