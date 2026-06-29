#!/usr/bin/env python3
"""Multi-model gym pipeline for the last 2 months: clean movement GIFs.

For each is_workout video from the catalog (last 60 days):
  1. Extract dense frames (every 0.75s) from the SOURCE mp4 — denser than the
     standard pipeline's ~5 frames per video.
  2. Run primary model (Qwen3.5-9B-MLX-4bit on :8081 — already up) on each.
     Returns: exercise_name, form_score, segment notes.
  3. Find the longest contiguous window of form_score >= 6 → that's the
     "clean movement segment". Use its start/end timestamps.
  4. ffmpeg that segment → a clean movement GIF (better quality settings than
     the comparison page: 12fps, 360px wide, palette dither).
  5. If primary model's confidence is low (max form_score < 7 OR all "none"),
     try secondary model (Qwen3.5-27B-4bit) on the same dense frames.
  6. Pick best label across models. Write final JSON manifest.
  7. Email progress every 10 videos.

Output:
  ~/.local/share/gym-2month-pipeline/
    <video_sha8>.gif           — clean movement GIF
    <video_sha8>.json          — labels + scores + which model won
    manifest.json              — index of all outputs
"""

# /// script
# requires-python = ">=3.14"
# dependencies = ["psutil", "openai"]
# ///

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from base64 import b64encode
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _emaillib import send as send_email  # noqa: E402

PROJECT = Path("/Users/kmx/projects/local-vlm-analysis")
VIDEOS_JSON = PROJECT / "data" / "videos"
OUT_DIR = Path.home() / ".local/share/gym-2month-pipeline"
LOOKBACK_DAYS = 60
FRAME_INTERVAL_S = 0.75
PRIMARY_MODEL_ID = "mlx-community/Qwen3.5-9B-MLX-4bit"
PRIMARY_BASE = "http://localhost:8081/v1"
SECONDARY_MODEL_ID = "mlx-community/Qwen3.5-27B-4bit"
SECONDARY_PORT = 8084
SECONDARY_BASE = f"http://127.0.0.1:{SECONDARY_PORT}/v1"
MAX_GIF_BYTES = 2_500_000
EMAIL_BATCH_SIZE = 10

PROMPT = """One workout-video frame. Score the exercise form visible and identify the exercise.
Output ONLY this JSON (no markdown fences):
{
 "form_score": <int 0-10, 0=no exercise visible, 5=fair, 10=peak movement with clear form>,
 "exercise_name": "<specific gym exercise name, or 'rest', or 'transition', or 'none'>",
 "movement_phase": "<setup|eccentric|peak|concentric|rest|transition|other>",
 "form_notes": "<one short sentence>"
}"""


def select_videos() -> list[dict]:
    cutoff = datetime.now() - timedelta(days=LOOKBACK_DAYS)
    items = []
    for jf in VIDEOS_JSON.glob("*.json"):
        if jf.name == "_batch_summary.json":
            continue
        try:
            d = json.loads(jf.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if not d.get("workout_summary", {}).get("is_workout"):
            continue
        src = Path(d.get("source", ""))
        if not src.exists():
            continue
        ca = d.get("meta", {}).get("created_at", "")
        try:
            dt = datetime.strptime(ca, "%Y:%m:%d %H:%M:%S")
        except ValueError:
            continue
        if dt < cutoff:
            continue
        items.append({
            "sha_head": d.get("sha_head", ""),
            "source": src,
            "source_name": src.name,
            "duration_s": d.get("duration_s", 0),
            "created_at": dt,
            "json_path": jf,
            "existing_workout_summary": d.get("workout_summary", {}),
        })
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return items


def extract_dense_frames(source: Path, duration_s: float, out_dir: Path, interval: float = FRAME_INTERVAL_S) -> list[tuple[float, Path]]:
    """ffmpeg-extract one frame per `interval` seconds. Returns [(t, path), ...]."""
    out_dir.mkdir(parents=True, exist_ok=True)
    fps = 1.0 / interval
    pattern = out_dir / "f_%04d.jpg"
    try:
        result = subprocess.run([
            "ffmpeg", "-y", "-i", str(source),
            "-vf", f"fps={fps:.3f},scale=512:-1",
            "-qscale:v", "3",
            str(pattern),
        ], capture_output=True, timeout=120)
        if result.returncode != 0:
            return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    frames = sorted(out_dir.glob("f_*.jpg"))
    return [(i * interval, p) for i, p in enumerate(frames)]


def query(client_url: str, model_id: str, frame_path: Path, prompt: str = PROMPT, timeout: float = 60) -> dict:
    from openai import OpenAI
    client = OpenAI(base_url=client_url, api_key="mlx-vlm", timeout=timeout)
    img_b64 = b64encode(frame_path.read_bytes()).decode("ascii")
    try:
        resp = client.chat.completions.create(
            model=model_id,
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        raw = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        return {"_error": repr(e)}

    cleaned = raw
    for fence in ("```json", "```JSON", "```"):
        if fence in cleaned:
            parts = cleaned.split(fence)
            cleaned = parts[1] if len(parts) >= 2 else cleaned
            cleaned = cleaned.split("```")[0]
    s, e = cleaned.find("{"), cleaned.rfind("}")
    if s >= 0 and e > s:
        try:
            return {**json.loads(cleaned[s:e+1]), "_raw": raw}
        except json.JSONDecodeError:
            pass
    return {"_raw": raw, "_parse_failed": True}


def find_best_segment(scores: list[dict], frame_times: list[float], min_window_s: float = 1.5) -> tuple[float, float, float]:
    """Find longest contiguous window where form_score >= 6. Returns (start, end, avg_score)."""
    if not scores:
        return (0, 0, 0)
    high = [(t, s.get("form_score", 0)) for t, s in zip(frame_times, scores) if isinstance(s.get("form_score"), int)]
    if not high:
        return (0, 0, 0)

    # Greedy: find longest run with score >= 6
    best_start, best_end, best_avg = 0, 0, 0
    run_start, run_scores = None, []
    last_t = None
    for t, score in high:
        if score >= 6:
            if run_start is None:
                run_start = t
                run_scores = []
            run_scores.append(score)
            last_t = t
        else:
            if run_start is not None:
                length = (last_t or run_start) - run_start
                avg = sum(run_scores) / len(run_scores)
                if length >= min_window_s and (length > (best_end - best_start) or (length == (best_end - best_start) and avg > best_avg)):
                    best_start, best_end, best_avg = run_start, last_t, avg
                run_start, run_scores, last_t = None, [], None
    if run_start is not None and run_scores:
        length = (last_t or run_start) - run_start
        avg = sum(run_scores) / len(run_scores)
        if length >= min_window_s and (length > (best_end - best_start) or (length == (best_end - best_start) and avg > best_avg)):
            best_start, best_end, best_avg = run_start, last_t, avg

    # Fallback: if no window meets threshold, use the single highest-scored frame ±1s
    if best_end == best_start:
        max_score = max(high, key=lambda x: x[1])
        best_start = max(0, max_score[0] - 1.0)
        best_end = max_score[0] + 1.0
        best_avg = max_score[1]
    return (best_start, best_end, best_avg)


def make_clean_gif(source: Path, start: float, end: float, out: Path) -> bool:
    """Higher-quality GIF for the final pipeline output."""
    duration = max(0.5, min(8.0, end - start))
    try:
        result = subprocess.run([
            "ffmpeg", "-y", "-ss", f"{start:.2f}", "-i", str(source),
            "-t", f"{duration:.2f}",
            "-vf", "fps=12,scale=360:-1:flags=lanczos,split[s0][s1];[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=4",
            "-loop", "0", str(out),
        ], capture_output=True, timeout=90)
        if result.returncode != 0:
            return False
        return out.exists()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def pick_best_label(primary: list[dict], secondary: list[dict] | None) -> dict:
    """Across both model passes, surface the most-confident exercise name + best segment."""
    def winner(scores):
        valid = [(s.get("form_score", 0), s.get("exercise_name", ""), s.get("form_notes", ""), s.get("movement_phase", "")) for s in scores]
        valid = [v for v in valid if v[1] and v[1].lower() not in ("", "none", "rest", "transition")]
        if not valid:
            return None
        # Pick highest-form-scoring with a real exercise name
        valid.sort(key=lambda x: -x[0])
        return {"score": valid[0][0], "name": valid[0][1], "notes": valid[0][2], "phase": valid[0][3]}

    a = winner(primary)
    b = winner(secondary) if secondary else None
    if a and b:
        return a if a["score"] >= b["score"] else b
    return a or b or {"score": 0, "name": "none", "notes": "", "phase": ""}


def start_secondary_server() -> subprocess.Popen | None:
    cmd = [
        str(Path.home() / ".local/bin/mlx_vlm.server"),
        "--model", SECONDARY_MODEL_ID,
        "--host", "127.0.0.1",
        "--port", str(SECONDARY_PORT),
    ]
    log = OUT_DIR / "secondary-server.log"
    log_fp = open(log, "w")
    return subprocess.Popen(cmd, stdout=log_fp, stderr=subprocess.STDOUT,
                            env={**os.environ, "PATH": f"{Path.home()}/.local/bin:" + os.environ.get('PATH', '')})


def wait_for_server(url: str, timeout: float = 300) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url + "/models", timeout=3) as r:
                if r.status == 200:
                    return True
        except (urllib.error.URLError, socket.timeout, ConnectionRefusedError):
            pass
        time.sleep(2)
    return False


def send_batch_email(processed: list[dict], total: int) -> None:
    """Email a progress digest of the last N processed videos."""
    recent = processed[-EMAIL_BATCH_SIZE:]
    plain = [f"# Gym 2-month pipeline · {len(processed)}/{total} processed", ""]
    html = [
        "<html><body style='font-family:-apple-system,sans-serif;max-width:760px;margin:1rem auto;line-height:1.5'>",
        f"<h1>Gym pipeline · batch update</h1>",
        f"<p style='color:#666'>{len(processed)} of {total} videos processed so far. Last {len(recent)} below.</p>",
    ]
    images: dict[str, bytes] = {}
    for item in recent:
        gif_path = item.get("gif_path")
        if gif_path and Path(gif_path).exists():
            data = Path(gif_path).read_bytes()
            if len(data) < MAX_GIF_BYTES:
                cid = item["sha_head"][:12]
                images[cid] = data
        label = item.get("label", {})
        ex = label.get("name", "?")
        score = label.get("score", 0)
        winner = item.get("winner_model", "primary")
        seg = item.get("segment", (0, 0, 0))
        plain.append(f"- {item['source_name']}  exercise={ex}  score={score}  segment={seg[0]:.1f}-{seg[1]:.1f}s  ({winner})")

        cid_html = item['sha_head'][:12]
        html.append(
            f"<div style='margin:1rem 0;padding:0.75rem;background:#fafafa;border-radius:6px'>"
            f"<div style='display:flex;gap:0.75rem'>"
        )
        if cid_html in images:
            html.append(f"<img src='cid:{cid_html}' style='max-width:280px;border-radius:4px' />")
        html.append(
            f"<div style='flex:1;font-size:13px'>"
            f"<div style='font-weight:bold'>{item['source_name']}</div>"
            f"<div style='color:#7a9'><strong>{ex}</strong> · score {score} · phase {label.get('phase','?')}</div>"
            f"<div style='color:#555;margin-top:0.25rem'><em>{label.get('notes','')}</em></div>"
            f"<div style='color:#888;font-size:11px;margin-top:0.25rem'>"
            f"segment {seg[0]:.1f}–{seg[1]:.1f}s · avg form {seg[2]:.1f} · winner: {winner}</div>"
            f"</div></div></div>"
        )
    html.append("</body></html>")
    ok, info = send_email(
        f"🏋️ gym pipeline · {len(processed)}/{total}",
        "\n".join(plain), "".join(html), inline_images=images,
    )
    print(f"  batch email: {'✓' if ok else '✗'} {info}")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    videos = select_videos()
    print(f"=== {len(videos)} gym videos to process (last {LOOKBACK_DAYS} days) ===")
    if not videos:
        return 1

    # Wait for :8081 (primary) to be available
    if not wait_for_server(PRIMARY_BASE):
        print("FAIL: primary :8081 not available")
        return 1

    # Start secondary in background (for low-confidence retries)
    print(f"=== Starting secondary server on :{SECONDARY_PORT} ({SECONDARY_MODEL_ID}) ===")
    sec_proc = start_secondary_server()
    sec_ready = False
    sec_start_time = time.time()
    # We'll check secondary readiness when we actually need it

    processed: list[dict] = []
    manifest: list[dict] = []
    try:
        for i, video in enumerate(videos, 1):
            print(f"\n[{i}/{len(videos)}] {video['source_name']}  ({video['created_at']:%Y-%m-%d %H:%M}  dur={video['duration_s']:.1f}s)")
            sha = video["sha_head"]
            out_record = OUT_DIR / f"{sha[:16]}.json"
            out_gif = OUT_DIR / f"{sha[:16]}.gif"

            with tempfile.TemporaryDirectory(prefix="gym2m-") as td:
                frames = extract_dense_frames(video["source"], video["duration_s"], Path(td))
                if not frames:
                    print(f"  ✗ frame extraction failed; skipping")
                    continue
                print(f"  extracted {len(frames)} dense frames @ {FRAME_INTERVAL_S}s")

                primary_scores = []
                for t, fp in frames:
                    s = query(PRIMARY_BASE, PRIMARY_MODEL_ID, fp)
                    primary_scores.append(s)
                p_fmax = max((s.get("form_score", 0) for s in primary_scores if isinstance(s.get("form_score"), int)), default=0)
                print(f"  primary done; max form={p_fmax}")

                secondary_scores = None
                if p_fmax < 7:
                    # Low confidence — try secondary
                    if not sec_ready:
                        print(f"  waiting on secondary load ({int(time.time() - sec_start_time)}s elapsed)…")
                        if wait_for_server(SECONDARY_BASE, timeout=300):
                            sec_ready = True
                            print(f"  ✓ secondary up after {int(time.time() - sec_start_time)}s")
                        else:
                            print(f"  ✗ secondary not ready; using primary only")
                    if sec_ready:
                        secondary_scores = []
                        for t, fp in frames:
                            secondary_scores.append(query(SECONDARY_BASE, SECONDARY_MODEL_ID, fp))
                        s_fmax = max((s.get("form_score", 0) for s in secondary_scores if isinstance(s.get("form_score"), int)), default=0)
                        print(f"  secondary done; max form={s_fmax}")

                # Pick best label
                label = pick_best_label(primary_scores, secondary_scores)
                winner_model = "primary"
                if secondary_scores:
                    p_label = pick_best_label(primary_scores, None)
                    if label["score"] > p_label["score"]:
                        winner_model = "secondary"
                print(f"  winner: {label['name']} score={label['score']} ({winner_model})")

                # Find best segment
                frame_times = [t for t, _ in frames]
                use_scores = secondary_scores if winner_model == "secondary" else primary_scores
                seg = find_best_segment(use_scores, frame_times)
                print(f"  best segment: {seg[0]:.1f}s → {seg[1]:.1f}s  avg form={seg[2]:.1f}")

                # Make clean GIF
                gif_ok = make_clean_gif(video["source"], seg[0], seg[1], out_gif)
                gif_size = out_gif.stat().st_size if out_gif.exists() else 0
                print(f"  gif: {'✓' if gif_ok else '✗'}  size={gif_size/1024:.0f}KB")

                record = {
                    "sha_head": sha,
                    "source_name": video["source_name"],
                    "source_path": str(video["source"]),
                    "created_at": video["created_at"].isoformat(),
                    "duration_s": video["duration_s"],
                    "label": label,
                    "segment": seg,
                    "winner_model": winner_model,
                    "frame_count": len(frames),
                    "gif_path": str(out_gif) if gif_ok else None,
                    "primary_scores": primary_scores,
                    "secondary_scores": secondary_scores,
                }
                out_record.write_text(json.dumps(record, indent=2, default=str))
                manifest.append({
                    "sha_head": sha,
                    "source_name": video["source_name"],
                    "created_at": video["created_at"].isoformat(),
                    "label": label,
                    "segment": seg,
                    "winner_model": winner_model,
                    "gif_path": str(out_gif) if gif_ok else None,
                })
                processed.append(record)

                # Email every EMAIL_BATCH_SIZE
                if len(processed) % EMAIL_BATCH_SIZE == 0:
                    send_batch_email(processed, len(videos))

        # Final batch + final manifest
        if processed and (len(processed) % EMAIL_BATCH_SIZE) != 0:
            send_batch_email(processed, len(videos))

        (OUT_DIR / "manifest.json").write_text(json.dumps({
            "total": len(videos),
            "processed": len(processed),
            "videos": manifest,
        }, indent=2, default=str))
        print(f"\n=== Done. {len(processed)}/{len(videos)} processed. Manifest at {OUT_DIR}/manifest.json ===")
    finally:
        if sec_proc:
            try:
                sec_proc.terminate()
                sec_proc.wait(timeout=10)
            except Exception:
                try: sec_proc.kill()
                except: pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
