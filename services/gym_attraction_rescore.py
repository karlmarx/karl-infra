#!/usr/bin/env python3
"""Re-score the existing 42 gym-2month-pipeline GIFs with 27B attraction prompt.

For each <sha8>.json record:
  1. ffmpeg ONE peak frame at segment midpoint from the source mp4
  2. 27B on that frame with the attraction-aware prompt
  3. Augment record with: exercise_refined, primary_subject, background_men_*
  4. Persist to ~/.local/share/gym-attraction-rescore/<sha8>.json (resumable)

At end: dedupe by normalized exercise_name (best per bucket by attraction then
form), email an HTML digest with the existing GIFs inlined. Guard against
empty digest (no email if nothing scored).
"""

# /// script
# requires-python = ">=3.14"
# dependencies = ["openai"]
# ///

from __future__ import annotations

import json
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

SRC_DIR = Path.home() / ".local/share/gym-2month-pipeline"
OUT_DIR = Path.home() / ".local/share/gym-attraction-rescore"
ANALYSIS_MODEL = "mlx-community/Qwen3.5-27B-4bit"
ANALYSIS_BASE = "http://127.0.0.1:8084/v1"
MAX_GIF_BYTES = 2_500_000

PROMPT = """Gym video frame analysis. The primary subject is the person doing the exercise.
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


def wait_for(url: str, timeout: float = 600) -> bool:
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


def extract_peak_frame(source: Path, t: float, out: Path) -> bool:
    try:
        r = subprocess.run([
            "ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", str(source),
            "-frames:v", "1", "-vf", "scale=512:-1", "-qscale:v", "3",
            str(out),
        ], capture_output=True, timeout=30)
        return r.returncode == 0 and out.exists()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def query_27b(frame: Path) -> dict:
    from openai import OpenAI
    client = OpenAI(base_url=ANALYSIS_BASE, api_key="mlx-vlm", timeout=180)
    img_b64 = b64encode(frame.read_bytes()).decode("ascii")
    try:
        r = client.chat.completions.create(
            model=ANALYSIS_MODEL, max_tokens=400,
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                {"type": "text", "text": PROMPT},
            ]}],
        )
        raw = (r.choices[0].message.content or "").strip()
    except Exception as e:
        return {"_error": repr(e)}
    raw_clean = raw
    for f in ("```json", "```JSON", "```"):
        if f in raw_clean:
            parts = raw_clean.split(f)
            raw_clean = parts[1].split("```")[0] if len(parts) >= 2 else raw_clean
            break
    s, e = raw_clean.find("{"), raw_clean.rfind("}")
    if s >= 0 and e > s:
        try:
            return json.loads(raw_clean[s:e+1])
        except json.JSONDecodeError:
            pass
    return {"_parse_failed": True, "_raw": raw[:200]}


def normalize_exercise(name: str) -> str:
    if not name:
        return "unknown"
    s = re.sub(r"[^\w\s]", " ", name.lower()).strip()
    s = re.sub(r"\s+", " ", s)
    drop = {"barbell", "dumbbell", "cable", "machine", "smith"}
    parts = [w for w in s.split() if w not in drop]
    return " ".join(parts) if parts else s


def build_digest(records: list[dict]) -> tuple[str, str, dict[str, bytes]]:
    workouts = [r for r in records if r.get("gif_path") and Path(r["gif_path"]).exists()
                and r.get("attraction") and not r["attraction"].get("_error")
                and not r["attraction"].get("_parse_failed")]
    by_ex: dict[str, list[dict]] = {}
    for r in workouts:
        ex = normalize_exercise(r["attraction"].get("exercise_name") or r.get("label", {}).get("name", "unknown"))
        by_ex.setdefault(ex, []).append(r)

    chosen = []
    for ex, items in by_ex.items():
        items.sort(key=lambda r: (
            -(r["attraction"].get("background_men_hottest_score") or -1),
            -(r.get("label", {}).get("score", 0)),
        ))
        # Override the exercise key onto the chosen record for digest rendering
        winner = dict(items[0])
        winner["_bucket"] = ex
        chosen.append(winner)
    chosen.sort(key=lambda r: -(r["attraction"].get("background_men_hottest_score") or -1))

    images: dict[str, bytes] = {}
    rows = []
    for r in chosen:
        gp = Path(r["gif_path"])
        data = gp.read_bytes()
        if len(data) > MAX_GIF_BYTES:
            continue
        cid = r["sha_head"][:12]
        images[cid] = data
        a = r["attraction"]
        hot = a.get("background_men_hottest_score")
        cnt = a.get("background_men_count", 0)
        notes = a.get("background_men_notes", "") or "(none visible)"
        subj_notes = a.get("primary_subject", "") or ""
        ex_notes = a.get("exercise_notes", "") or ""
        seg = r.get("segment", [0, 0, 0])
        rows.append(
            f"<div style='margin:1.25rem 0;padding:0.85rem;background:#f7f7f8;border-radius:8px'>"
            f"<div style='display:flex;gap:0.85rem;align-items:flex-start;flex-wrap:wrap'>"
            f"<img src='cid:{cid}' style='max-width:340px;border-radius:6px' />"
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

    n_errors = len([r for r in records if r.get("attraction", {}).get("_error")
                    or r.get("attraction", {}).get("_parse_failed")])
    html = (
        "<html><body style='font-family:-apple-system,sans-serif;max-width:780px;"
        "margin:1.5rem auto;line-height:1.5;color:#222'>"
        f"<h1 style='margin-bottom:0.25rem'>🏋️ Gym digest · {len(chosen)} exercises</h1>"
        f"<p style='color:#666;margin-top:0'>"
        f"{len(records)} workout clips scored with Qwen3.5-27B · "
        f"{len(workouts)} parsed cleanly · {len(chosen)} unique exercises · "
        f"{n_errors} errors"
        f"</p>"
        + "".join(rows)
        + "<p style='color:#888;font-size:11px;margin-top:2rem'>"
        f"Generated {datetime.now():%Y-%m-%d %H:%M}. Source: ~/.local/share/gym-2month-pipeline/. "
        f"27B attraction-rescore pass."
        "</p></body></html>"
    )
    plain = [f"Gym digest · {len(chosen)} unique exercises from {len(records)} workout clips"]
    for r in chosen:
        a = r["attraction"]
        plain.append(f"- {r['_bucket']}  ({r['source_name']})  "
                     f"hot={a.get('background_men_hottest_score')}  "
                     f"count={a.get('background_men_count',0)}")
    return "\n".join(plain), html, images


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log_path = OUT_DIR / "run.log"
    log_fp = open(log_path, "a")

    def log(msg: str):
        line = f"[{datetime.now():%H:%M:%S}] {msg}"
        print(line, flush=True)
        log_fp.write(line + "\n")
        log_fp.flush()

    log("=== gym-attraction-rescore start ===")

    records_in = []
    for jf in sorted(SRC_DIR.glob("*.json")):
        if jf.name == "manifest.json":
            continue
        try:
            records_in.append(json.loads(jf.read_text()))
        except json.JSONDecodeError:
            pass
    log(f"{len(records_in)} source records from {SRC_DIR}")
    if not records_in:
        log("nothing to do")
        return 1

    if not wait_for(ANALYSIS_BASE, timeout=600):
        log(f"FAIL: 27B not responding at {ANALYSIS_BASE} after 10 min")
        return 2
    log(f"27B ready at {ANALYSIS_BASE}")

    augmented: list[dict] = []
    for i, r in enumerate(records_in, 1):
        sha8 = r["sha_head"][:16]
        cache = OUT_DIR / f"{sha8}.json"
        if cache.exists():
            try:
                rec = json.loads(cache.read_text())
                augmented.append(rec)
                log(f"[{i}/{len(records_in)}] {r['source_name']}  (cached)")
                continue
            except json.JSONDecodeError:
                pass

        src = Path(r.get("source_path", ""))
        gif = Path(r.get("gif_path", ""))
        seg = r.get("segment", [0, 0, 0])
        if not src.exists() or not gif.exists() or len(seg) < 2:
            log(f"[{i}/{len(records_in)}] {r['source_name']}  SKIP (missing files)")
            continue

        midpoint = (seg[0] + seg[1]) / 2
        with tempfile.TemporaryDirectory(prefix="gymrescore-") as td:
            frame = Path(td) / "peak.jpg"
            if not extract_peak_frame(src, midpoint, frame):
                log(f"[{i}/{len(records_in)}] {r['source_name']}  SKIP (frame extract failed)")
                continue
            t0 = time.time()
            attraction = query_27b(frame)
            dt = time.time() - t0

        ex_label = attraction.get("exercise_name", "?") if not attraction.get("_error") else "ERR"
        hot = attraction.get("background_men_hottest_score")
        cnt = attraction.get("background_men_count", 0)
        log(f"[{i}/{len(records_in)}] {r['source_name']}  ex='{ex_label}'  hot={hot}  cnt={cnt}  ({dt:.0f}s)")

        rec = {
            "sha_head": r["sha_head"],
            "source_name": r["source_name"],
            "source_path": r["source_path"],
            "gif_path": r["gif_path"],
            "segment": seg,
            "label": r.get("label", {}),
            "peak_frame_time": midpoint,
            "attraction": attraction,
        }
        cache.write_text(json.dumps(rec, indent=2, default=str))
        augmented.append(rec)

    # Guard: don't email empty digests
    has_content = any(r.get("attraction") and not r["attraction"].get("_error")
                      and not r["attraction"].get("_parse_failed") for r in augmented)
    if not has_content:
        log("no successfully-scored records; SKIPPING email")
        return 3

    plain, html, images = build_digest(augmented)
    subj = f"🏋️ gym digest · {len(images)} exercises (27B attraction)"
    ok, info = send_email(subj, plain, html, inline_images=images, image_subtype="gif")
    log(f"email: {'✓' if ok else '✗'} {info}  ({len(images)} GIFs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
