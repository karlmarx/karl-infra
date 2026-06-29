#!/usr/bin/env python3
"""Aesthetic weekly best-of — Sunday morning email of the week's catalog highlights.

For each video catalogued in the last 7 days (by JSON mtime), pick a
representative frame and embed it inline. v1 picks the middle frame; future
versions can call MLX-VLM to actually score for aesthetic quality and pick the
best-scored frames.

If aesthetic_results.json is populated (>=10 entries with scores), prefer
those rankings over the simple mtime-based selection.
"""

# /// script
# requires-python = ">=3.14"
# dependencies = ["psutil"]
# ///

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _emaillib import send as send_email  # noqa: E402

PROJECT = Path("/Users/kmx/projects/local-vlm-analysis")
VIDEOS_JSON = PROJECT / "data" / "videos"
DERIVATIVES = PROJECT / "data" / "derivatives"
AESTHETIC_RESULTS = PROJECT / "aesthetic_results.json"
WEEK = timedelta(days=7)
TARGET_COUNT = 10
THUMB_MAX_BYTES = 250_000


def recent_videos() -> list[dict]:
    cutoff = datetime.now() - WEEK
    items = []
    for jf in VIDEOS_JSON.glob("*.json"):
        if jf.name == "_batch_summary.json":
            continue
        mtime = datetime.fromtimestamp(jf.stat().st_mtime)
        if mtime < cutoff:
            continue
        try:
            data = json.loads(jf.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        items.append({
            "json_path": jf,
            "mtime": mtime,
            "source": data.get("source", ""),
            "sha_head": data.get("sha_head", ""),
            "duration_s": data.get("duration_s", 0),
            "frame_count": data.get("frame_count", 0),
            "created_at": data.get("meta", {}).get("created_at"),
            "is_workout": data.get("workout_summary", {}).get("is_workout", False),
        })
    return items


def aesthetic_ranked() -> list[dict] | None:
    """If aesthetic_results.json has real data, use it. Else None."""
    if not AESTHETIC_RESULTS.exists():
        return None
    try:
        data = json.loads(AESTHETIC_RESULTS.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, list) or len(data) < TARGET_COUNT:
        return None
    return sorted(data, key=lambda r: -r.get("score", 0))[:TARGET_COUNT]


def pick_thumb(sha_head: str, frame_idx: int | None = None) -> bytes | None:
    if not sha_head:
        return None
    deriv = DERIVATIVES / sha_head
    frames = sorted(deriv.glob("frame_*.jpg")) if deriv.is_dir() else []
    if not frames:
        return None
    chosen = frames[frame_idx] if (frame_idx is not None and 0 <= frame_idx < len(frames)) else frames[len(frames) // 2]
    try:
        data = chosen.read_bytes()
    except OSError:
        return None
    if len(data) > THUMB_MAX_BYTES:
        return None
    return data


def render(items: list[dict], using_aesthetic: bool, images: dict[str, bytes]) -> tuple[str, str]:
    today = datetime.now().date()
    week_start = today - timedelta(days=6)
    header = "Aesthetic best of the week" if using_aesthetic else "Highlights of the week"

    plain = [f"# {header}", f"_{week_start:%b %-d} — {today:%b %-d, %Y}_", ""]
    html = [
        "<html><body style='font-family:-apple-system,BlinkMacSystemFont,sans-serif;"
        "max-width:680px;margin:1.5rem auto;line-height:1.5'>",
        f"<h1 style='color:#444'>{header}</h1>",
        f"<p style='color:#888;font-size:13px'>{week_start:%b %-d} — {today:%b %-d, %Y}</p>",
    ]

    if not items:
        msg = "No new videos catalogued this week."
        plain.append(msg)
        html.append(f"<p style='color:#888;font-style:italic'>{msg}</p>")
    else:
        for i, item in enumerate(items, 1):
            src_name = Path(item.get("source", "")).name or "(unknown)"
            duration = f"{item.get('duration_s', 0):.1f}s"
            tags = " 💪" if item.get("is_workout") else ""
            created = item.get("created_at", "")
            plain.append(f"{i:>2}. {src_name} · {created} · {duration}{tags}")

            cid = item.get("sha_head", "")[:12]
            if cid in images:
                html.append(
                    f"<div style='margin:1.5rem 0'>"
                    f"<div style='font-size:14px;color:#888'>#{i}</div>"
                    f"<img src='cid:{cid}' style='max-width:100%;border-radius:6px;margin-top:0.25rem' />"
                    f"<div style='font-size:13px;color:#555;margin-top:0.5rem'>"
                    f"<strong>{src_name}</strong>{tags}<br/>"
                    f"{created} · {duration}"
                    f"</div></div>"
                )

    plain.extend(["", "—", "Browse full gallery: https://hot.93.fyi/"])
    html.append(
        "<p style='color:#888;font-size:12px;margin-top:2rem;border-top:1px solid #eee;padding-top:1rem'>"
        "Full gallery: <a href='https://hot.93.fyi/'>hot.93.fyi</a><br/>"
        + ("Source: aesthetic_results.json (scored)" if using_aesthetic else
           "Source: most-recently-catalogued (no aesthetic ranking yet)")
        + "</p></body></html>"
    )
    return "\n".join(plain), "".join(html)


def main() -> int:
    ranked = aesthetic_ranked()
    if ranked:
        items = [
            {
                "source": r.get("video", ""),
                "sha_head": (Path(r.get("video", "")).stem if r.get("video") else ""),
                "duration_s": 0,
                "is_workout": False,
                "created_at": r.get("desc", ""),
            }
            for r in ranked
        ]
        using_aesthetic = True
    else:
        items = recent_videos()
        items.sort(key=lambda x: x["mtime"], reverse=True)
        items = items[:TARGET_COUNT]
        using_aesthetic = False

    images: dict[str, bytes] = {}
    for it in items:
        sha = it.get("sha_head", "")
        if not sha:
            continue
        data = pick_thumb(sha)
        if data:
            images[sha[:12]] = data

    plain, html = render(items, using_aesthetic, images)
    week_label = datetime.now().strftime("%b %-d")
    subject = f"✨ Weekly best-of · {week_label} · {len(items)} highlights"
    ok, info = send_email(subject, plain, html, inline_images=images or None)
    print(f"[{datetime.now():%H:%M:%S}] aesthetic-weekly: {len(items)} items, {len(images)} embedded")
    print(f"  email: {'✓' if ok else '✗'} {info}")
    print(f"  source: {'aesthetic_results.json' if using_aesthetic else 'recent-catalog fallback'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
