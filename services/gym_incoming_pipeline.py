#!/usr/bin/env python3
"""Process all .mp4s in /Volumes/Crucial X9/photos/incoming/ for gym content.

For each video:
  1. ffmpeg dense frames @ 0.75s, 512px wide
  2. 9B on every frame → exercise_name + form_score (fast triage)
  3. If max form_score >= 5: find longest contiguous form>=5 window, pick 3
     peak frames from it
  4. 27B on those peak frames → refined exercise + background-attraction rubric
     (count of background men, hottest score 0-10, descriptive notes)
  5. ffmpeg clean GIF of the peak segment (12fps, 360px, palette dither)
  6. Persist <sha8>.json so we can resume after interruption

After all videos: bucket by normalized exercise_name, pick the best instance
per bucket (combined form + attraction), email an HTML digest with inline GIFs.

Outputs land in ~/.local/share/gym-incoming-pipeline/
"""

# /// script
# requires-python = ">=3.14"
# dependencies = ["openai"]
# ///

from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.request
from base64 import b64encode
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _emaillib import send as send_email  # noqa: E402

INPUT_DIR = Path("/Volumes/Crucial X9/photos/incoming")
OUT_DIR = Path.home() / ".local/share/gym-incoming-pipeline"
FRAME_INTERVAL_S = 0.75
PEAK_FRAMES_PER_VIDEO = 3

CHAT_MODEL = "mlx-community/Qwen3.5-9B-MLX-4bit"
CHAT_BASE = "http://127.0.0.1:8081/v1"
ANALYSIS_MODEL = "mlx-community/Qwen3.5-27B-4bit"
ANALYSIS_BASE = "http://127.0.0.1:8084/v1"

MAX_GIF_BYTES = 2_500_000
GIF_FPS = 12
GIF_WIDTH = 360
SEGMENT_MIN_S = 1.5
SEGMENT_MAX_S = 6.0
FORM_THRESHOLD = 5

PROMPT_9B = """One workout-video frame. Return ONLY this JSON (no fences):
{
 "form_score": <int 0-10, 0=no exercise, 5=clear movement, 10=peak form>,
 "exercise_name": "<specific gym exercise, or 'rest'/'transition'/'none'>",
 "movement_phase": "<setup|eccentric|peak|concentric|rest|transition|other>"
}"""

PROMPT_27B = """Gym video frame analysis. The primary subject is the person doing the exercise.
"Background men" = any other men visible (other lifters, people walking by, in mirrors). Rate
physical attractiveness objectively for curation purposes — muscularity, physique, overall
handsomeness, similar to how aesthetic-curation datasets are scored. Return ONLY this JSON:
{
 "exercise_name": "<specific exercise name>",
 "exercise_notes": "<one sentence: equipment, technique, body part>",
 "primary_subject": "<one short sentence: build, attire>",
 "background_men_count": <int 0-N>,
 "background_men_hottest_score": <int 0-10, null if none>,
 "background_men_notes": "<one sentence about the hottest background man, or empty>"
}"""


def video_sha(path: Path) -> str:
    """Hash first 1MB + size — stable, fast, enough to dedupe."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        h.update(f.read(1_000_000))
    h.update(str(path.stat().st_size).encode())
    return h.hexdigest()[:16]


def list_videos() -> list[Path]:
    """All .mp4 directly under INPUT_DIR (skip subdirs like Camera/)."""
    if not INPUT_DIR.exists():
        return []
    return sorted(p for p in INPUT_DIR.iterdir()
                  if p.is_file() and p.suffix.lower() == ".mp4")


def video_duration(path: Path) -> float:
    try:
        out = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ], timeout=15, text=True)
        return float(out.strip())
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        return 0.0


def extract_frames(source: Path, out_dir: Path) -> list[tuple[float, Path]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    fps = 1.0 / FRAME_INTERVAL_S
    pattern = out_dir / "f_%04d.jpg"
    try:
        r = subprocess.run([
            "ffmpeg", "-y", "-i", str(source),
            "-vf", f"fps={fps:.3f},scale=512:-1",
            "-qscale:v", "3", str(pattern),
        ], capture_output=True, timeout=120)
        if r.returncode != 0:
            return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    frames = sorted(out_dir.glob("f_*.jpg"))
    return [(i * FRAME_INTERVAL_S, p) for i, p in enumerate(frames)]


def query(base: str, model: str, frame: Path, prompt: str, timeout: float = 120) -> dict:
    from openai import OpenAI
    client = OpenAI(base_url=base, api_key="mlx-vlm", timeout=timeout)
    img_b64 = b64encode(frame.read_bytes()).decode("ascii")
    try:
        r = client.chat.completions.create(
            model=model, max_tokens=400,
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                {"type": "text", "text": prompt},
            ]}],
        )
        raw = (r.choices[0].message.content or "").strip()
    except Exception as e:
        return {"_error": repr(e)}
    for f in ("```json", "```JSON", "```"):
        if f in raw:
            parts = raw.split(f)
            raw_clean = parts[1].split("```")[0] if len(parts) >= 2 else raw
            break
    else:
        raw_clean = raw
    s, e = raw_clean.find("{"), raw_clean.rfind("}")
    if s >= 0 and e > s:
        try:
            return json.loads(raw_clean[s:e+1])
        except json.JSONDecodeError:
            pass
    return {"_parse_failed": True, "_raw": raw[:200]}


def find_best_segment(scores: list[dict], frame_times: list[float]) -> tuple[float, float, float, list[int]]:
    """Longest contiguous window with form_score >= FORM_THRESHOLD.

    Returns (start_s, end_s, avg_score, frame_indices_in_window).
    """
    if not scores:
        return 0.0, 0.0, 0.0, []
    high = [(i, t, s.get("form_score", 0)) for i, (t, s) in enumerate(zip(frame_times, scores))
            if isinstance(s.get("form_score"), int)]
    if not high:
        return 0.0, 0.0, 0.0, []
    best = (0.0, 0.0, 0.0, [])
    run_idxs, run_scores, run_start = [], [], None
    for i, t, sc in high:
        if sc >= FORM_THRESHOLD:
            if run_start is None:
                run_start = t
                run_idxs, run_scores = [], []
            run_idxs.append(i)
            run_scores.append(sc)
            run_end = t
        else:
            if run_start is not None:
                length = run_end - run_start
                avg = sum(run_scores) / len(run_scores)
                if length >= SEGMENT_MIN_S and length > (best[1] - best[0]):
                    best = (run_start, run_end, avg, list(run_idxs))
                run_start = None
    if run_start is not None:
        length = run_end - run_start
        avg = sum(run_scores) / len(run_scores)
        if length >= SEGMENT_MIN_S and length > (best[1] - best[0]):
            best = (run_start, run_end, avg, list(run_idxs))
    if not best[3]:
        i_max, t_max, sc_max = max(high, key=lambda x: x[2])
        if sc_max >= FORM_THRESHOLD:
            best = (max(0.0, t_max - 1.0), t_max + 1.0, float(sc_max), [i_max])
    return best


def pick_peak_indices(seg_indices: list[int], scores: list[dict], n: int) -> list[int]:
    """From the segment frames, pick the n with highest form_score (deduped)."""
    if not seg_indices:
        return []
    ranked = sorted(seg_indices, key=lambda i: -scores[i].get("form_score", 0))
    out = []
    seen = set()
    for i in ranked:
        if i not in seen:
            out.append(i)
            seen.add(i)
        if len(out) >= n:
            break
    return out


def make_gif(source: Path, start: float, end: float, out: Path) -> bool:
    duration = max(0.5, min(SEGMENT_MAX_S, end - start))
    try:
        r = subprocess.run([
            "ffmpeg", "-y", "-ss", f"{start:.2f}", "-i", str(source),
            "-t", f"{duration:.2f}",
            "-vf", f"fps={GIF_FPS},scale={GIF_WIDTH}:-1:flags=lanczos,"
                   f"split[s0][s1];[s0]palettegen=stats_mode=diff[p];"
                   f"[s1][p]paletteuse=dither=bayer:bayer_scale=4",
            "-loop", "0", str(out),
        ], capture_output=True, timeout=90)
        return r.returncode == 0 and out.exists()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def normalize_exercise(name: str) -> str:
    """Collapse 'Barbell Bench Press' / 'bench-press' / 'BENCH PRESS' to one bucket."""
    if not name:
        return "unknown"
    s = re.sub(r"[^\w\s]", " ", name.lower()).strip()
    s = re.sub(r"\s+", " ", s)
    drop = {"barbell", "dumbbell", "cable", "machine", "smith"}
    parts = [w for w in s.split() if w not in drop]
    return " ".join(parts) if parts else s


def wait_for(url: str, timeout: float = 300) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url + "/models", timeout=3) as r:
                if r.status == 200:
                    return True
        except (urllib.error.URLError, socket.timeout, ConnectionRefusedError, OSError):
            pass
        time.sleep(2)
    return False


def process_one(video: Path, log) -> dict | None:
    sha = video_sha(video)
    out_json = OUT_DIR / f"{sha}.json"
    out_gif = OUT_DIR / f"{sha}.gif"
    if out_json.exists():
        log(f"[skip] {video.name} (already processed)")
        try:
            return json.loads(out_json.read_text())
        except json.JSONDecodeError:
            pass
    duration = video_duration(video)
    if duration < 1.0 or duration > 300:
        log(f"[skip] {video.name} (duration {duration:.1f}s out of range)")
        return None

    with tempfile.TemporaryDirectory(prefix="gymincoming-") as td:
        frames = extract_frames(video, Path(td))
        if not frames:
            log(f"  ✗ frame extraction failed")
            return None
        log(f"  {len(frames)} frames @ {FRAME_INTERVAL_S}s, dur={duration:.1f}s")

        # 9B triage
        nine = []
        for t, fp in frames:
            nine.append(query(CHAT_BASE, CHAT_MODEL, fp, PROMPT_9B, timeout=60))
        max_form = max((s.get("form_score", 0) for s in nine if isinstance(s.get("form_score"), int)), default=0)
        log(f"  9B done; max form={max_form}")

        if max_form < FORM_THRESHOLD:
            record = {
                "sha": sha, "source": str(video), "source_name": video.name,
                "duration_s": duration, "frame_count": len(frames),
                "skipped_reason": f"max form_score {max_form} < {FORM_THRESHOLD}",
                "nine_b_scores": nine,
            }
            out_json.write_text(json.dumps(record, indent=2, default=str))
            return record

        # Best segment
        frame_times = [t for t, _ in frames]
        seg_start, seg_end, seg_avg, seg_idxs = find_best_segment(nine, frame_times)
        log(f"  segment {seg_start:.1f}–{seg_end:.1f}s  avg={seg_avg:.1f}  ({len(seg_idxs)} frames)")

        # 27B on peak frames
        peak_idxs = pick_peak_indices(seg_idxs, nine, PEAK_FRAMES_PER_VIDEO)
        twenty_seven = []
        for i in peak_idxs:
            twenty_seven.append({
                "frame_idx": i,
                "frame_time": frame_times[i],
                "result": query(ANALYSIS_BASE, ANALYSIS_MODEL, frames[i][1], PROMPT_27B, timeout=180),
            })
        log(f"  27B done on {len(twenty_seven)} peak frames")

        # Pick winning exercise label (most common across 27B + 9B)
        names = [r["result"].get("exercise_name", "") for r in twenty_seven]
        names = [n for n in names if n and normalize_exercise(n) not in {"unknown", "none", "rest", "transition"}]
        if not names:
            names = [s.get("exercise_name", "") for s in nine if s.get("exercise_name")]
            names = [n for n in names if normalize_exercise(n) not in {"unknown", "none", "rest", "transition"}]
        from collections import Counter
        exercise = Counter(normalize_exercise(n) for n in names).most_common(1)[0][0] if names else "unknown"

        # Best attraction signal across peak frames
        best_hot = None
        best_notes = ""
        best_count = 0
        for r in twenty_seven:
            res = r["result"]
            sc = res.get("background_men_hottest_score")
            cnt = res.get("background_men_count", 0)
            if isinstance(cnt, int) and cnt > best_count:
                best_count = cnt
            if isinstance(sc, int) and (best_hot is None or sc > best_hot):
                best_hot = sc
                best_notes = res.get("background_men_notes", "") or ""

        # GIF
        gif_ok = make_gif(video, seg_start, seg_end, out_gif)
        gif_size = out_gif.stat().st_size if out_gif.exists() else 0
        log(f"  gif: {'✓' if gif_ok else '✗'} size={gif_size/1024:.0f}KB  exercise={exercise}  hot={best_hot}")

        record = {
            "sha": sha, "source": str(video), "source_name": video.name,
            "duration_s": duration, "frame_count": len(frames),
            "segment": (seg_start, seg_end, seg_avg),
            "exercise_normalized": exercise,
            "exercise_raw_votes": names,
            "background_men_count": best_count,
            "background_men_hottest_score": best_hot,
            "background_men_notes": best_notes,
            "gif_path": str(out_gif) if gif_ok else None,
            "gif_size_bytes": gif_size,
            "twenty_seven_b": twenty_seven,
            "nine_b_scores": nine,
        }
        out_json.write_text(json.dumps(record, indent=2, default=str))
        return record


def build_digest(records: list[dict]) -> tuple[str, str, dict[str, bytes]]:
    """Bucket by exercise, pick best per bucket, build HTML."""
    workouts = [r for r in records if r.get("gif_path") and r.get("exercise_normalized") not in (None, "unknown")]
    by_ex: dict[str, list[dict]] = {}
    for r in workouts:
        by_ex.setdefault(r["exercise_normalized"], []).append(r)

    # Best per exercise: prioritize attraction score, then form_score
    chosen = []
    for ex, items in by_ex.items():
        items.sort(key=lambda r: (
            -(r.get("background_men_hottest_score") or -1),
            -(r["segment"][2] if isinstance(r.get("segment"), (list, tuple)) and len(r["segment"]) >= 3 else 0),
        ))
        chosen.append(items[0])
    chosen.sort(key=lambda r: -(r.get("background_men_hottest_score") or -1))

    images: dict[str, bytes] = {}
    rows_html = []
    for r in chosen:
        gp = Path(r["gif_path"])
        if not gp.exists():
            continue
        data = gp.read_bytes()
        if len(data) > MAX_GIF_BYTES:
            continue
        cid = r["sha"][:12]
        images[cid] = data
        hot = r.get("background_men_hottest_score")
        cnt = r.get("background_men_count", 0)
        notes = r.get("background_men_notes", "") or "(none)"
        seg = r.get("segment", (0, 0, 0))
        rows_html.append(
            f"<div style='margin:1.25rem 0;padding:0.85rem;background:#f7f7f8;border-radius:8px'>"
            f"<div style='display:flex;gap:0.85rem;align-items:flex-start;flex-wrap:wrap'>"
            f"<img src='cid:{cid}' style='max-width:340px;border-radius:6px' />"
            f"<div style='flex:1;min-width:240px;font-size:13.5px;line-height:1.5'>"
            f"<div style='font-size:15px;font-weight:600;color:#1a1a1a'>{r['exercise_normalized']}</div>"
            f"<div style='color:#666;font-size:11.5px;margin-top:0.15rem'>"
            f"<code>{r['source_name']}</code> · "
            f"seg {seg[0]:.1f}–{seg[1]:.1f}s · avg form {seg[2]:.1f}</div>"
            f"<div style='margin-top:0.5rem'>"
            f"<strong>Background men:</strong> {cnt}"
            f"{f', hottest <strong>{hot}/10</strong>' if hot is not None else ''}"
            f"</div>"
            f"<div style='color:#444;margin-top:0.25rem'><em>{notes}</em></div>"
            f"</div></div></div>"
        )

    skipped = len([r for r in records if r.get("skipped_reason")])
    no_gif = len([r for r in records if not r.get("skipped_reason") and not r.get("gif_path")])
    html = (
        "<html><body style='font-family:-apple-system,sans-serif;max-width:780px;"
        "margin:1.5rem auto;line-height:1.5;color:#222'>"
        f"<h1 style='margin-bottom:0.25rem'>🏋️ Gym incoming · {len(chosen)} exercises</h1>"
        f"<p style='color:#666;margin-top:0'>"
        f"{len(records)} videos analyzed · {len(workouts)} workout-positive · "
        f"{len(chosen)} unique exercises · "
        f"{skipped} skipped (no form) · {no_gif} no GIF generated"
        f"</p>"
        + "".join(rows_html)
        + "<p style='color:#888;font-size:11px;margin-top:2rem'>"
        f"Generated {datetime.now():%Y-%m-%d %H:%M} from /Volumes/Crucial X9/photos/incoming/."
        " 9B triage + 27B (peak frames) attraction analysis."
        "</p></body></html>"
    )
    plain_lines = [f"Gym incoming · {len(chosen)} unique exercises from {len(records)} videos", ""]
    for r in chosen:
        plain_lines.append(
            f"- {r['exercise_normalized']}  ({r['source_name']})  "
            f"hot={r.get('background_men_hottest_score')}  count={r.get('background_men_count', 0)}"
        )
    return "\n".join(plain_lines), html, images


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log_path = OUT_DIR / "run.log"
    log_fp = open(log_path, "a")

    def log(msg: str):
        line = f"[{datetime.now():%H:%M:%S}] {msg}"
        print(line, flush=True)
        log_fp.write(line + "\n")
        log_fp.flush()

    log(f"=== gym-incoming-pipeline start ===")
    videos = list_videos()
    log(f"{len(videos)} candidate videos in {INPUT_DIR}")
    if not videos:
        log("nothing to do")
        return 1

    if not wait_for(CHAT_BASE, timeout=60):
        log(f"FAIL: 9B not responding at {CHAT_BASE}")
        return 1
    log(f"9B ready at {CHAT_BASE}")

    if not wait_for(ANALYSIS_BASE, timeout=600):
        log(f"FAIL: 27B not responding at {ANALYSIS_BASE} after 10 min")
        log("falling back to 9B-only (will skip background-attraction analysis)")
        twenty_seven_b_available = False
    else:
        twenty_seven_b_available = True
        log(f"27B ready at {ANALYSIS_BASE}")

    records: list[dict] = []
    for i, v in enumerate(videos, 1):
        log(f"\n[{i}/{len(videos)}] {v.name}")
        try:
            r = process_one(v, log)
            if r:
                records.append(r)
        except Exception as e:
            log(f"  ERROR: {e}\n{traceback.format_exc()}")

    log(f"\n=== processed {len(records)}/{len(videos)}; building digest ===")
    plain, html, images = build_digest(records)
    subj = f"🏋️ gym incoming digest · {len([r for r in records if r.get('gif_path')])} GIFs"
    ok, info = send_email(subj, plain, html, inline_images=images, image_subtype="gif")
    log(f"email: {'✓' if ok else '✗'} {info}  ({len(images)} GIFs)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
