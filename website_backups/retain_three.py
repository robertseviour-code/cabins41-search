"""Keep only the three most recent approved Cabins41 website ZIP packages.

Usage: python website_backups/retain_three.py /path/to/approved-site.zip

Run this against a checked-out copy of the repository, then commit and push
website_backups/ to GitHub. Only approved packages should be supplied.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.json"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    package = args.package.resolve()
    if not package.is_file() or not zipfile.is_zipfile(package):
        parser.error("Supply a valid ZIP package")
    with zipfile.ZipFile(package) as archive:
        if "index.html" not in archive.namelist():
            parser.error("ZIP must contain index.html at its root")
        if archive.testzip():
            parser.error("ZIP contains a damaged file")
    entries = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else []
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    if any(item["sha256"] == digest for item in entries):
        print("This exact ZIP is already backed up.")
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = HERE / f"Cabins41_approved_{stamp}.zip"
    shutil.copy2(package, destination)
    entries.append({"filename": destination.name, "sha256": digest,
                    "approved_at_utc": stamp})
    for old in entries[:-3]:
        (HERE / old["filename"]).unlink(missing_ok=True)
    MANIFEST.write_text(json.dumps(entries[-3:], indent=2) + "\n")
    print(f"Saved {destination.name}; retained {len(entries[-3:])} approved packages.")

if __name__ == "__main__":
    main()
