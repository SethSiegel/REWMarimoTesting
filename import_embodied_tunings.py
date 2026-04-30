import json
import re
import uuid
from pathlib import Path

from tuning_storage import save_profile


ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT / "tuning_files" / "Embodied Sound tunings"


def _is_ignored(path: Path) -> bool:
    name = path.name
    if "__MACOSX" in path.parts:
        return True
    if name in (".DS_Store",):
        return True
    if name.startswith("._"):
        return True
    return False


def _read_json(path: Path):
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore").strip()
    except Exception:
        return None
    if not raw.startswith("{"):
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


HI_LO_RE = re.compile(r"^(?P<base>.*?)(?:[ _-]+)(?P<band>hi|lo)$", re.IGNORECASE)


def _split_hi_lo(path: Path):
    stem = path.stem if path.suffix else path.name
    match = HI_LO_RE.match(stem)
    if not match:
        return None, None
    base = match.group("base").strip()
    band = match.group("band").lower()
    return base, band


def _as_channel(data, source_path: str):
    output = data.get("output", {}) if isinstance(data, dict) else {}
    crossover = data.get("crossover", {}) if isinstance(data, dict) else {}
    band = crossover.get("bandGainAndDelay", {}) if isinstance(crossover, dict) else {}

    invert = bool(band.get("invert", False))
    polarity = "inverted" if invert else "normal"

    peq_list = []
    filters = data.get("outputEqFilters", {})
    if isinstance(filters, dict):
        for key in sorted(filters.keys(), key=lambda k: str(k)):
            filt = filters.get(key)
            if not isinstance(filt, dict):
                continue
            peq_list.append(
                {
                    "id": str(key),
                    "type": filt.get("type"),
                    "frequency_hz": filt.get("frequency"),
                    "gain_db": filt.get("gain"),
                    "q": filt.get("q"),
                    "enabled": bool(filt.get("enable", False)),
                }
            )

    limiters = {
        "rms": data.get("rmsLimiter", {}),
        "peak": data.get("peakLimiter", {}),
        "loadMonitor": data.get("loadMonitor", {}),
        "pilotToneDetector": data.get("pilotToneDetector", {}),
    }

    routing = {
        "inputSelector": data.get("inputSelector", {}),
        "output": {k: v for k, v in output.items() if k not in ("fader", "mute")},
        "mute": output.get("mute"),
        "hiZLoZ": output.get("hiZLoZ"),
        "source_channel_number": data.get("channelNumber"),
        "source_device_id": data.get("deviceId"),
        "source_version": data.get("version"),
        "source_file": source_path,
    }

    return {
        "gain_db": output.get("fader", 0.0),
        "delay_ms": band.get("delay", 0.0),
        "polarity": polarity,
        "peq": peq_list,
        "crossover": crossover,
        "limiters": limiters,
        "routing": routing,
    }


def main():
    if not SOURCE_ROOT.exists():
        raise SystemExit(f"Missing source folder: {SOURCE_ROOT}")

    groups = {}
    for path in SOURCE_ROOT.rglob("*"):
        if path.is_dir() or _is_ignored(path):
            continue
        base, band = _split_hi_lo(path)
        if not base or band not in ("hi", "lo"):
            continue
        data = _read_json(path)
        if not isinstance(data, dict):
            continue
        rel_dir = path.parent.relative_to(SOURCE_ROOT)
        key = (str(rel_dir).lower(), base.lower())
        groups.setdefault(key, {"rel_dir": rel_dir, "base": base, "files": {}})
        groups[key]["files"][band] = (path, data)

    created = 0
    skipped = 0
    for group in groups.values():
        files = group["files"]
        if "hi" not in files or "lo" not in files:
            skipped += 1
            continue

        rel_dir = group["rel_dir"]
        base_display = group["base"].replace("_", " ").strip()
        group_label = " / ".join(rel_dir.parts) if str(rel_dir) != "." else "Embodied Sound"
        profile_name = f"{group_label} - {base_display}"

        hi_path, hi_data = files["hi"]
        lo_path, lo_data = files["lo"]

        rel_hi = str(hi_path.relative_to(ROOT)).replace("\\", "/")
        rel_lo = str(lo_path.relative_to(ROOT)).replace("\\", "/")

        profile_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"embodied:{group_label}/{base_display}".lower(),
            )
        )

        profile = {
            "schema_version": 1,
            "id": profile_id,
            "name": profile_name,
            "parent_profile_id": None,
            "derived_from_preset_id": None,
            "mounting_context": base_display,
            "notes": f"Imported from {rel_hi} and {rel_lo}",
            "tags": [
                "source:embodied_sound_tunings",
                f"group:{group_label.lower().replace(' ', '_')}",
            ],
            "measurement_links": [
                {"kind": "lea_json", "relative_path": rel_hi},
                {"kind": "lea_json", "relative_path": rel_lo},
            ],
            "channels": {
                "1": _as_channel(lo_data, rel_lo),
                "2": _as_channel(hi_data, rel_hi),
            },
            "change_log": [],
            "auto_tune_runs": [],
        }

        errors, cleaned = save_profile(profile)
        if errors:
            skipped += 1
            continue
        created += 1

    print(f"Profiles created/updated: {created}")
    if skipped:
        print(f"Groups skipped (missing hi/lo or invalid): {skipped}")


if __name__ == "__main__":
    main()
