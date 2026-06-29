#!/usr/bin/env python3
"""Gym video multi-model comparison experiment.

For a small fixed test set of recent workout videos, run each MLX-VLM model
(smallest→largest) across three tasks:

  1. exercise_form    — name the exercise + rate form quality 1-10
  2. aesthetic_muscle — rate visual appeal + describe visible muscle groups
  3. background_gaze  — note any background people + whether they appear
                        to be looking at the subject

Each model gets its own mlx_vlm.server on port 8083 (leaves :8081 worker alone).
After each model completes, emails Karl the results inline with the frames.
Final summary email compares responses side-by-side.

Caveats / scope:
  - Test set is fixed at top-5 most-recent is_workout videos with frames on disk.
  - 2 representative frames per video (middle-third positions).
  - 'background_gaze' task is novel; expect varying compliance across models.
  - Smaller models (gemma-3-4b) often won't follow JSON-structured output.
"""

# /// script
# requires-python = ">=3.14"
# dependencies = ["psutil", "openai", "requests"]
# ///

from __future__ import annotations

import json
import os
import shlex
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from base64 import b64encode
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _emaillib import send as send_email  # noqa: E402


PROJECT = Path("/Users/kmx/projects/local-vlm-analysis")
VIDEOS_JSON = PROJECT / "data" / "videos"
DERIVATIVES = PROJECT / "data" / "derivatives"
EXPERIMENT_DIR = Path.home() / ".local/share/gym-model-compare"
PORT = 8083
VIDEOS_PER_TEST = 5
FRAMES_PER_VIDEO = 2

MODELS = [
    ("gemma-3-4b-it-4bit",         "mlx-community/gemma-3-4b-it-4bit"),
    ("Qwen3.5-9B-MLX-4bit",        "mlx-community/Qwen3.5-9B-MLX-4bit"),
    ("paligemma2-10b-mix-448-4bit","mlx-community/paligemma2-10b-mix-448-4bit"),
    ("gemma-4-26b-a4b-it-4bit",    "mlx-community/gemma-4-26b-a4b-it-4bit"),
    ("Qwen3.5-27B-4bit",           "mlx-community/Qwen3.5-27B-4bit"),
]


@dataclass
class Task:
    key: str
    label: str
    prompt: str


TASKS = [
    Task(
        key="exercise_form",
        label="Exercise & form quality",
        prompt=(
            "Look at this gym/workout image. Identify the exercise being performed "
            "(specific name like 'barbell row', 'pec deck', 'kettlebell swing'). "
            "Rate the visible form quality 1-10 and explain in 1-2 sentences. "
            'Respond ONLY as JSON: {"exercise": "...", "form_quality": 0-10, "explanation": "..."}. '
            'If no exercise visible, return {"exercise": "none", "form_quality": 0, "explanation": "..."}.'
        ),
    ),
    Task(
        key="aesthetic_muscle",
        label="Aesthetic appeal & muscle definition",
        prompt=(
            "Rate this image's overall aesthetic appeal 1-10 based on composition, "
            "lighting, and the subject's physique. Note specifically any visibly "
            "bulging or well-defined muscle groups (e.g. biceps, lats, glutes, "
            "quads, shoulders). "
            'Respond ONLY as JSON: {"aesthetic_score": 0-10, "muscles_visible": [...], "notes": "..."}.'
        ),
    ),
    Task(
        key="background_gaze",
        label="Background people & gaze direction",
        prompt=(
            "Besides the main person in this image, are there OTHER people visible "
            "(in the background, at other equipment, etc.)? For each other person, "
            "describe: where they are in the frame, what they appear to be doing, "
            "and whether they appear to be looking toward the main subject. Be "
            "concise and objective. "
            'Respond ONLY as JSON: {"others_present": bool, "count": 0, "people": [{"position":"...","activity":"...","looking_at_subject":"yes/no/unclear","notes":"..."}]}.'
        ),
    ),
]


def select_test_set() -> list[dict]:
    """Pick top-N most-recent is_workout videos that have frames on disk."""
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
        if not sha_head:
            continue
        deriv = DERIVATIVES / sha_head
        if not deriv.exists():
            continue
        frames = sorted(deriv.glob("frame_*.jpg"))
        if not frames:
            continue
        ca = d.get("meta", {}).get("created_at", "")
        try:
            dt = datetime.strptime(ca, "%Y:%m:%d %H:%M:%S")
        except ValueError:
            dt = datetime.min
        items.append({
            "dt": dt,
            "sha_head": sha_head,
            "source_name": Path(d.get("source", "")).name,
            "duration_s": d.get("duration_s", 0),
            "frames": frames,
            "workout_summary": d.get("workout_summary", {}),
        })
    items.sort(key=lambda x: x["dt"], reverse=True)
    selected = items[:VIDEOS_PER_TEST]

    # Pick FRAMES_PER_VIDEO representative frames per video (evenly spaced from middle)
    for item in selected:
        n = len(item["frames"])
        if n <= FRAMES_PER_VIDEO:
            item["chosen_frames"] = item["frames"]
        else:
            # Middle band: skip first and last frame, sample evenly
            mid_start = max(1, n // 4)
            mid_end = min(n - 1, n * 3 // 4)
            band = item["frames"][mid_start:mid_end + 1] or item["frames"][1:-1] or item["frames"]
            step = max(1, len(band) // FRAMES_PER_VIDEO)
            item["chosen_frames"] = band[::step][:FRAMES_PER_VIDEO]
    return selected


def port_is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def wait_for_server(port: int, timeout: float = 180) -> bool:
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
    """Spawn mlx_vlm.server in background. Returns the Popen."""
    cmd = [
        str(Path.home() / ".local/bin/mlx_vlm.server"),
        "--model", model_id,
        "--host", "127.0.0.1",
        "--port", str(port),
    ]
    log_fp = open(log_path, "w")
    proc = subprocess.Popen(
        cmd,
        stdout=log_fp,
        stderr=subprocess.STDOUT,
        env={**os.environ, "PATH": f"{Path.home()}/.local/bin:" + os.environ.get("PATH", "")},
    )
    return proc


def stop_server(proc: subprocess.Popen) -> None:
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=10)
    except (subprocess.TimeoutExpired, ProcessLookupError):
        try:
            proc.kill()
        except ProcessLookupError:
            pass


def query_vlm(model_id: str, port: int, frame_path: Path, prompt: str, timeout: float = 90) -> str:
    """Call /v1/chat/completions with the image inline as base64 data URI."""
    from openai import OpenAI
    client = OpenAI(base_url=f"http://127.0.0.1:{port}/v1", api_key="mlx-vlm", timeout=timeout)
    img_b64 = b64encode(frame_path.read_bytes()).decode("ascii")
    image_uri = f"data:image/jpeg;base64,{img_b64}"
    try:
        resp = client.chat.completions.create(
            model=model_id,
            max_tokens=512,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_uri}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        return f"[ERROR: {e!r}]"


def try_parse_json(text: str) -> dict | None:
    """Best-effort JSON extraction — tolerates markdown fences, leading prose."""
    if not text:
        return None
    # Strip markdown fences
    cleaned = text
    for fence in ("```json", "```JSON", "```"):
        if fence in cleaned:
            parts = cleaned.split(fence)
            cleaned = parts[1] if len(parts) >= 2 else cleaned
            cleaned = cleaned.split("```")[0]
    # Find first { and last }
    s, e = cleaned.find("{"), cleaned.rfind("}")
    if s == -1 or e == -1 or e <= s:
        return None
    try:
        return json.loads(cleaned[s:e + 1])
    except json.JSONDecodeError:
        return None


def render_model_email(model_name: str, test_set: list[dict], results: dict, elapsed_s: float, images: dict[str, bytes]) -> tuple[str, str]:
    """Render per-model email with results grouped by task, frames inline."""
    plain_lines = [
        f"# Model: {model_name}",
        f"_Test set: {len(test_set)} workout videos, {sum(len(v['chosen_frames']) for v in test_set)} frames, 3 tasks_",
        f"_Elapsed: {elapsed_s:.1f}s_",
        "",
    ]
    html_parts = [
        "<html><body style='font-family:-apple-system,sans-serif;max-width:720px;margin:1rem auto;line-height:1.5'>",
        f"<h1 style='margin-bottom:0.25rem'>{model_name}</h1>",
        f"<p style='color:#888;font-size:13px;margin-top:0'>{len(test_set)} videos · "
        f"{sum(len(v['chosen_frames']) for v in test_set)} frames · 3 tasks · "
        f"{elapsed_s:.1f}s total</p>",
    ]

    for task in TASKS:
        plain_lines.append(f"\n## {task.label}\n")
        html_parts.append(
            f"<h2 style='color:#444;border-bottom:1px solid #eee;margin-top:2rem'>{task.label}</h2>"
        )
        for v_idx, item in enumerate(test_set):
            for f_idx, frame in enumerate(item["chosen_frames"]):
                key = f"{item['sha_head']}_{frame.name}_{task.key}"
                cid = f"{item['sha_head'][:8]}_f{f_idx}"
                response = results.get(key, "(no response)")
                parsed = try_parse_json(response)
                src = item["source_name"]

                plain_lines.append(f"### {src} · {frame.name}")
                if parsed:
                    for k, val in parsed.items():
                        plain_lines.append(f"  {k}: {val!r}")
                else:
                    plain_lines.append(f"  raw: {response[:300]}")
                plain_lines.append("")

                html_parts.append(
                    f"<div style='margin:1.2rem 0;padding:0.75rem;background:#fafafa;border-radius:6px'>"
                    f"<div style='display:flex;gap:1rem'>"
                    f"<img src='cid:{cid}' style='max-width:220px;border-radius:4px;object-fit:cover' />"
                    f"<div style='flex:1;font-size:13px'>"
                    f"<div style='color:#888;margin-bottom:0.25rem'>{src} · {frame.name}</div>"
                )
                if parsed:
                    for k, val in parsed.items():
                        html_parts.append(
                            f"<div><strong style='color:#555'>{k}:</strong> "
                            f"<span style='color:#222'>{json.dumps(val) if not isinstance(val, str) else val}</span></div>"
                        )
                else:
                    html_parts.append(
                        f"<pre style='white-space:pre-wrap;font-family:inherit;color:#444;margin:0'>"
                        f"{response[:600]}</pre>"
                    )
                html_parts.append("</div></div></div>")

    html_parts.append("</body></html>")
    return "\n".join(plain_lines), "".join(html_parts)


def main() -> int:
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)

    test_set = select_test_set()
    if not test_set:
        print("FAIL: no workout videos with extracted frames found")
        return 1

    print(f"=== Test set ===")
    for v in test_set:
        print(f"  {v['dt']:%Y-%m-%d %H:%M}  {v['source_name']}  "
              f"({len(v['chosen_frames'])} frames chosen of {len(v['frames'])})")

    # Pre-load image bytes once for inline embedding (and CID mapping)
    images: dict[str, bytes] = {}
    for item in test_set:
        for f_idx, frame in enumerate(item["chosen_frames"]):
            cid = f"{item['sha_head'][:8]}_f{f_idx}"
            try:
                data = frame.read_bytes()
                if len(data) < 250_000:
                    images[cid] = data
            except OSError:
                pass

    all_model_results: dict[str, dict] = {}
    for model_name, model_id in MODELS:
        print(f"\n=== Model: {model_name} ===")
        start_ts = time.time()
        log_path = EXPERIMENT_DIR / f"{model_name}-server.log"

        proc = start_server(model_id, PORT, log_path)
        try:
            if not wait_for_server(PORT, timeout=240):
                print(f"  ✗ server failed to come up (see {log_path})")
                stop_server(proc)
                continue
            print(f"  ✓ server up ({time.time() - start_ts:.0f}s load)")

            results: dict[str, str] = {}
            for v_idx, item in enumerate(test_set):
                for f_idx, frame in enumerate(item["chosen_frames"]):
                    for task in TASKS:
                        key = f"{item['sha_head']}_{frame.name}_{task.key}"
                        t0 = time.time()
                        out = query_vlm(model_id, PORT, frame, task.prompt)
                        elapsed = time.time() - t0
                        results[key] = out
                        preview = out[:80].replace("\n", " ")
                        print(f"    [{v_idx+1}/{len(test_set)}.{f_idx+1}] {task.key} {elapsed:5.1f}s: {preview}")
        finally:
            stop_server(proc)
            print(f"  server stopped; total {time.time() - start_ts:.0f}s")

        all_model_results[model_name] = results

        # Save raw results to disk in case of crash
        out_file = EXPERIMENT_DIR / f"{model_name}-results.json"
        out_file.write_text(json.dumps({
            "model": model_name,
            "elapsed_s": time.time() - start_ts,
            "test_set": [{"sha_head": v["sha_head"], "source": v["source_name"],
                          "frames": [str(f) for f in v["chosen_frames"]]} for v in test_set],
            "results": results,
        }, indent=2))

        plain, html = render_model_email(model_name, test_set, results, time.time() - start_ts, images)
        subject = f"🏋️ Model comparison: {model_name}"
        ok, info = send_email(subject, plain, html, inline_images=images)
        print(f"  email: {'✓' if ok else '✗'} {info}")

    # Final summary email comparing models
    print(f"\n=== Sending comparison summary ===")
    summary_plain = [f"# Multi-model comparison summary", ""]
    summary_html = [
        "<html><body style='font-family:-apple-system,sans-serif;max-width:760px;margin:1rem auto'>",
        "<h1>Multi-model gym comparison</h1>",
        f"<p style='color:#666'>Tested {len(MODELS)} models on {len(test_set)} workout videos "
        f"({sum(len(v['chosen_frames']) for v in test_set)} frames) across 3 tasks.</p>",
    ]
    for task in TASKS:
        summary_plain.append(f"\n## {task.label}\n")
        summary_html.append(f"<h2 style='border-bottom:1px solid #eee'>{task.label}</h2>")
        # Pick first frame as anchor for side-by-side
        first = test_set[0]
        anchor_frame = first["chosen_frames"][0]
        anchor_key = f"{first['sha_head']}_{anchor_frame.name}_{task.key}"
        summary_html.append(
            f"<p style='color:#888;font-size:12px'>Anchor frame: {first['source_name']} · {anchor_frame.name}</p>"
            f"<img src='cid:{first['sha_head'][:8]}_f0' style='max-width:300px;border-radius:4px' />"
        )
        for model_name, _ in MODELS:
            resp = all_model_results.get(model_name, {}).get(anchor_key, "(no result)")
            parsed = try_parse_json(resp)
            summary_plain.append(f"  {model_name}:")
            summary_html.append(
                f"<div style='margin:1rem 0;padding:0.75rem;background:#fafafa;border-radius:6px'>"
                f"<div style='font-weight:bold;color:#444'>{model_name}</div>"
            )
            if parsed:
                for k, v in parsed.items():
                    summary_plain.append(f"    {k}: {v}")
                    summary_html.append(f"<div style='font-size:13px'><strong>{k}:</strong> {v}</div>")
            else:
                summary_plain.append(f"    {resp[:200]}")
                summary_html.append(f"<pre style='white-space:pre-wrap;font-size:12px;color:#555'>{resp[:400]}</pre>")
            summary_html.append("</div>")
    summary_html.append("</body></html>")

    ok, info = send_email("🏋️ Multi-model summary", "\n".join(summary_plain), "".join(summary_html), inline_images=images)
    print(f"  summary email: {'✓' if ok else '✗'} {info}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
