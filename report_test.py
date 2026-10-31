#!/usr/bin/env python3
"""Produce a per-run Cabins41 test report from actual source results."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import urllib.request

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--since", required=True, help="UTC ISO start time for this run")
    p.add_argument("--expected", type=int, default=None)
    p.add_argument("--search-exit", type=int, default=0)
    p.add_argument("--output", default="data/latest-test-report.md")
    args = p.parse_args()
    if args.expected is None:
        args.expected = len(json.loads(Path("sources.json").read_text(encoding="utf-8")))
    since = dt.datetime.fromisoformat(args.since.replace("Z", "+00:00"))
    now = dt.datetime.now(dt.timezone.utc)
    today = dt.datetime.now(dt.timezone(dt.timedelta(0))).date().isoformat()
    holding = Path(f"data/holding-{today}.json")
    if not holding.exists():
        files = sorted(Path("data").glob("holding-*.json"), reverse=True)
        holding = files[0] if files else holding
    raw = json.loads(holding.read_text()) if holding.exists() else {}
    results = raw.get("results", {})
    fresh = {}
    for k, v in results.items():
        stamp = v.get("checked_at")
        try:
            if stamp and dt.datetime.fromisoformat(stamp.replace("Z", "+00:00")) >= since:
                fresh[k] = v
        except ValueError:
            pass
    checked = [v for v in fresh.values() if v.get("status") == "checked"]
    blocked = [v for v in fresh.values() if v.get("status") == "blocked"]
    failed = [v for v in fresh.values() if v.get("status") not in ("checked", "blocked")]
    offers = [o for v in fresh.values() for o in v.get("possible_offers", [])]
    dedup = {}
    for o in offers:
        if isinstance(o, dict):
            key = (str(o.get("ship", "")).lower(), str(o.get("departure_date", "")))
            dedup.setdefault(key, o)
    lines = [
        "# Cabins41 — test report",
        f"Run: {since.isoformat()} to {now.isoformat()}",
        f"GitHub: {os.getenv('GITHUB_SERVER_URL', 'https://github.com')}/{os.getenv('GITHUB_REPOSITORY', 'robertseviour-code/cabins41-search')}/actions/runs/{os.getenv('GITHUB_RUN_ID', '')}",
        f"**Search exit code:** {args.search_exit}",
        f"**Sources freshly attempted:** {len(fresh)} of {args.expected}",
        f"**Checked:** {len(checked)}; **blocked:** {len(blocked)}; **other failures:** {len(failed)}",
        f"**Potential solo sailings (unverified):** {len(dedup)}; **verified fares:** 0 (not independently checked)",
        "",
        "## Blocked and failed sources",
    ]
    for v in blocked + failed:
        lines.append(f"- {v.get('source_name', 'Unknown')}: {v.get('status')} — {v.get('error', 'No error detail')}")
    if not blocked and not failed:
        lines.append("None recorded.")
    lines.extend(["", "## Potential offers requiring manual checking"])
    for o in list(dedup.values())[:50]:
        lines.append(f"- {o.get('ship', 'Unknown ship')} | {o.get('departure_date', 'Date unconfirmed')} | {o.get('source_name', '')} | {o.get('seller_url', '')} | solo evidence: {o.get('solo_evidence', 'not recorded')}")
    if not dedup:
        lines.append("No potential offers detected in this run.")
    lines.extend(["", "## Assessment"])
    if args.search_exit or len(fresh) != args.expected or len(blocked) > 1 or len(failed) > 1:
        lines.append("INCOMPLETE / DEGRADED: investigate missing checks, run errors, or more than one blocked/failed main source.")
    else:
        lines.append("All expected main sources were accounted for within the operational baseline. Offer quality still requires manual verification.")
    lines.append("No offers have been approved for publication by this report.")
    report = "\n".join(lines) + "\n"
    # Optional AI commentary. It must never hide the factual report or invent verified fares.
    if os.getenv("OPENAI_API_KEY"):
        payload = json.dumps({"model": os.getenv("CABINS41_REPORT_MODEL", "gpt-4.1-mini"),
          "input": [{"role": "system", "content": "You are a critical QA analyst for Cabins41. Analyse the supplied factual test report. Explain recurring failure patterns, likely root causes, and concrete next debugging steps. Never claim unverified offers are verified or invent facts. Be concise."},
                    {"role": "user", "content": report}]}).encode()
        try:
            req = urllib.request.Request("https://api.openai.com/v1/responses", data=payload,
                headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"], "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=45) as response:
                result = json.load(response)
            commentary = "\n".join(part.get("text", "") for item in result.get("output", [])
                                   for part in item.get("content", []) if part.get("type") == "output_text")
            if commentary:
                report += "\n## AI assessment\n" + commentary + "\n"
        except Exception as exc:
            report += f"\nAI assessment unavailable: {type(exc).__name__}\n"
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(report, encoding="utf-8")
    print(report)
    # Email using an optional Resend API key. No credentials or report body are logged.
    if os.getenv("RESEND_API_KEY") and os.getenv("CABINS41_FROM_EMAIL"):
        payload = json.dumps({"from": os.environ["CABINS41_FROM_EMAIL"],
                              "to": ["robertseviour@gmail.com"],
                              "subject": f"Cabins41 test: {len(fresh)}/{args.expected} sources, {len(blocked)+len(failed)} errors",
                              "text": report}).encode()
        req = urllib.request.Request("https://api.resend.com/emails", data=payload,
            headers={"Authorization": "Bearer " + os.environ["RESEND_API_KEY"], "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                print("Email accepted by sending service:", response.status)
        except Exception as exc:
            print("Email sending failed:", type(exc).__name__)

if __name__ == "__main__":
    main()
