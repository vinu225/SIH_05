import json
from pathlib import Path

base_dir = Path(r"second_pinpeline_test\SAKSHAM_Input_Only_Dataset_v2\AICTE_PS26261_Improved_Input_Data_v2\input_data")
cases_file = base_dir / "cases.json"
data = json.loads(cases_file.read_text(encoding="utf-8"))

for c in data.get("cases", []):
    cid = c["case_id"]
    app_id = c["application_id"]
    inst_name = c["institution_name"]
    inst_id = c["institution_id"]
    cat = c["application_category"]
    docs = c["document_files"]
    print(f"\n==================================================")
    print(f"CASE: {cid} | APP: {app_id} | INST: {inst_id} ({inst_name}) | CAT: {cat}")
    print(f"FILES ({len(docs)}):")
    for doc in docs:
        p = base_dir / doc
        ext = p.suffix.lower()
        size = p.stat().st_size
        print(f"  - [{ext}] {p.name} ({size} bytes)")
        if ext in [".txt", ".json"]:
            lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
            first_few = " | ".join([line.strip() for line in lines[:3] if line.strip()])
            print(f"    Sample: {first_few[:120]}")
