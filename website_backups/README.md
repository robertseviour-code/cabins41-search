# Cabins41 approved website backups

Keep **only the three most recent approved, complete website ZIP packages** in this directory. These are publication-ready Netlify packages, not GitHub search reports.

## Procedure for each approved update

1. Build the complete website ZIP from the latest approved website files (never from an older package unless expressly authorised).
2. Check that `index.html` and all intended linked pages and assets are present; verify that the ZIP opens and is not corrupt.
3. Run `python website_backups/retain_three.py /path/to/approved.zip` from a checked-out copy of this repository.
4. Commit and push the ZIP, updated `manifest.json`, and deletions of the oldest backup. Check GitHub has received them **before** telling the owner the backup is secure.
5. Upload the exact same approved ZIP to Netlify, or use a separately approved automated deployment process.

The utility does not itself upload anything to GitHub, and **there are no approved ZIP backups in this folder yet**. The first backup must be the actual latest approved website ZIP, not the older 29 October package. Do not treat the GitHub search code or public website as a substitute for a saved publication ZIP.
