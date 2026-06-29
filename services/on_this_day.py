#!/usr/bin/env python3
"""On This Day — daily email of videos/photos from N years ago today.

Scans the VLM-catalogued archive (data/videos/*.json) for entries whose
EXIF `meta.created_at` falls on today's month-day in years past. Emails
the first frame of each match inline with the source date and any caption
fields the pipeline has produced.

Year-deltas surfaced: 1y, 2y, 3y, 5y, 7y, 10y. Up to 2 per delta.
"""

# /// script
# requires-python = ">=3.14"
# dependencies = ["psutil"]
# ///

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _emaillib import send as send_email  # noqa: E402

PROJECT = Path("/Users/kmx/projects/local-vlm-analysis")
VIDEOS_JSON = PROJECT / "data" / "videos"
DERIVATIVES = PROJECT / "data" / "derivatives"
YEAR_DELTAS = [1, 2, 3, 5, 7, 10]
PER_DELTA_CAP = 2
THUMB_MAX_BYTES = 250_000  # ~250KB ceiling per inline image — Gmail accepts 25MB total


def parse_created_at(raw: str | None) -> datetime | None:
    """EXIF format is 'YYYY:MM:DD HH:MM:SS'."""
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def gather_matches(today: date) -> dict[int, list[dict]]:
    """Group matching videos by year-delta from today."""
    by_delta: dict[int, list[dict]] = {d: [] for d in YEAR_DELTAS}
    for jf in VIDEOS_JSON.glob("*.json"):
        if jf.name == "_batch_summary.json":
            continue
        try:
            data = json.loads(jf.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        ts = parse_created_at(data.get("meta", {}).get("created_at"))
        if not ts:
            continue
        if ts.month != today.month or ts.day != today.day:
            continue
        delta = today.year - ts.year
        if delta not in by_delta:
            continue
        by_delta[delta].append({
            "json_path": jf,
            "source": data.get("source", ""),
            "sha_head": data.get("sha_head", ""),
            "created_at": ts,
            "duration_s": data.get("duration_s", 0),
            "frame_count": data.get("frame_count", 0),
            "lat": data.get("meta", {}).get("lat"),
            "lon": data.get("meta", {}).get("lon"),
            "cluster": data.get("meta", {}).get("cluster"),
            "is_workout": data.get("workout_summary", {}).get("is_workout", False),
        })
    return by_delta


def pick_thumb(sha_head: str) -> bytes | None:
    """Return JPEG bytes of a representative frame, or None if unavailable."""
    if not sha_head:
        return None
    deriv_dir = DERIVATIVES / sha_head
    if not deriv_dir.is_dir():
        return None
    # Prefer a middle frame for content; frame_000000 is often a black opener
    frames = sorted(deriv_dir.glob("frame_*.jpg"))
    if not frames:
        return None
    chosen = frames[len(frames) // 2]
    try:
        data = chosen.read_bytes()
    except OSError:
        return None
    # If the file is too big, skip it (no shrinking dep — keep email lean)
    if len(data) > THUMB_MAX_BYTES:
        return None
    return data


def render_html(matches: dict[int, list[dict]], today: date, images: dict[str, bytes]) -> tuple[str, str]:
    plain_lines = [f"# On this day — {today:%B %-d}", ""]
    html_parts = [
        "<html><body style='font-family:-apple-system,BlinkMacSystemFont,sans-serif;"
        "max-width:680px;margin:1.5rem auto;line-height:1.5;color:#222'>",
        f"<h1 style='color:#444'>On this day — {today:%B %-d}</h1>",
    ]
    any_match = False
    for delta in YEAR_DELTAS:
        items = matches.get(delta, [])
        if not items:
            continue
        any_match = True
        year_label = f"{delta} year{'s' if delta != 1 else ''} ago ({today.year - delta})"
        plain_lines.extend([f"\n## {year_label}", ""])
        html_parts.append(f"<h2 style='color:#666;border-bottom:1px solid #eee'>{year_label}</h2>")
        for m in items[:PER_DELTA_CAP]:
            src_name = Path(m["source"]).name if m["source"] else "(unknown)"
            cluster = m.get("cluster")
            location = f" · {cluster}" if cluster else ""
            tags = " 💪" if m["is_workout"] else ""
            duration = f"{m['duration_s']:.1f}s"
            line = f"- {src_name} · {m['created_at']:%H:%M}{location} · {duration}{tags}"
            plain_lines.append(line)

            cid = m["sha_head"][:12]
            if cid in images:
                html_parts.append(
                    f"<div style='margin:1rem 0;padding:0.5rem;background:#fafafa;"
                    f"border-radius:8px'>"
                    f"<img src='cid:{cid}' style='max-width:100%;border-radius:4px' />"
                    f"<div style='font-size:13px;color:#555;margin-top:0.5rem'>"
                    f"<strong>{src_name}</strong>{tags}<br/>"
                    f"{m['created_at']:%Y-%m-%d %H:%M}{location} · {duration}"
                    f"</div></div>"
                )
            else:
                html_parts.append(
                    f"<div style='margin:0.5rem 0;font-size:13px;color:#666'>"
                    f"<strong>{src_name}</strong>{tags} · "
                    f"{m['created_at']:%H:%M}{location} · {duration}"
                    f"</div>"
                )

    if not any_match:
        plain_lines.append("(no matching videos in catalog)")
        html_parts.append("<p style='color:#888;font-style:italic'>No matching videos in catalog today.</p>")

    plain_lines.extend(["", "—", "From your Crucial X9 catalog · https://hot.93.fyi/"])
    html_parts.append(
        "<p style='color:#888;font-size:12px;margin-top:2rem'>"
        "From your Crucial X9 catalog · "
        "<a href='https://hot.93.fyi/'>hot.93.fyi</a>"
        "</p></body></html>"
    )
    return "\n".join(plain_lines), "".join(html_parts)


def main() -> int:
    today = date.today()
    matches = gather_matches(today)
    total = sum(len(items) for items in matches.values())
    print(f"[{datetime.now():%H:%M:%S}] on-this-day {today:%Y-%m-%d}: {total} match{'es' if total != 1 else ''}")

    if total == 0:
        # Stay quiet on empty days — no email
        print("  (no matches; not sending email)")
        return 0

    images: dict[str, bytes] = {}
    for delta in YEAR_DELTAS:
        for m in matches.get(delta, [])[:PER_DELTA_CAP]:
            data = pick_thumb(m["sha_head"])
            if data:
                images[m["sha_head"][:12]] = data

    plain, html = render_html(matches, today, images)
    subject = f"📷 On this day · {today:%b %-d} · {total} memor{'y' if total == 1 else 'ies'}"
    ok, info = send_email(subject, plain, html, inline_images=images or None)
    print(f"  email: {'✓' if ok else '✗'} {info}")
    print(f"  images embedded: {len(images)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
