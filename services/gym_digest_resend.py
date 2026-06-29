#!/usr/bin/env python3
"""Rebuild the gym digest with smaller GIFs and resend.

Reads the cached 27B attraction scores from ~/.local/share/gym-attraction-rescore/
(no model inference needed — already done). Re-encodes each source segment to a
small GIF (~1 MB target: 8fps, 240px wide, 3.5s max, sharper palette). Buckets
by normalized exercise, picks best per bucket, emails one digest.
"""

# /// script
# requires-python = ">=3.14"
# dependencies = []
# ///

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _emaillib import send as send_email  # noqa: E402

CACHE = Path.home() / ".local/share/gym-attraction-rescore"
OUT_GIFS = CACHE / "small_gifs"
OUT_GIFS.mkdir(parents=True, exist_ok=True)

GIF_FPS = 8
GIF_WIDTH = 240
GIF_MAX_DURATION = 3.5
MAX_GIF_BYTES = 1_800_000  # 1.8 MB per GIF; ~20 GIFs × 1.8 MB ≈ 36 MB but
                            # most will be smaller, target avg ~700 KB.


def normalize_exercise(name: str) -> str:
    if not name:
        return "unknown"
    s = re.sub(r"[^\w\s]", " ", name.lower()).strip()
    s = re.sub(r"\s+", " ", s)
    drop = {"barbell", "dumbbell", "cable", "machine", "smith"}
    parts = [w for w in s.split() if w not in drop]
    return " ".join(parts) if parts else s


def reencode_small(source: Path, start: float, end: float, out: Path) -> bool:
    """Re-encode the original segment into a small GIF (~700 KB target)."""
    duration = max(0.5, min(GIF_MAX_DURATION, end - start))
    # Center the trimmed window on the original segment midpoint
    if (end - start) > GIF_MAX_DURATION:
        mid = (start + end) / 2
        start = max(0.0, mid - GIF_MAX_DURATION / 2)
    try:
        r = subprocess.run([
            "ffmpeg", "-y", "-ss", f"{start:.2f}", "-i", str(source),
            "-t", f"{duration:.2f}",
            "-vf", f"fps={GIF_FPS},scale={GIF_WIDTH}:-1:flags=lanczos,"
                   f"split[s0][s1];[s0]palettegen=max_colors=128:stats_mode=diff[p];"
                   f"[s1][p]paletteuse=dither=bayer:bayer_scale=5",
            "-loop", "0", str(out),
        ], capture_output=True, timeout=60)
        return r.returncode == 0 and out.exists()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def main() -> int:
    print(f"=== rebuild digest from {CACHE} ===")
    records = []
    for jf in sorted(CACHE.glob("*.json")):
        if jf.name == "manifest.json":
            continue
        try:
            records.append(json.loads(jf.read_text()))
        except json.JSONDecodeError:
            pass
    print(f"loaded {len(records)} cached attraction records")

    usable = [r for r in records if r.get("attraction")
              and not r["attraction"].get("_error")
              and not r["attraction"].get("_parse_failed")
              and Path(r.get("source_path", "")).exists()]
    print(f"usable: {len(usable)}")

    # Re-encode small GIF for each
    for r in usable:
        sha8 = r["sha_head"][:16]
        out = OUT_GIFS / f"{sha8}.gif"
        if out.exists():
            r["_small_gif"] = str(out)
            continue
        seg = r["segment"]
        if reencode_small(Path(r["source_path"]), seg[0], seg[1], out):
            r["_small_gif"] = str(out)
            sz = out.stat().st_size / 1024
            print(f"  {sha8}  {sz:.0f}KB  {r.get('attraction',{}).get('exercise_name','?')}")
        else:
            print(f"  {sha8}  re-encode FAILED  {r['source_name']}")

    # Bucket by exercise, pick best per bucket (attraction first, form second)
    by_ex: dict[str, list[dict]] = {}
    for r in usable:
        if not r.get("_small_gif"):
            continue
        if Path(r["_small_gif"]).stat().st_size > MAX_GIF_BYTES:
            print(f"  still too big after re-encode: {r['source_name']} "
                  f"({Path(r['_small_gif']).stat().st_size/1024:.0f}KB)")
            continue
        ex = normalize_exercise(r["attraction"].get("exercise_name")
                                or r.get("label", {}).get("name", "unknown"))
        by_ex.setdefault(ex, []).append(r)

    chosen = []
    for ex, items in by_ex.items():
        items.sort(key=lambda r: (
            -(r["attraction"].get("background_men_hottest_score") or -1),
            -(r.get("label", {}).get("score", 0)),
        ))
        w = dict(items[0])
        w["_bucket"] = ex
        chosen.append(w)
    chosen.sort(key=lambda r: -(r["attraction"].get("background_men_hottest_score") or -1))
    print(f"unique exercise buckets: {len(chosen)}")

    # Build email
    images: dict[str, bytes] = {}
    rows = []
    total_email_bytes = 0
    EMAIL_BYTE_BUDGET = 22 * 1024 * 1024  # Gmail caps at ~25 MB total

    for r in chosen:
        data = Path(r["_small_gif"]).read_bytes()
        if total_email_bytes + len(data) > EMAIL_BYTE_BUDGET:
            print(f"  budget hit; truncating at {len(images)} GIFs")
            break
        cid = r["sha_head"][:12]
        images[cid] = data
        total_email_bytes += len(data)
        a = r["attraction"]
        hot = a.get("background_men_hottest_score")
        cnt = a.get("background_men_count", 0)
        notes = a.get("background_men_notes", "") or "(no background men)"
        subj_notes = a.get("primary_subject", "") or ""
        ex_notes = a.get("exercise_notes", "") or ""
        seg = r.get("segment", [0, 0, 0])
        rows.append(
            f"<div style='margin:1.1rem 0;padding:0.85rem;background:#f7f7f8;border-radius:8px'>"
            f"<div style='display:flex;gap:0.85rem;align-items:flex-start;flex-wrap:wrap'>"
            f"<img src='cid:{cid}' style='max-width:240px;border-radius:6px' />"
            f"<div style='flex:1;min-width:240px;font-size:13.5px;line-height:1.5'>"
            f"<div style='font-size:15px;font-weight:600;color:#1a1a1a'>{r['_bucket']}</div>"
            f"<div style='color:#666;font-size:11.5px;margin-top:0.15rem'>"
            f"<code>{r['source_name']}</code> · seg {seg[0]:.1f}–{seg[1]:.1f}s · "
            f"form {r.get('label',{}).get('score','?')}</div>"
            f"<div style='color:#444;margin-top:0.35rem'><em>{ex_notes}</em></div>"
            f"<div style='color:#444;margin-top:0.2rem'><strong>Lifter:</strong> {subj_notes}</div>"
            f"<div style='margin-top:0.5rem;padding-top:0.4rem;border-top:1px solid #e0e0e2'>"
            f"<strong>Background men:</strong> {cnt}"
            f"{f', hottest <strong>{hot}/10</strong>' if hot is not None else ''}"
            f"</div>"
            f"<div style='color:#444;margin-top:0.2rem'><em>{notes}</em></div>"
            f"</div></div></div>"
        )

    print(f"final: {len(images)} GIFs, total {total_email_bytes/1024/1024:.2f}MB")

    html = (
        "<html><body style='font-family:-apple-system,sans-serif;max-width:780px;"
        "margin:1.5rem auto;line-height:1.5;color:#222'>"
        f"<h1 style='margin-bottom:0.25rem'>🏋️ Gym digest · {len(chosen)} unique exercises</h1>"
        f"<p style='color:#666;margin-top:0'>"
        f"{len(records)} workout clips, all scored with Qwen3.5-27B for exercise + background-attraction. "
        f"Showing best clip per exercise type, sorted by background-attraction score."
        f"</p>"
        + "".join(rows)
        + "<p style='color:#888;font-size:11px;margin-top:2rem'>"
        f"Generated {datetime.now():%Y-%m-%d %H:%M}. "
        f"Original GIFs at ~/.local/share/gym-2month-pipeline/ (larger); "
        f"these are re-encoded smaller ({GIF_FPS}fps, {GIF_WIDTH}px, ≤{GIF_MAX_DURATION:.1f}s) for email."
        "</p></body></html>"
    )
    plain = [f"Gym digest · {len(chosen)} unique exercises"]
    for r in chosen:
        a = r["attraction"]
        plain.append(f"- {r['_bucket']}  ({r['source_name']})  "
                     f"hot={a.get('background_men_hottest_score')}  "
                     f"count={a.get('background_men_count',0)}")

    if not images:
        print("no images to send; skipping email")
        return 1

    subj = f"🏋️ gym digest v2 · {len(images)} exercises (27B + small GIFs)"
    ok, info = send_email(subj, "\n".join(plain), html,
                          inline_images=images, image_subtype="gif")
    print(f"email: {'✓' if ok else '✗'} {info}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
