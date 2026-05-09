#!/usr/bin/env python3
"""
gantt_historical.py — Generate a Gantt HTML from cached handoff CSV.
Usage:
  python3 gantt_historical.py --from 2026-05-01 --to 2026-05-08
  python3 gantt_historical.py  # defaults to full date range in data
Output: gantt_historical.html (next to this script's parent dir)
"""
import argparse, csv, os, sys
from collections import defaultdict
from datetime import datetime, timedelta

CSV_DEFAULT = "/tmp/handoff_clean.csv"
OUT_DEFAULT = os.path.join(os.path.dirname(__file__), "..", "gantt_historical.html")

# Match app palette exactly
BATCH_COLORS = ["#EFD9A3", "#E8A9A0", "#9FC9C3", "#C8B6D9", "#B2C9A8", "#E6C494", "#D9A8B2"]

# ── Data loading ──────────────────────────────────────────────────────────────

def load_events(csv_path: str, date_from: datetime, date_to: datetime) -> list[dict]:
    """Stream CSV, return only rows whose start_iso falls in [date_from, date_to+1day)."""
    events = []
    cutoff = date_to + timedelta(days=1)
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                dt = datetime.fromisoformat(row["start_iso"])
            except ValueError:
                continue
            if date_from <= dt < cutoff:
                row["_dt"] = dt
                row["_index"] = int(row["index"]) if row["index"].strip().lstrip("-").isdigit() else 0
                events.append(row)
    return events


def load_batches_from_csv(csv_path: str) -> dict[str, str]:
    """Return {id_hanger → load_date_iso} from ALL load events (needed to assign batches)."""
    hanger_load_date = {}
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["action"] == "load":
                try:
                    dt = datetime.fromisoformat(row["start_iso"])
                    hanger_load_date[row["id_hanger"]] = dt.date().isoformat()
                except ValueError:
                    pass
    return hanger_load_date


# ── Batch timeline computation ────────────────────────────────────────────────

def compute_batches(events: list[dict], hanger_load_date: dict[str, str]) -> list[dict]:
    """
    Group events by load_date (batch). For each batch compute:
      load_start, prime_start, prime_end, backup_start, backup_end, is_complete, hanger_count
    """
    # First, enrich each event with its load_date
    for ev in events:
        ev["_load_date"] = hanger_load_date.get(ev["id_hanger"], "unknown")

    # Group by load_date
    by_date = defaultdict(list)
    for ev in events:
        by_date[ev["_load_date"]].append(ev)

    batches = []
    for load_date, evs in sorted(by_date.items()):
        load_evs    = [e for e in evs if e["action"] == "load"]
        prime_picks = [e for e in evs if e["action"] == "robot_pick_start" and e["conveyor"] == "Prime"]
        back_picks  = [e for e in evs if e["action"] == "robot_pick_start" and e["conveyor"] == "Backup"]
        unload_evs  = [e for e in evs if e["action"] == "unload"]
        all_times   = [e["_dt"] for e in evs]

        if not load_evs and not prime_picks and not back_picks:
            continue

        load_start   = min((e["_dt"] for e in load_evs), default=None)
        prime_start  = min((e["_dt"] for e in prime_picks), default=None)
        prime_end    = max((e["_dt"] for e in prime_picks), default=None)
        backup_start = min((e["_dt"] for e in back_picks), default=None)
        backup_end   = max((e["_dt"] for e in back_picks), default=None)
        last_unload  = max((e["_dt"] for e in unload_evs), default=None)
        last_any     = max(all_times) if all_times else None
        hangers      = len({e["id_hanger"] for e in evs})

        batches.append({
            "load_date":   load_date,
            "load_start":  load_start,
            "prime_start": prime_start,
            "prime_end":   prime_end,
            "backup_start": backup_start,
            "backup_end":  backup_end,
            "last_unload": last_unload,
            "last_any":    last_any,
            "is_complete": last_unload is not None,
            "hanger_count": hangers,
        })

    return batches


# ── HTML generation ───────────────────────────────────────────────────────────

def dt_to_px(dt: datetime, t_start: datetime, total_minutes: float, width_px: int) -> float:
    delta = (dt - t_start).total_seconds() / 60
    return max(0.0, delta / total_minutes * width_px)


def fmt(dt: datetime | None) -> str:
    return dt.strftime("%d/%m %H:%M") if dt else "—"


def duration_str(a: datetime | None, b: datetime | None) -> str:
    if not a or not b:
        return ""
    mins = int((b - a).total_seconds() / 60)
    h, m = divmod(mins, 60)
    return f"{h}h{m:02d}m"


def generate_html(batches: list[dict], date_from: datetime, date_to: datetime, out_path: str):
    WIDTH = 1400          # px for the timeline area
    ROW_H = 44            # px per batch row
    LABEL_W = 160         # px for left label
    HEADER_H = 56         # px for day headers

    t_start = date_from
    t_end   = date_to + timedelta(days=1)
    total_min = (t_end - t_start).total_seconds() / 60

    def px(dt):
        return dt_to_px(dt, t_start, total_min, WIDTH) if dt else None

    # Day gridlines
    days = []
    d = t_start
    while d < t_end:
        days.append(d)
        d += timedelta(days=1)

    # Build rows HTML
    rows_html = ""
    for i, b in enumerate(batches):
        color = BATCH_COLORS[i % len(BATCH_COLORS)]
        label_icon = "✓" if b["is_complete"] else "⏳"
        label_txt  = f"{b['load_date'][5:]}  {b['hanger_count']}מ׳  {label_icon}"

        # Bars
        bars = ""

        # 1. Load-wait bar (gray)
        if b["load_start"] and b["prime_start"]:
            x1 = px(b["load_start"])
            x2 = px(b["prime_start"])
            w  = max(x2 - x1, 1)
            t_lw = f"Load wait: {fmt(b['load_start'])} → {fmt(b['prime_start'])} ({duration_str(b['load_start'],b['prime_start'])})"
            bars += f'<div class="bar load-bar" style="left:{x1:.1f}px;width:{w:.1f}px" title="{t_lw}"></div>'

        # 2. Prime bar
        if b["prime_start"] and b["prime_end"]:
            x1 = px(b["prime_start"])
            x2 = px(b["prime_end"])
            w  = max(x2 - x1, 2)
            t_p = f"Prime: {fmt(b['prime_start'])} → {fmt(b['prime_end'])} ({duration_str(b['prime_start'],b['prime_end'])})"
            bars += f'<div class="bar prime-bar" style="left:{x1:.1f}px;width:{w:.1f}px;background:{color}" title="{t_p}"><span>P</span></div>'

        # 3. Backup bar
        if b["backup_start"]:
            x1  = px(b["backup_start"])
            end = b["last_unload"] or b["backup_end"] or b["last_any"]
            # Guard: end must be >= backup_start
            if end and b["backup_start"] and end < b["backup_start"]:
                end = b["backup_end"] or b["last_any"]
            x2  = px(end) if (end and end >= b["backup_start"]) else WIDTH
            w   = max(x2 - x1, 2)
            dashed = "" if b["is_complete"] else "border-right:2px dashed #888;"
            t_b = f"Backup: {fmt(b['backup_start'])} → {fmt(end)} ({duration_str(b['backup_start'],end)})"
            bars += f'<div class="bar backup-bar" style="left:{x1:.1f}px;width:{w:.1f}px;background:{color};opacity:0.65;{dashed}" title="{t_b}"><span>B</span></div>'

        rows_html += f"""
        <div class="gantt-row">
          <div class="row-label">
            <span class="dot" style="background:{color}"></span>
            {label_txt}
          </div>
          <div class="row-bars">{bars}</div>
        </div>"""

    # Day header
    header_cells = ""
    for d in days:
        x = px(d)
        label = d.strftime("%-d/%m %a")
        header_cells += f'<div class="day-label" style="left:{x:.1f}px">{label}</div>'

    # Hour gridlines
    gridlines = ""
    h = t_start
    while h <= t_end:
        x = px(h)
        cls = "day-line" if h.hour == 0 else "hour-line"
        gridlines += f'<div class="{cls}" style="left:{x:.1f}px"></div>'
        h += timedelta(hours=1)

    title = f"Gantt היסטורי — {date_from.strftime('%-d/%m/%Y')} עד {date_to.strftime('%-d/%m/%Y')}"

    html = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, sans-serif; background: #1a1a2e; color: #e0e0e0; }}
  h1 {{ padding: 16px 20px 8px; font-size: 1rem; font-weight: 600; color: #c8d6e5; letter-spacing:.04em; }}
  .gantt-wrap {{ overflow-x: auto; padding-bottom: 24px; }}
  .gantt-inner {{ position: relative; min-width: {WIDTH + LABEL_W}px; }}
  .gantt-header {{ position: relative; height: {HEADER_H}px; margin-right: 0; padding-left: {LABEL_W}px; border-bottom: 1px solid #333; }}
  .day-label {{ position: absolute; top: 28px; font-size: .72rem; color: #888; padding-left: 4px; white-space: nowrap; }}
  .gantt-row {{ display: flex; align-items: center; height: {ROW_H}px; border-bottom: 1px solid #222; }}
  .gantt-row:hover {{ background: rgba(255,255,255,.03); }}
  .row-label {{
    flex: 0 0 {LABEL_W}px; width: {LABEL_W}px;
    display: flex; align-items: center; gap: 6px;
    font-size: .72rem; color: #aaa; padding: 0 8px;
    white-space: nowrap; overflow: hidden;
    position: sticky; left: 0; background: #1a1a2e; z-index: 2;
    border-right: 1px solid #333;
  }}
  .dot {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}
  .row-bars {{ position: relative; flex: 1; height: 100%; overflow: hidden; }}
  .bar {{
    position: absolute; height: 22px; top: 11px;
    border-radius: 3px; cursor: default;
    display: flex; align-items: center; justify-content: center;
    overflow: hidden;
  }}
  .bar span {{ font-size: .6rem; font-weight: 700; color: rgba(0,0,0,.55); pointer-events: none; }}
  .load-bar {{ background: #444; opacity: .4; }}
  .prime-bar {{ opacity: 1; }}
  .backup-bar {{ }}
  .day-line {{ position: absolute; top: 0; bottom: 0; width: 1px; background: #383838; pointer-events: none; }}
  .hour-line {{ position: absolute; top: 0; bottom: 0; width: 1px; background: #252525; pointer-events: none; }}
  .legend {{ display: flex; gap: 20px; padding: 8px 20px; font-size: .72rem; color: #888; }}
  .legend-item {{ display: flex; align-items: center; gap: 6px; }}
  .legend-swatch {{ width: 24px; height: 10px; border-radius: 2px; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="legend">
  <div class="legend-item"><div class="legend-swatch" style="background:#444;opacity:.5"></div> המתנה טעינה</div>
  <div class="legend-item"><div class="legend-swatch" style="background:#9FC9C3"></div> P — פריים (טבילות ראשוניות)</div>
  <div class="legend-item"><div class="legend-swatch" style="background:#9FC9C3;opacity:.65"></div> B — בקאפ (טבילות המשך)</div>
  <div class="legend-item">⏳ = עדיין בתהליך</div>
</div>
<div class="gantt-wrap">
  <div class="gantt-inner">
    <div class="gantt-header" style="width:{WIDTH + LABEL_W}px">
      <div style="position:absolute;left:{LABEL_W}px;right:0;top:0;bottom:0;overflow:hidden">
        {gridlines}
        {header_cells}
      </div>
    </div>
    {rows_html}
  </div>
</div>
</body>
</html>"""

    with open(out_path, "w") as f:
        f.write(html)
    print(f"Wrote {out_path}", file=sys.stderr)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--from", dest="date_from", default="2026-05-01")
    p.add_argument("--to",   dest="date_to",   default="2026-05-08")
    p.add_argument("--csv",  default=CSV_DEFAULT)
    p.add_argument("--out",  default=OUT_DEFAULT)
    args = p.parse_args()

    date_from = datetime.fromisoformat(args.date_from)
    date_to   = datetime.fromisoformat(args.date_to)

    if not os.path.exists(args.csv):
        print(f"CSV not found: {args.csv}\nRun parse_handoff.py first.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading events {args.date_from} → {args.date_to} ...", file=sys.stderr)

    # Load ALL load events (to assign batch identity across full dataset)
    hanger_load_date = load_batches_from_csv(args.csv)

    # Load events visible in the requested window
    # Also include events for hangers whose load date is within ±5 days of window
    # (they may be mid-process during our window)
    wide_from = date_from - timedelta(days=7)
    wide_to   = date_to   + timedelta(days=2)
    events = load_events(args.csv, wide_from, wide_to)

    # Keep only hangers whose load_date falls within [date_from-7, date_to]
    window_load_dates = {
        hid for hid, ld in hanger_load_date.items()
        if (date_from - timedelta(days=7)).date().isoformat() <= ld <= date_to.date().isoformat()
    }
    events = [e for e in events if e["id_hanger"] in window_load_dates]

    batches = compute_batches(events, hanger_load_date)
    print(f"Found {len(batches)} batches", file=sys.stderr)
    for b in batches:
        status = "✓" if b["is_complete"] else "⏳"
        print(f"  {b['load_date']}  {b['hanger_count']:>3}מ׳  {status}  "
              f"prime={fmt(b['prime_start'])}→{fmt(b['prime_end'])}  "
              f"backup={fmt(b['backup_start'])}→{fmt(b['last_unload'] or b['backup_end'])}", file=sys.stderr)

    generate_html(batches, date_from, date_to, args.out)


def fmt(dt):
    return dt.strftime("%d/%m %H:%M") if dt else "—"


if __name__ == "__main__":
    main()
