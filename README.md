# Cabins41 Search Controller — initial working prototype

This repository checks the 85 websites in `sources.json`, one at a time, with 20-second gaps, and saves a dated JSON ledger after each source. GitHub Actions commits each result so interrupted runs can resume. Run manually from **Actions → Cabins41 daily source check → Run workflow**.

**Important limitation:** This is a first-stage keyword scanner, not a complete solo cruise deal search. It checks the publicly accessible page at each source's registered URL for solo-cruise phrases. It cannot navigate booking engines, authenticate to Facebook, search all subpages, or establish dated sailings and advertised fares. A successful source check does not mean its solo offers were exhaustively searched. Do not use keyword matches as homepage offers.

The schedule targets 02:30 Europe/London, using 01:30 and 02:30 UTC triggers with a London-hour gate. GitHub scheduled workflows may start late. Each failed source is recorded and can be retried in a later run; a saved `checked` source is skipped on reruns for the same date. The initial controller is not guaranteed to finish 85 checks; inspect Actions logs and the dated ledger. The code and repository are independent of the public Cabins41 website. No Netlify site is required to run this prototype.

## Setup

1. Upload the **contents** of this ZIP (not the ZIP itself) to the root of the empty GitHub repository. Include the hidden `.github` folder.
2. In repository **Settings → Actions → General → Workflow permissions**, allow **Read and write permissions** for GitHub Actions if not already selected.
3. Open **Actions** and run the workflow manually. Check that dated results appear in `data/`.
4. Inspect failed entries and keyword snippets before developing the next stage of actual offer extraction.
