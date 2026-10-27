import json
from pathlib import Path

base_dir = Path(r"second_pinpeline_test\SAKSHAM_Input_Only_Dataset_v2\AICTE_PS26261_Improved_Input_Data_v2\input_data")
cases_file = base_dir / "cases.json"
data = json.loads(cases_file.read_text(encoding="utf-8"))

print(f"Dataset ID: {data.get('dataset_id')}")
print(f"Total Cases: {data.get('case_count')}")

for c in data.get("cases", []):
    files = c.get("document_files", [])
    exts = [Path(f).suffix for f in files]
    types = []
    for f in files:
        if "applications" in f:
            types.append("app_text")
        elif "identity" in f:
            types.append("authority/id")
        elif "scanned" in f:
            types.append("scan")
        elif "infrastructure" in f:
            types.append("infra_img")
        elif "signature" in f:
            types.append("sig_fixture")
        else:
            types.append("other")
    print(f"{c['case_id']} | {c['application_id']} | {c['institution_id']} | {c['application_category']} | exts={exts} | types={types} | files={[Path(f).name for f in files]}")
