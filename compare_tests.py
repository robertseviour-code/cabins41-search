import json, os
from pathlib import Path
p=Path("data/test-history"); p.mkdir(parents=True,exist_ok=True)
report=Path("data/latest-test-report.md")
s=report.read_text()
def number(label):
 import re
 m=re.search(label+r":\*\* (\d+)",s)
 return int(m.group(1)) if m else 0
current={"run":os.getenv("GITHUB_RUN_ID","unknown"),"attempted":number("Sources freshly attempted"),"checked":number("Checked"),"blocked":number("blocked"),"failed":number("other failures"),"potential":number("Potential solo sailings \(unverified\)")}
previous_files=sorted(p.glob("*.json"))
previous=json.loads(previous_files[-1].read_text()) if previous_files else None
# Baseline recognises the 21 known inaccessible sources, without hiding new failures.
passed=(current["attempted"]==85 and current["checked"]>=64 and current["failed"]<=1 and current["blocked"]<=20 and "**Search exit code:** 0" in s)
current["passed"]=passed
streak=0
for file in reversed(previous_files):
 if not json.loads(file.read_text()).get("passed"):break
 streak+=1
current["streak"]=streak+1 if passed else 0
lines=["## Comparison and reliability",f"Operational baseline passed: {'YES' if passed else 'NO'}",f"Consecutive baseline passes: {current['streak']}/8"]
if previous:
 lines.append("Changes from previous run:")
 for key in ("attempted","checked","blocked","failed","potential"):
  lines.append(f"- {key}: {current[key]} (previous {previous[key]}, change {current[key]-previous[key]:+d})")
else:lines.append("First snapshot; comparison begins next test.")
lines.append("Baseline excludes the known 20 blocked sources and one DNS failure. This does not verify offer accuracy.")
report.write_text(s+"\n"+"\n".join(lines)+"\n")
(p/(current["run"]+".json")).write_text(json.dumps(current,indent=2))
