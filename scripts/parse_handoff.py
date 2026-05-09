#!/usr/bin/env python3
"""
parse_handoff.py — One-time conversion of raw handoff JSON → clean CSV.
Usage:
  python3 parse_handoff.py --src <raw_json_path> --out <csv_path>
  python3 parse_handoff.py  # uses defaults
Skips conversion if output CSV already exists (use --force to overwrite).
"""
import argparse, csv, io, json, os, re, sys
from datetime import datetime

RAW_DEFAULT = (
    "/root/.claude/projects/-home-user-shellroom/"
    "8cc71d76-dad0-4af4-98cf-67a755ad0b7d/tool-results/"
    "mcp-3e3a7dff-5c53-4b1c-a08f-d2a652b6c4de-read_file_content-1778321474307.txt"
)
CSV_DEFAULT = "/tmp/handoff_clean.csv"

COLUMNS = ["id_hanger", "action", "cabiran", "poid", "start_iso", "minutes", "conveyor", "program", "index", "steps"]


def convert(src: str, out: str) -> int:
    print(f"Reading {src} ...", file=sys.stderr)
    with open(src) as f:
        raw = json.load(f)["fileContent"]

    raw = raw.replace("\\_", "_")
    # Records are space-separated; each starts with a 5-digit number followed by comma
    raw_csv = re.sub(r" (?=\d{5},)", "\n", raw)

    reader = csv.reader(io.StringIO(raw_csv))
    next(reader)  # skip header

    count = 0
    with open(out, "w", newline="") as fout:
        writer = csv.writer(fout)
        writer.writerow(COLUMNS)
        for row in reader:
            if len(row) < 9:
                continue
            try:
                dt = datetime.strptime(row[4].strip(), "%d/%m/%Y %H:%M")
                iso = dt.isoformat()
            except ValueError:
                continue
            try:
                minutes = float(row[5].strip()) if row[5].strip() else ""
            except ValueError:
                minutes = ""
            writer.writerow([
                row[0].strip(),   # id_hanger
                row[1].strip(),   # action
                row[2].strip(),   # cabiran
                row[3].strip(),   # poid
                iso,              # start_iso (ISO 8601)
                minutes,          # minutes
                row[6].strip(),   # conveyor
                row[7].strip(),   # program
                row[8].strip(),   # index
                row[9].strip() if len(row) > 9 else "",  # steps
            ])
            count += 1

    print(f"Wrote {count:,} rows → {out}", file=sys.stderr)
    return count


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--src", default=RAW_DEFAULT)
    p.add_argument("--out", default=CSV_DEFAULT)
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    if os.path.exists(args.out) and not args.force:
        print(f"Cache exists: {args.out}  (use --force to rebuild)", file=sys.stderr)
        return

    convert(args.src, args.out)


if __name__ == "__main__":
    main()
