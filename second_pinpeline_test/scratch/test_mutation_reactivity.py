import json
import shutil
import urllib.request
from pathlib import Path

BASE_URL = "http://localhost:8000"

# Copy Land_Title_Deed.pdf and Fire_Safety_NOC.pdf from INST-01-COMPLIANT into an isolated test dir
src_dir = Path("test_data/aicte_institutions/INST-01-COMPLIANT")
test_dir = Path("test_data/aicte_institutions/SYN-MUTATION-TEST")
if test_dir.exists():
    shutil.rmtree(test_dir)
test_dir.mkdir(parents=True, exist_ok=True)

for f in ["Land_Title_Deed.pdf", "Faculty_Portfolio.pdf", "Fire_Safety_NOC.pdf"]:
    shutil.copy(src_dir / f, test_dir / f)

# Baseline metadata with 4.5 acres (matching deed)
meta = {
    "application_id": "APP-2024-SYN-MUTATION-TEST",
    "institution_name": "Mutation Test Institute",
    "institution_category": "UG Engineering & Technology",
    "declared_land_acres": 4.5,
    "total_approved_students": 240,
    "created_at": "2026-10-26T12:00:00"
}
(test_dir / "application_metadata.json").write_text(json.dumps(meta, indent=2))

# 1. Run baseline evaluation
req = urllib.request.Request(f"{BASE_URL}/api/v1/evaluate/SYN-MUTATION-TEST", data=b"", method="POST")
with urllib.request.urlopen(req) as resp:
    res1 = json.loads(resp.read().decode())
    land_findings1 = [f for f in res1["findings"] if "LAND" in f["finding_id"]]
    print("Baseline Land Finding:", land_findings1[0]["outcome"] if land_findings1 else "None")

# 2. Mutate metadata declared_land_acres from 4.5 to 2.0 (triggering discrepancy with deed 4.5)
meta["declared_land_acres"] = 2.0
(test_dir / "application_metadata.json").write_text(json.dumps(meta, indent=2))

req = urllib.request.Request(f"{BASE_URL}/api/v1/evaluate/SYN-MUTATION-TEST", data=b"", method="POST")
with urllib.request.urlopen(req) as resp:
    res2 = json.loads(resp.read().decode())
    land_findings2 = [f for f in res2["findings"] if "LAND" in f["finding_id"]]
    print("Mutated Land Finding:", land_findings2[0]["outcome"] if land_findings2 else "None")
    print("Mutated Discrepancy:", land_findings2[0]["evidence"].get("discrepancy_magnitude") if land_findings2 else "None")

# Cleanup
shutil.rmtree(test_dir)
print("Isolated mutation test complete and cleaned up successfully.")
