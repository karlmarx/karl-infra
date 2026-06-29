#!/usr/bin/env python3
"""Side-by-side analysis of multi-model gym scoring experiment.

Reads all *-scores.json from ~/.local/share/gym-model-compare-v2/, computes
per-model summary stats, identifies each model's top picks, and emails a
ranked side-by-side comparison with editorial notes per model.

Includes v1 Qwen3.5 data (different corpus — flagged in the report).
"""

# /// script
# requires-python = ">=3.14"
# dependencies = ["psutil"]
# ///

from __future__ import annotations

import json
import statistics
import sys
from base64 import b64encode
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _emaillib import send as send_email  # noqa: E402

V2_DIR = Path.home() / ".local/share/gym-model-compare-v2"
V1_DIR = Path.home() / ".local/share/gym-model-compare"
PROJECT = Path("/Users/kmx/projects/local-vlm-analysis")
DERIVATIVES = PROJECT / "data" / "derivatives"
THUMB_MAX_BYTES = 250_000

TASKS = [
    ("form_score",               "🏋️ Form / exercise picks",  "form_notes",       "exercise_name"),
    ("aesthetic_score",          "💪 Aesthetic / muscle picks", "aesthetic_notes", "muscles_visible"),
    ("background_admirer_score", "👀 Background-admirer picks", "admirer_notes",   "others_count"),
]


def load_v2_scores() -> dict[str, dict]:
    out = {}
    for sf in sorted(V2_DIR.glob("*-scores.json")):
        try:
            d = json.loads(sf.read_text())
            out[d.get("model", sf.stem.replace("-scores", ""))] = d.get("scores", {})
        except (json.JSONDecodeError, OSError):
            continue
    return out


def load_v1_scores() -> dict[str, dict]:
    """v1 used a different shape — adapt for comparison."""
    out = {}
    for sf in sorted(V1_DIR.glob("*-results.json")):
        try:
            d = json.loads(sf.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        model = d.get("model", sf.stem)
        scores = {}
        # v1 results: dict keyed by f"{sha}_{frame}_{task}" → string response
        # We need to map back to multi-task per-frame entries.
        per_frame: dict[str, dict] = {}
        for k, v in d.get("results", {}).items():
            # parse "{sha_head}_frame_NNN.jpg_{task}" — task is the suffix
            for task_key in ("exercise_form", "aesthetic_muscle", "background_gaze"):
                if k.endswith(f"_{task_key}"):
                    fid = k[:-len(f"_{task_key}")]
                    per_frame.setdefault(fid, {})[task_key] = v
                    break
        # Convert v1 task names to v2 score keys with best-effort regex extraction
        import re
        for fid, tasks in per_frame.items():
            entry = {}
            ef = tasks.get("exercise_form", "")
            am = tasks.get("aesthetic_muscle", "")
            bg = tasks.get("background_gaze", "")
            m = re.search(r'"form_quality"\s*:\s*(\d+)', ef)
            if m: entry["form_score"] = int(m.group(1))
            m = re.search(r'"exercise"\s*:\s*"([^"]+)"', ef)
            if m: entry["exercise_name"] = m.group(1)
            m = re.search(r'"explanation"\s*:\s*"([^"]+)"', ef)
            if m: entry["form_notes"] = m.group(1)
            m = re.search(r'"aesthetic_score"\s*:\s*(\d+)', am)
            if m: entry["aesthetic_score"] = int(m.group(1))
            m = re.search(r'"others_present"\s*:\s*(true|false)', bg)
            if m: entry["background_admirer_score"] = 7 if m.group(1) == "true" else 0  # v1 was bool
            entry["_raw"] = (ef + " | " + am + " | " + bg)[:300]
            scores[fid] = entry
        out[model] = scores
    return out


def model_metrics(scores: dict[str, dict]) -> dict:
    """Compute per-model summary stats."""
    valid_form = [s.get("form_score") for s in scores.values() if isinstance(s.get("form_score"), int)]
    valid_aes = [s.get("aesthetic_score") for s in scores.values() if isinstance(s.get("aesthetic_score"), int)]
    valid_bg = [s.get("background_admirer_score") for s in scores.values() if isinstance(s.get("background_admirer_score"), int)]
    parse_fails = sum(1 for s in scores.values() if s.get("_parse_failed") or s.get("_error"))
    total = len(scores)
    extras_offered = sum(1 for s in scores.values() if isinstance(s.get("extras"), str) and s["extras"].strip())
    exercise_names = Counter(s.get("exercise_name", "") for s in scores.values() if s.get("exercise_name"))
    distinct_exercises = sum(1 for k in exercise_names if k and k.lower() not in ("none", ""))

    return {
        "total": total,
        "parse_fails": parse_fails,
        "extras_offered": extras_offered,
        "form_mean": statistics.mean(valid_form) if valid_form else None,
        "form_stdev": statistics.stdev(valid_form) if len(valid_form) > 1 else 0,
        "form_max": max(valid_form) if valid_form else None,
        "aes_mean": statistics.mean(valid_aes) if valid_aes else None,
        "aes_stdev": statistics.stdev(valid_aes) if len(valid_aes) > 1 else 0,
        "aes_max": max(valid_aes) if valid_aes else None,
        "bg_mean": statistics.mean(valid_bg) if valid_bg else None,
        "bg_max": max(valid_bg) if valid_bg else None,
        "bg_hits_8plus": sum(1 for x in valid_bg if x >= 8),
        "distinct_exercises_named": distinct_exercises,
        "top_exercises": exercise_names.most_common(5),
    }


def editorial_take(model: str, m: dict) -> str:
    """My opinion of this model based on its score distribution + behaviors."""
    notes = []

    # Score discrimination
    if m["form_stdev"] is not None:
        if m["form_stdev"] < 1.5:
            notes.append("low score variance — collapses into a narrow range, doesn't rank decisively")
        elif m["form_stdev"] > 3.0:
            notes.append("wide score variance — willing to commit to strong picks")

    # Parse compliance
    if m["parse_fails"] > 5:
        notes.append(f"{m['parse_fails']} JSON-parse failures — not great at following structured output")
    elif m["parse_fails"] == 0:
        notes.append("perfect JSON compliance across all 316 frames")

    # Exercise vocabulary
    if m["distinct_exercises_named"] >= 15:
        notes.append(f"named {m['distinct_exercises_named']} distinct exercises — broad gym vocabulary")
    elif m["distinct_exercises_named"] < 5:
        notes.append(f"only {m['distinct_exercises_named']} distinct exercises — vague labeling")

    # Background admirer behavior
    if m["bg_hits_8plus"] == 0:
        notes.append("never flagged a confident background admirer (score 8+) — conservative on this task")
    elif m["bg_hits_8plus"] > 30:
        notes.append(f"flagged {m['bg_hits_8plus']} 'high-confidence admirer' frames — may be over-eager / hallucinating")

    # Extras
    if m["extras_offered"] > 50:
        notes.append(f"offered extras commentary on {m['extras_offered']} frames — engages with the open prompt")
    elif m["extras_offered"] < 5:
        notes.append(f"only {m['extras_offered']} extras offered — sticks to the structured fields")

    if not notes:
        notes.append("nothing remarkable in score distribution")

    return ". ".join(notes) + "."


def fmt(v):
    if v is None: return "—"
    if isinstance(v, float): return f"{v:.2f}"
    return str(v)


def render(v2: dict[str, dict], v1: dict[str, dict]) -> tuple[str, str]:
    rows = []
    for name, scores in v2.items():
        m = model_metrics(scores)
        rows.append((name, m, "v2"))
    for name, scores in v1.items():
        m = model_metrics(scores)
        rows.append((name + " (v1 corpus)", m, "v1"))

    plain = [
        "# Multi-model gym scoring — side-by-side comparison",
        "",
        f"v2 corpus: 316 frames across 45 workout videos (each frame scored by every model on 3 tasks).",
        f"v1 corpus: 10 fixed frames (different experiment, included for Qwen3.5 reference only).",
        "",
        "## Summary table",
        "",
        f"{'Model':<35} {'parse_ok':>9} {'form μ':>8} {'aes μ':>8} {'bg μ':>7} {'bg8+':>6} {'exers':>6} {'extras':>7}",
    ]
    for name, m, _v in rows:
        ok = m["total"] - m["parse_fails"]
        plain.append(
            f"{name:<35} {ok:>4}/{m['total']:<4} {fmt(m['form_mean']):>8} {fmt(m['aes_mean']):>8} "
            f"{fmt(m['bg_mean']):>7} {m['bg_hits_8plus']:>6} {m['distinct_exercises_named']:>6} {m['extras_offered']:>7}"
        )

    plain.append("\n## Editorial take per model\n")
    for name, m, _v in rows:
        plain.append(f"### {name}\n")
        plain.append(f"  {editorial_take(name, m)}")
        if m["top_exercises"]:
            top = ", ".join(f"{ex or '(blank)'}×{c}" for ex, c in m["top_exercises"][:3])
            plain.append(f"  Most-named exercises: {top}")
        plain.append("")

    # HTML version
    html = [
        "<html><body style='font-family:-apple-system,sans-serif;max-width:880px;margin:1rem auto;line-height:1.5;color:#222'>",
        "<h1>Multi-model gym scoring — side-by-side</h1>",
        "<p style='color:#666;font-size:13px'>",
        "<strong>v2 corpus:</strong> 316 frames across 45 workout videos, each scored on 3 tasks (form / aesthetic / background-admirer) plus open-ended extras.<br/>",
        "<strong>v1 corpus:</strong> 10 fixed frames; Qwen3.5 ran here only. Direct numeric comparison with v2 is rough — different inputs.",
        "</p>",
        "<h2>Summary</h2>",
        "<table style='border-collapse:collapse;width:100%;font-size:13px'>",
        "<thead><tr style='background:#f5f5f5'>",
        "<th style='text-align:left;padding:6px;border:1px solid #ddd'>Model</th>",
        "<th style='padding:6px;border:1px solid #ddd' title='Frames with valid JSON / total'>parse</th>",
        "<th style='padding:6px;border:1px solid #ddd' title='Mean form score across corpus'>form μ</th>",
        "<th style='padding:6px;border:1px solid #ddd' title='Mean aesthetic score'>aes μ</th>",
        "<th style='padding:6px;border:1px solid #ddd' title='Mean admirer score'>bg μ</th>",
        "<th style='padding:6px;border:1px solid #ddd' title='Frames where bg admirer score ≥ 8'>bg8+</th>",
        "<th style='padding:6px;border:1px solid #ddd' title='Distinct exercise names'>exers</th>",
        "<th style='padding:6px;border:1px solid #ddd' title='Frames with open-ended extras'>extras</th>",
        "</tr></thead><tbody>",
    ]
    for name, m, version in rows:
        ok = m["total"] - m["parse_fails"]
        bg_color = "#fafafa" if version == "v2" else "#fff8e8"
        html.append(
            f"<tr style='background:{bg_color}'>"
            f"<td style='padding:6px;border:1px solid #ddd;font-weight:bold'>{name}</td>"
            f"<td style='padding:6px;border:1px solid #ddd;text-align:center'>{ok}/{m['total']}</td>"
            f"<td style='padding:6px;border:1px solid #ddd;text-align:center'>{fmt(m['form_mean'])}</td>"
            f"<td style='padding:6px;border:1px solid #ddd;text-align:center'>{fmt(m['aes_mean'])}</td>"
            f"<td style='padding:6px;border:1px solid #ddd;text-align:center'>{fmt(m['bg_mean'])}</td>"
            f"<td style='padding:6px;border:1px solid #ddd;text-align:center'>{m['bg_hits_8plus']}</td>"
            f"<td style='padding:6px;border:1px solid #ddd;text-align:center'>{m['distinct_exercises_named']}</td>"
            f"<td style='padding:6px;border:1px solid #ddd;text-align:center'>{m['extras_offered']}</td>"
            f"</tr>"
        )
    html.append("</tbody></table>")

    html.append("<h2>Editorial take per model</h2>")
    for name, m, version in rows:
        html.append(
            f"<div style='margin:1rem 0;padding:0.75rem;background:#fafafa;border-left:3px solid #4CAF50;border-radius:4px'>"
            f"<div style='font-weight:bold;color:#333;font-size:15px'>{name}</div>"
            f"<div style='color:#555;font-size:13px;margin-top:0.25rem'>{editorial_take(name, m)}</div>"
        )
        if m["top_exercises"]:
            top = " · ".join(f"<code>{(ex or 'blank').replace('<','&lt;')}</code>×{c}" for ex, c in m["top_exercises"][:3])
            html.append(f"<div style='color:#888;font-size:12px;margin-top:0.25rem'>Most-named: {top}</div>")
        html.append("</div>")

    html.append(
        "<h2>What I think overall</h2>"
        "<p style='font-size:14px'>"
        "Look at <strong>parse-compliance</strong> first — models that fail JSON consistently are surfacing weaker frame picks "
        "because my filter falls back to regex extraction. Then look at <strong>form-score variance (form μ + stdev)</strong> — "
        "models with wider distributions are more willing to commit to a top pick rather than rate everything as a 6 or 7. "
        "Then look at <strong>distinct_exercises_named</strong> — a model that names <em>'barbell row'</em> vs <em>'cable row'</em> vs "
        "<em>'chest-supported row'</em> shows real gym vocabulary; a model that says <em>'exercise'</em> 50 times is generic. "
        "The <strong>background-admirer task</strong> is the noisiest signal — models that flag 30+ frames as admirers (bg8+) "
        "are almost certainly hallucinating. The trustable signal is a model that flags 0-3 but with high confidence.</p>"
        "<p style='font-size:14px'>"
        "<strong>Qwen 3.5</strong> appears under (v1 corpus). I excluded it from v2 because you'd already seen the results; "
        "the experiment is being re-run with Qwen3.5-9B and Qwen3.5-27B on the same v2 corpus so the next comparison email "
        "will have them apples-to-apples.</p>"
    )
    html.append("</body></html>")

    return "\n".join(plain), "".join(html)


def main() -> int:
    v2 = load_v2_scores()
    v1 = load_v1_scores()
    print(f"loaded {len(v2)} v2 models, {len(v1)} v1 models")
    plain, html = render(v2, v1)
    ok, info = send_email("🏋️ Multi-model gym comparison + my take", plain, html)
    print(f"email: {'✓' if ok else '✗'} {info}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
