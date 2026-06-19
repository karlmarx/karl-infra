from __future__ import annotations

from pathlib import Path

import yaml

from .models import ClientProfile, Firm


def load_firms(path: Path) -> list[Firm]:
    if not path.exists():
        raise FileNotFoundError(f"firms registry not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    firms_raw = raw.get("firms", [])
    out: list[Firm] = []
    for entry in firms_raw:
        out.append(Firm(**entry))
    return out


def load_client(path: Path) -> ClientProfile:
    if not path.exists():
        raise FileNotFoundError(
            f"client profile not found: {path} — "
            "copy client.example.yaml to client.yaml and fill in your details"
        )
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return ClientProfile(**raw)


def eligible_firms(firms: list[Firm]) -> list[Firm]:
    """Filter out firms we shouldn't contact: already declined, opt-out, etc."""
    out: list[Firm] = []
    for f in firms:
        if f.skip:
            continue
        if f.still_accepting == "no":
            continue
        if f.accepts_prep == "no":
            continue
        out.append(f)
    return out
