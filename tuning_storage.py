import json
import uuid
from datetime import datetime
from pathlib import Path

from project_paths import (
    ensure_tuning_dirs,
    get_tuning_presets_dir,
    get_tuning_profiles_dir,
)

SCHEMA_VERSION = 1

def _new_channel():
    return {
        "gain_db": 0.0,
        "delay_ms": 0.0,
        "polarity": "normal",
        "peq": [],
        "crossover": {},
        "limiters": {},
        "routing": {},
    }


DEFAULT_CHANNELS = {
    "1": _new_channel(),
    "2": _new_channel(),
}


def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _index_path(kind: str) -> Path:
    if kind == "presets":
        return get_tuning_presets_dir() / "index.json"
    if kind == "profiles":
        return get_tuning_profiles_dir() / "index.json"
    raise ValueError("kind must be 'presets' or 'profiles'")


def _item_path(kind: str, item_id: str) -> Path:
    if kind == "presets":
        return get_tuning_presets_dir() / f"{item_id}.json"
    if kind == "profiles":
        return get_tuning_profiles_dir() / f"{item_id}.json"
    raise ValueError("kind must be 'presets' or 'profiles'")


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_index(kind: str):
    ensure_tuning_dirs()
    return _load_json(_index_path(kind), [])


def save_index(kind: str, items):
    ensure_tuning_dirs()
    _save_json(_index_path(kind), items)


def list_presets():
    return load_index("presets")


def list_profiles():
    return load_index("profiles")


def _coerce_channels(channels):
    output = {}
    if not isinstance(channels, dict):
        channels = {}
    for ch in ("1", "2"):
        raw = channels.get(ch) if isinstance(channels, dict) else None
        base = _new_channel()
        if isinstance(raw, dict):
            base.update(raw)
        output[ch] = base
    return output


def _validate_channels(channels):
    errors = []
    if not isinstance(channels, dict):
        return ["channels must be an object"], _coerce_channels(channels)

    for ch in ("1", "2"):
        ch_data = channels.get(ch)
        if not isinstance(ch_data, dict):
            errors.append(f"channel {ch} must be an object")
            continue
        gain = ch_data.get("gain_db")
        if gain is not None:
            try:
                gain_val = float(gain)
                if gain_val < -120 or gain_val > 24:
                    errors.append(f"channel {ch} gain_db out of range")
            except Exception:
                errors.append(f"channel {ch} gain_db must be numeric")
        delay = ch_data.get("delay_ms")
        if delay is not None:
            try:
                delay_val = float(delay)
                if delay_val < 0 or delay_val > 2000:
                    errors.append(f"channel {ch} delay_ms out of range")
            except Exception:
                errors.append(f"channel {ch} delay_ms must be numeric")
        polarity = ch_data.get("polarity")
        if polarity not in (None, "normal", "inverted"):
            errors.append(f"channel {ch} polarity must be normal or inverted")
        if "peq" in ch_data and not isinstance(ch_data.get("peq"), list):
            errors.append(f"channel {ch} peq must be a list")
        for key in ("crossover", "limiters", "routing"):
            if key in ch_data and not isinstance(ch_data.get(key), dict):
                errors.append(f"channel {ch} {key} must be an object")
    return errors, _coerce_channels(channels)


def validate_preset(preset):
    errors = []
    if not isinstance(preset, dict):
        return ["preset must be an object"], {}

    preset = dict(preset)
    preset.setdefault("schema_version", SCHEMA_VERSION)
    preset.setdefault("id", str(uuid.uuid4()))
    preset.setdefault("created_at", _now_iso())
    preset.setdefault("name", "Untitled Preset")
    preset.setdefault("notes", "")
    preset.setdefault("tags", [])

    channels = preset.get("channels")
    channel_errors, channels = _validate_channels(channels)
    errors.extend(channel_errors)
    preset["channels"] = channels

    if not isinstance(preset.get("tags"), list):
        errors.append("tags must be a list")
        preset["tags"] = []

    return errors, preset


def validate_profile(profile):
    errors = []
    if not isinstance(profile, dict):
        return ["profile must be an object"], {}

    profile = dict(profile)
    profile.setdefault("schema_version", SCHEMA_VERSION)
    profile.setdefault("id", str(uuid.uuid4()))
    profile.setdefault("created_at", _now_iso())
    profile.setdefault("name", "Untitled Profile")
    profile.setdefault("parent_profile_id", None)
    profile.setdefault("derived_from_preset_id", None)
    profile.setdefault("mounting_context", "")
    profile.setdefault("notes", "")
    profile.setdefault("tags", [])
    profile.setdefault("measurement_links", [])
    profile.setdefault("change_log", [])
    profile.setdefault("auto_tune_runs", [])

    channels = profile.get("channels")
    channel_errors, channels = _validate_channels(channels)
    errors.extend(channel_errors)
    profile["channels"] = channels

    if not isinstance(profile.get("tags"), list):
        errors.append("tags must be a list")
        profile["tags"] = []

    if not isinstance(profile.get("measurement_links"), list):
        errors.append("measurement_links must be a list")
        profile["measurement_links"] = []

    if not isinstance(profile.get("change_log"), list):
        errors.append("change_log must be a list")
        profile["change_log"] = []

    return errors, profile


def load_preset(item_id: str):
    ensure_tuning_dirs()
    return _load_json(_item_path("presets", item_id), None)


def load_profile(item_id: str):
    ensure_tuning_dirs()
    return _load_json(_item_path("profiles", item_id), None)


def _update_index(kind: str, item):
    items = load_index(kind)
    if not isinstance(items, list):
        items = []
    entry = {
        "id": item.get("id"),
        "name": item.get("name"),
        "created_at": item.get("created_at"),
        "tags": item.get("tags", []),
    }
    existing = [i for i in items if i.get("id") == entry["id"]]
    if existing:
        items = [entry if i.get("id") == entry["id"] else i for i in items]
    else:
        items.append(entry)
    save_index(kind, items)


def save_preset(preset):
    ensure_tuning_dirs()
    errors, cleaned = validate_preset(preset)
    if errors:
        return errors, cleaned
    _save_json(_item_path("presets", cleaned["id"]), cleaned)
    _update_index("presets", cleaned)
    return [], cleaned


def save_profile(profile):
    ensure_tuning_dirs()
    errors, cleaned = validate_profile(profile)
    if errors:
        return errors, cleaned
    _save_json(_item_path("profiles", cleaned["id"]), cleaned)
    _update_index("profiles", cleaned)
    return [], cleaned
