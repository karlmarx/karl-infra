#!/usr/bin/env python3
"""Gym multi-model frame discovery + GIF generation (v2).

What v1 got wrong: it fed every model the same 10 fixed frames, so "frame
selection" was identical by construction. This version makes frame
selection the variable.

Design:
  1. Build a CORPUS of ~60 frames across the most-recent workout videos.
  2. For each model: send every corpus frame through one multi-task prompt
     that returns scores for (form, aesthetic, background-admirers).
  3. Rank the corpus by each task's score independently — different tasks
     surface different frames within the same model.
  4. For the form task, take the top frame per video, find its `t`
     timestamp in the source video, ffmpeg out a ~3s GIF around it.
  5. Email per model: top-5 form (with GIFs), top-5 aesthetic, top-5
     background-admirers, all inline. Different models surface different
     frames because they score the same corpus differently.
"""

# /// script
# requires-python = ">=3.14"
# dependencies = ["psutil", "openai", "huggingface_hub"]
# ///

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from base64 import b64encode
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _emaillib import send as send_email  # noqa: E402

PROJECT = Path("/Users/kmx/projects/local-vlm-analysis")
VIDEOS_JSON = PROJECT / "data" / "videos"
DERIVATIVES = PROJECT / "data" / "derivatives"
EXPERIMENT_DIR = Path.home() / ".local/share/gym-model-compare-v2"
PORT = 8083
# Use ALL is_workout videos and ALL their extracted frames — no downsampling.
# Quality > speed; each model gets the full pool and surfaces its own picks.
VIDEOS_FOR_CORPUS = 999
FRAMES_PER_VIDEO_MAX = 999
TOP_N_PER_TASK = 10
THUMB_MAX_BYTES = 250_000
GIF_MAX_BYTES = 1_500_000  # was 800k — too restrictive; ffmpeg makes ~300-800KB GIFs at the tighter settings below

# Verified latest as of 2026-05-16 via mlx-community HF search
MODELS = [
    ("gemma-4-e2b-it-4bit",            "mlx-community/gemma-4-e2b-it-4bit"),
    ("Qwen3-VL-4B-Instruct-4bit",      "mlx-community/Qwen3-VL-4B-Instruct-4bit"),
    ("MiniCPM-V-4_6-4bit",             "mlx-community/MiniCPM-V-4_6-4bit"),
    ("Qwen3-VL-8B-Instruct-4bit",      "mlx-community/Qwen3-VL-8B-Instruct-4bit"),
    ("Qwen3.5-9B-MLX-4bit",            "mlx-community/Qwen3.5-9B-MLX-4bit"),
    ("gemma-3-12b-it-4bit",            "mlx-community/gemma-3-12b-it-4bit"),
    ("gemma-3-27b-it-4bit",            "mlx-community/gemma-3-27b-it-4bit"),
    ("gemma-4-31b-it-4bit",            "mlx-community/gemma-4-31b-it-4bit"),
    ("Qwen3-VL-30B-A3B-Instruct-4bit", "mlx-community/Qwen3-VL-30B-A3B-Instruct-4bit"),
    ("Qwen3.5-27B-4bit",               "mlx-community/Qwen3.5-27B-4bit"),
]

SKIP_IF_SCORED = True  # reuse existing scores; just regen GIFs + re-email

MULTI_TASK_PROMPT = """Analyze this single frame from a workout/gym video. Score it on THREE independent criteria and output ONE JSON object (no commentary, no markdown fences):

1. form_score (0-10): if a recognizable strength or cardio exercise is being performed with visible form, score 5-10 (higher = clearer form, better camera angle, peak movement). If no exercise or it's a rest/transition shot, score 0-3.

2. aesthetic_score (0-10): visual appeal of the main subject in the frame. Consider composition, lighting, and visibility of muscle definition. Note specifically any bulging or well-defined muscle groups (biceps, triceps, lats, delts, chest, glutes, quads, calves).

3. background_admirer_score (0-10): are OTHER people visible in the BACKGROUND (besides the main subject), and do any appear to be looking toward / paying attention to the main subject? 0 = no one else or they're absorbed in their own thing. 5-7 = others present, gaze ambiguous. 8-10 = clearly looking at the subject.

Output exactly this JSON shape:
{
 "form_score": <int 0-10>,
 "exercise_name": "<specific name or 'none'>",
 "form_notes": "<one short sentence>",
 "aesthetic_score": <int 0-10>,
 "muscles_visible": ["<...>", "<...>"],
 "aesthetic_notes": "<one short sentence>",
 "background_admirer_score": <int 0-10>,
 "others_count": <int>,
 "admirer_notes": "<one short sentence>",
 "extras": "<optional, open-ended: anything else worth surfacing about this frame — outfit, lighting, hair, expression, equipment used, funny background detail, suggested camera angle next time, anything you think the viewer would want to know that's NOT covered by the three scores above. Leave empty string if nothing stands out.>"
}"""


@dataclass
class FrameEntry:
    sha_head: str
    source_path: Path
    source_name: str
    duration_s: float
    frame_count: int
    frame_i: int
    frame_t: float
    frame_path: Path
    created_at: datetime
    cid: str  # email content-id


def select_corpus() -> list[FrameEntry]:
    """Pick ~60 frames across the most-recent workout videos."""
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
        sha_head = d.get("sha_head", "")
        src = Path(d.get("source", ""))
        if not src.exists():
            continue
        frames_list = d.get("frames", [])
        if not frames_list:
            continue
        ca = d.get("meta", {}).get("created_at", "")
        try:
            dt = datetime.strptime(ca, "%Y:%m:%d %H:%M:%S")
        except ValueError:
            dt = datetime.min
        items.append({
            "sha_head": sha_head,
            "source": src,
            "duration_s": d.get("duration_s", 0),
            "frame_count": d.get("frame_count", 0),
            "frames": frames_list,
            "created_at": dt,
        })
    items.sort(key=lambda x: x["created_at"], reverse=True)
    items = items[:VIDEOS_FOR_CORPUS]

    corpus = []
    for video in items:
        frames = video["frames"]
        n = len(frames)
        if n <= FRAMES_PER_VIDEO_MAX:
            picks = frames
        else:
            # Evenly-spaced sample
            step = n / FRAMES_PER_VIDEO_MAX
            picks = [frames[int(i * step)] for i in range(FRAMES_PER_VIDEO_MAX)]
        for f in picks:
            frame_path = PROJECT / f["path"]
            if not frame_path.exists():
                continue
            corpus.append(FrameEntry(
                sha_head=video["sha_head"],
                source_path=video["source"],
                source_name=video["source"].name,
                duration_s=video["duration_s"],
                frame_count=video["frame_count"],
                frame_i=f.get("i", 0),
                frame_t=f.get("t", 0.0),
                frame_path=frame_path,
                created_at=video["created_at"],
                cid=f"{video['sha_head'][:8]}_i{f.get('i', 0):03d}",
            ))
    return corpus


def ensure_downloaded(model_id: str) -> Path | None:
    """Download model if not in HF cache. Returns the local snapshot path or None on failure."""
    try:
        from huggingface_hub import snapshot_download
        path = snapshot_download(model_id, local_files_only=False)
        return Path(path)
    except Exception as e:
        print(f"  download failed for {model_id}: {e!r}")
        return None


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def wait_for_server(port: int, timeout: float = 240) -> bool:
    start = time.time()
    url = f"http://127.0.0.1:{port}/v1/models"
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status == 200:
                    return True
        except (urllib.error.URLError, socket.timeout, ConnectionRefusedError):
            pass
        time.sleep(2)
    return False


def start_server(model_id: str, port: int, log_path: Path) -> subprocess.Popen:
    cmd = [
        str(Path.home() / ".local/bin/mlx_vlm.server"),
        "--model", model_id,
        "--host", "127.0.0.1",
        "--port", str(port),
    ]
    log_fp = open(log_path, "w")
    proc = subprocess.Popen(
        cmd, stdout=log_fp, stderr=subprocess.STDOUT,
        env={**os.environ, "PATH": f"{Path.home()}/.local/bin:" + os.environ.get("PATH", "")},
    )
    return proc


def stop_server(proc: subprocess.Popen) -> None:
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=15)
    except (subprocess.TimeoutExpired, ProcessLookupError):
        try:
            proc.kill()
            proc.wait(timeout=5)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            pass


def query_frame(model_id: str, port: int, frame_path: Path, prompt: str, timeout: float = 90) -> dict | None:
    """One inference per frame. Returns parsed dict (best-effort) or None on hard failure."""
    from openai import OpenAI
    client = OpenAI(base_url=f"http://127.0.0.1:{port}/v1", api_key="mlx-vlm", timeout=timeout)
    img_b64 = b64encode(frame_path.read_bytes()).decode("ascii")
    try:
        resp = client.chat.completions.create(
            model=model_id,
            max_tokens=600,
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
        return {"_error": repr(e), "_raw": ""}

    # Best-effort JSON extraction
    cleaned = raw
    for fence in ("```json", "```JSON", "```"):
        if fence in cleaned:
            parts = cleaned.split(fence)
            cleaned = parts[1] if len(parts) >= 2 else cleaned
            cleaned = cleaned.split("```")[0]
    s, e = cleaned.find("{"), cleaned.rfind("}")
    if s >= 0 and e > s:
        try:
            parsed = json.loads(cleaned[s:e+1])
            parsed["_raw"] = raw
            return parsed
        except json.JSONDecodeError:
            pass
    # Fallback: extract integer scores via regex
    import re
    parsed = {"_raw": raw, "_parse_failed": True}
    for key in ("form_score", "aesthetic_score", "background_admirer_score"):
        m = re.search(rf'"?{key}"?\s*[:=]\s*(\d+)', raw)
        if m:
            parsed[key] = int(m.group(1))
    return parsed


def make_gif(source: Path, t_center: float, duration_s: float, out: Path) -> bool:
    """Encode a small ~2.5s GIF centered on t_center.

    Tighter ffmpeg settings than v1: 6fps, 280px wide, palette dithering for
    smaller output. Target ~300-700KB per GIF so 20-25 GIFs fit in one email
    under Gmail's 25MB limit.
    """
    start = max(0.0, t_center - 1.25)
    duration = min(2.5, max(0.5, duration_s - start))
    try:
        result = subprocess.run([
            "ffmpeg", "-y", "-ss", f"{start:.2f}", "-i", str(source),
            "-t", f"{duration:.2f}",
            "-vf", "fps=6,scale=280:-1:flags=lanczos,split[s0][s1];[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5",
            "-loop", "0", str(out),
        ], capture_output=True, timeout=60)
        if result.returncode != 0:
            return False
        if not out.exists():
            return False
        # Don't reject big ones here — let caller decide whether to embed.
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def top_n_by(scores: dict[str, dict], key: str, n: int) -> list[tuple[str, dict]]:
    """Return [(frame_id, parsed)] sorted by score descending."""
    valid = [(fid, p) for fid, p in scores.items() if isinstance(p.get(key), int)]
    valid.sort(key=lambda x: -x[1].get(key, 0))
    return valid[:n]


def render_email(
    model_name: str,
    elapsed_s: float,
    corpus: list[FrameEntry],
    scores: dict[str, dict],
    images: dict[str, bytes],
    gifs: dict[str, bytes],
) -> tuple[str, str]:
    """Per-model email with the model's own top-5 per task."""
    by_id = {f.cid: f for f in corpus}
    plain = [
        f"# Model: {model_name}",
        f"Corpus: {len(corpus)} frames across {len({f.sha_head for f in corpus})} videos · {elapsed_s:.0f}s",
        "",
    ]
    html = [
        "<html><body style='font-family:-apple-system,sans-serif;max-width:720px;margin:1rem auto;line-height:1.5'>",
        f"<h1 style='margin-bottom:0.25rem'>{model_name}</h1>",
        f"<p style='color:#888;font-size:13px;margin-top:0'>"
        f"Corpus: {len(corpus)} frames · {len({f.sha_head for f in corpus})} videos · {elapsed_s:.0f}s</p>",
    ]

    sections = [
        ("form_score",               "🏋️ Top form/exercise picks", "form_notes", "exercise_name"),
        ("aesthetic_score",          "💪 Top aesthetic/muscle picks", "aesthetic_notes", "muscles_visible"),
        ("background_admirer_score", "👀 Top background-admirer picks", "admirer_notes", "others_count"),
    ]

    for score_key, title, notes_key, extra_key in sections:
        plain.append(f"\n## {title}\n")
        html.append(f"<h2 style='border-bottom:1px solid #eee;color:#444'>{title}</h2>")
        top = top_n_by(scores, score_key, TOP_N_PER_TASK)
        if not top:
            plain.append("  (no scored frames)")
            html.append("<p style='color:#999;font-style:italic'>No scored frames.</p>")
            continue
        for rank, (fid, parsed) in enumerate(top, 1):
            f = by_id.get(fid)
            if not f:
                continue
            score = parsed.get(score_key, 0)
            notes = parsed.get(notes_key, "")
            extra = parsed.get(extra_key, "")
            plain.append(f"  {rank}. score={score:2d}  {f.source_name}  t={f.frame_t:.1f}s")
            plain.append(f"     notes: {notes}")
            if extra:
                plain.append(f"     {extra_key}: {extra}")
            plain.append("")

            html.append(
                f"<div style='margin:1rem 0;padding:0.75rem;background:#fafafa;border-radius:6px;display:flex;gap:0.75rem'>"
                f"<div style='font-size:32px;font-weight:bold;color:#666;min-width:2rem'>{score}</div>"
                f"<div style='flex:1'>"
            )
            # Prefer the animated GIF (any task), fall back to still thumbnail.
            gif_cid = f"{fid}_gif"
            if gif_cid in gifs:
                html.append(f"<img src='cid:{gif_cid}' style='max-width:320px;border-radius:4px;display:block;margin-bottom:0.5rem' />")
            elif fid in images:
                html.append(f"<img src='cid:{fid}' style='max-width:320px;border-radius:4px;display:block;margin-bottom:0.5rem' />")
            html.append(
                f"<div style='font-size:13px;color:#555'>"
                f"<strong>#{rank} · {f.source_name}</strong> · t={f.frame_t:.1f}s<br/>"
                f"<em style='color:#777'>{notes}</em>"
            )
            if extra:
                if isinstance(extra, list):
                    html.append(f"<br/><span style='color:#888'>{extra_key}: {', '.join(map(str, extra))}</span>")
                else:
                    html.append(f"<br/><span style='color:#888'>{extra_key}: {extra}</span>")
            # Model's open-ended "extras" — anything the model wanted to flag
            extras_text = parsed.get("extras", "").strip() if isinstance(parsed.get("extras"), str) else ""
            if extras_text and extras_text.lower() not in ("none", "n/a", "nothing", ""):
                html.append(
                    f"<br/><span style='color:#6a8c5f;font-size:12px'>"
                    f"<strong>💭 model noticed:</strong> {extras_text}</span>"
                )
                plain.append(f"     model noticed: {extras_text}")
            html.append("</div></div></div>")

    html.append("</body></html>")
    return "\n".join(plain), "".join(html)


def main() -> int:
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Building corpus ===")
    corpus = select_corpus()
    print(f"  {len(corpus)} frames from {len({f.sha_head for f in corpus})} videos")
    if not corpus:
        print("FAIL: no corpus")
        return 1

    # Pre-load thumbnails (small) — shared across all model emails
    thumb_cache: dict[str, bytes] = {}
    for f in corpus:
        try:
            data = f.frame_path.read_bytes()
            if len(data) < THUMB_MAX_BYTES:
                thumb_cache[f.cid] = data
        except OSError:
            pass

    all_results: dict[str, dict] = {}
    for model_name, model_id in MODELS:
        print(f"\n=== {model_name} ===")
        t_model = time.time()
        results_file = EXPERIMENT_DIR / f"{model_name}-scores.json"

        # Skip re-scoring if we already have scores on disk
        if SKIP_IF_SCORED and results_file.exists():
            try:
                cached = json.loads(results_file.read_text())
                scores = cached.get("scores", {})
                if len(scores) >= len(corpus) * 0.8:  # at least 80% coverage
                    print(f"  ↻ reusing cached scores ({len(scores)}/{len(corpus)} frames) — skipping re-inference")
                else:
                    raise ValueError("incomplete coverage")
            except Exception:
                scores = None
        else:
            scores = None

        if scores is None:
            print(f"  ensuring download…")
            path = ensure_downloaded(model_id)
            if not path:
                print(f"  ✗ skipping (download failed)")
                continue

            log_path = EXPERIMENT_DIR / f"{model_name}-server.log"
            proc = start_server(model_id, PORT, log_path)
            try:
                if not wait_for_server(PORT, timeout=300):
                    print(f"  ✗ server didn't come up (see {log_path})")
                    continue
                print(f"  ✓ server up ({time.time() - t_model:.0f}s load)")

                scores = {}
                for i, f in enumerate(corpus):
                    t0 = time.time()
                    parsed = query_frame(model_id, PORT, f.frame_path, MULTI_TASK_PROMPT)
                    el = time.time() - t0
                    scores[f.cid] = parsed or {"_error": "no_response"}
                    fs = parsed.get("form_score", "-") if parsed else "-"
                    ae = parsed.get("aesthetic_score", "-") if parsed else "-"
                    ba = parsed.get("background_admirer_score", "-") if parsed else "-"
                    print(f"    [{i+1:2}/{len(corpus)}] {el:5.1f}s  form={fs} aes={ae} bg={ba}  {f.source_name[:32]}")

                results_file.write_text(json.dumps({
                    "model": model_name,
                    "elapsed_s": time.time() - t_model,
                    "scores": scores,
                }, indent=2))
            finally:
                stop_server(proc)
                print(f"  server stopped, total {time.time() - t_model:.0f}s")

        # Generate GIFs for the top-N picks of EVERY task (form, aesthetic, admirers)
        # — animated clips help judge form, muscle motion, and gaze direction.
        print(f"  generating GIFs for top picks across all 3 tasks…")
        gif_cache: dict[str, bytes] = {}
        by_id = {f.cid: f for f in corpus}
        gif_fids_needed: set[str] = set()
        for score_key in ("form_score", "aesthetic_score", "background_admirer_score"):
            for fid, _ in top_n_by(scores, score_key, TOP_N_PER_TASK):
                gif_fids_needed.add(fid)
        print(f"    {len(gif_fids_needed)} unique frames need GIFs (across 3 tasks)")
        for fid in gif_fids_needed:
            f = by_id.get(fid)
            if not f:
                continue
            gif_out = EXPERIMENT_DIR / f"{model_name}_{fid}.gif"
            if gif_out.exists() and gif_out.stat().st_size < GIF_MAX_BYTES:
                pass  # already generated, reuse
            else:
                make_gif(f.source_path, f.frame_t, f.duration_s, gif_out)
            try:
                data = gif_out.read_bytes()
                if len(data) < GIF_MAX_BYTES:
                    gif_cache[f"{fid}_gif"] = data
            except OSError:
                pass

        # Email
        plain, html = render_email(model_name, time.time() - t_model, corpus, scores, thumb_cache, gif_cache)
        subject = f"🏋️ {model_name} — top picks across 3 tasks"
        ok, info = send_email(
            subject, plain, html,
            inline_images={**thumb_cache, **gif_cache},
        )
        print(f"  email: {'✓' if ok else '✗'} {info}")
        all_results[model_name] = scores

    # Cross-model summary: side-by-side anchor frame + each model's top form pick
    print(f"\n=== Sending cross-model summary ===")
    summary_html = [
        "<html><body style='font-family:-apple-system,sans-serif;max-width:760px;margin:1rem auto'>",
        "<h1>Cross-model summary</h1>",
        f"<p style='color:#666'>{len(MODELS)} models tested on {len(corpus)}-frame corpus.</p>",
    ]
    for score_key, title in [
        ("form_score", "🏋️ Each model's #1 form pick"),
        ("aesthetic_score", "💪 Each model's #1 aesthetic pick"),
        ("background_admirer_score", "👀 Each model's #1 admirer pick"),
    ]:
        summary_html.append(f"<h2 style='border-bottom:1px solid #eee'>{title}</h2>")
        for model_name, _ in MODELS:
            scores = all_results.get(model_name, {})
            top = top_n_by(scores, score_key, 1)
            if not top:
                summary_html.append(f"<p><strong>{model_name}</strong>: <em>no result</em></p>")
                continue
            fid, parsed = top[0]
            f = {x.cid: x for x in corpus}.get(fid)
            cid_to_show = f"{fid}_gif" if score_key == "form_score" and f"{fid}_gif" in {**thumb_cache} else fid
            score = parsed.get(score_key, 0)
            note_key = {"form_score": "form_notes", "aesthetic_score": "aesthetic_notes", "background_admirer_score": "admirer_notes"}[score_key]
            note = parsed.get(note_key, "")
            summary_html.append(
                f"<div style='margin:0.75rem 0;display:flex;gap:0.5rem;align-items:center'>"
                f"<div style='min-width:200px;font-weight:bold;color:#444'>{model_name}</div>"
                f"<div style='font-size:24px;color:#666;min-width:2.5rem'>{score}</div>"
                f"<img src='cid:{cid_to_show}' style='max-width:180px;border-radius:4px' />"
                f"<div style='font-size:12px;color:#777;flex:1'><em>{note}</em><br/>{f.source_name if f else '?'} · t={f.frame_t if f else 0:.1f}s</div>"
                f"</div>"
            )
    summary_html.append("</body></html>")
    summary_plain = f"Cross-model comparison across {len(MODELS)} models, {len(corpus)} frames. See HTML version."
    ok, info = send_email(
        f"🏋️ Cross-model summary ({len(MODELS)} models)",
        summary_plain, "".join(summary_html),
        inline_images=thumb_cache,
    )
    print(f"  summary email: {'✓' if ok else '✗'} {info}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
