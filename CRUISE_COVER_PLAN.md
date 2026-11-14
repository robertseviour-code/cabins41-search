# Cabins41 unattended cruise cover — development plan (14 November 2026)

**Status: safe staging only. No public website deployment is configured or authorised.**

## Verified current architecture
- The GitHub Actions workflow runs daily at 02:30 UTC and checks out `codex/strict-solo-sailing-dedupe` even though the workflow YAML is on `main`. It saves source results and uploads a GitHub artifact.
- The scanner explicitly calls its results research leads, not independently verified fares. Its notification job removes some of these warnings when posting to GitHub issue #1. This is a publication-integrity risk; preserve the warnings in future notifications.
- The repository README explicitly says the search controller is independent of the public website and Netlify. No Netlify deployment credentials, site ID or deployment action are established by the inspected workflow.
- The current schedule is 02:30 **UTC**, not necessarily 02:30 UK local time during summer; in December UK time equals UTC.

## Development delivered
`publication_gate.py` is a standalone fail-closed review stage. It reads a **separate, explicitly approved** JSON file and rejects scanner-only candidates, past departures, duplicate ship/date combinations, old verification, malformed seller URLs, and invalid solo fares. It produces a review JSON report and **never deploys**.
`test_publication_gate.py` covers the key rejection cases.

## Required before unattended publishing
1. Obtain the canonical complete Netlify website source (including assets) and establish its source of truth and backup method.
2. Establish a scoped Netlify deployment credential or verified Git-connected deploy pipeline. Never put tokens in source files; use GitHub Actions secrets and a protected environment.
3. Build a deterministic homepage renderer that updates only the offers section, preserves all other pages and assets, and archives the previous deployment.
4. Add tests for HTML structure, duplicate removal, expiry removal, zero approved new offers, rollback, and prevention of wholesale deletion on bad input.
5. Test against a private preview URL for at least three consecutive daily runs; inspect desktop/mobile rendering. Require explicit approval before enabling live deployments.
6. Add failure alerts and keep last known-good site online on any exception.

**Recommended fallback for 11–16 December:** leave the existing site live, let searches and reports continue, and defer unverified new listings. A stable site is preferable to automated false offers.
