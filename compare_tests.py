import json, os
from pathlib import Path
p=Path("data/test-history"); p.mkdir(parents=True,exist_ok=True)
report=Path("data/latest-test-report.md")
s=report.read_text()
def number(label):
 import re
 m=re.search(label+r":\*\* (\d+)",s)
 return int(m.group(1)) if m else 0
current={"run":os.getenv("GITHUB_RUN_ID","unknown"),"attempted":number("Sources freshly attempted"),"checked":number("Checked"),"blocked":number("blocked"),"failed":number("other failures"),"potential":number(r"Potential solo sailings \(unverified\)"),"criteria_version":2}
previous_files=sorted(p.glob("*.json"))
previous=json.loads(previous_files[-1].read_text()) if previous_files else None
# Read the active main-source count; Problem Sources are stored separately. Allow one blocked and one other failed source.
expected=len(json.loads(Path("sources.json").read_text(encoding="utf-8")))
passed=(current["attempted"]==expected and current["checked"]>=expected-2 and current["failed"]<=1 and current["blocked"]<=1 and "**Search exit code:** 0" in s)
current["passed"]=passed
streak=0
for file in reversed(previous_files):
 record=json.loads(file.read_text())
 if record.get("criteria_version") != current["criteria_version"] or not record.get("passed"):break
 streak+=1
current["streak"]=streak+1 if passed else 0
current["reliability_test_complete"] = current["streak"] >= 3
lines=["## Comparison and reliability",f"Operational baseline passed: {'YES' if passed else 'NO'}",f"Consecutive baseline passes: {current['streak']}/3",f"Three-run reliability test complete: {'YES' if current['reliability_test_complete'] else 'NO'}"]
if previous:
 lines.append("Changes from previous run:")
 for key in ("attempted","checked","blocked","failed","potential"):
  lines.append(f"- {key}: {current[key]} (previous {previous[key]}, change {current[key]-previous[key]:+d})")
else:lines.append("First snapshot; comparison begins next test.")
lines.append(f"Baseline uses {expected} main sources; Problem Sources are excluded. It allows at most one blocked source and one other source failure. This does not verify offer accuracy.")
report.write_text(s+"\n"+"\n".join(lines)+"\n")
(p/(current["run"]+".json")).write_text(json.dumps(current,indent=2))
