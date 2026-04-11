# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "jsonpickle>=4.1.1",
#     "marimo>=0.19.11",
#     "pyzmq>=27.1.0",
#     "requests>=2.32.5",
#     "websockets>=12.0",
# ]
# [tool.marimo.opengraph]
# title = "LEA Tuning Profiles"
# description = "Manage LEA tuning presets and profiles with lineage and REW links."
# image = "https://www.leaamplification.com/wp-content/uploads/2020/10/LEA-Amplification-Logo.png"
# ///

import marimo

__generated_with = "0.19.11"
app = marimo.App(app_title="LEA Tuning Profiles")

# NOTE: marimo requires unique variable names across cells.
# Use leading "_" for cell-local scratch variables to avoid collisions.

with app.setup:
    import sys
    import json
    import os
    import uuid
    from datetime import datetime
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    import marimo as mo

    from project_paths import (
        ensure_tuning_dirs,
        get_data_root,
        get_tuning_root,
        get_tuning_exports_dir,
    )
    from tuning_storage import (
        DEFAULT_CHANNELS,
        list_presets,
        list_profiles,
        load_preset,
        load_profile,
        save_preset,
        save_profile,
        validate_preset,
        validate_profile,
    )
    from LEA_controls import Lea_Settings


@app.cell
def _():
    mo.md(
        r"""
        # LEA Tuning Profiles
        Manage presets and profiles, link REW measurements, and apply settings to LEA amps.
        """
    )
    return


@app.cell
def _():
    ensure_tuning_dirs()
    return


@app.cell
def _():
    data_root = get_data_root()
    command_map_path = get_tuning_root() / "lea_command_map.json"
    if command_map_path.exists():
        try:
            command_map = json.loads(command_map_path.read_text(encoding="utf-8"))
            command_map_error = ""
        except Exception as exc:
            command_map = {"schema_version": 1, "channels": {}}
            command_map_error = f"Failed to load command map: {exc}"
    else:
        command_map = {"schema_version": 1, "channels": {}}
        command_map_error = "Command map not found."
    command_map, command_map_error, command_map_path
    return command_map, command_map_error, command_map_path, data_root


@app.cell
def _():
    def new_preset_template():
        return {
            "schema_version": 1,
            "id": str(uuid.uuid4()),
            "name": "Untitled Preset",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "notes": "",
            "tags": [],
            "channels": json.loads(json.dumps(DEFAULT_CHANNELS)),
        }

    def new_profile_template():
        return {
            "schema_version": 1,
            "id": str(uuid.uuid4()),
            "name": "Untitled Profile",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "parent_profile_id": None,
            "derived_from_preset_id": None,
            "mounting_context": "",
            "notes": "",
            "tags": [],
            "measurement_links": [],
            "channels": json.loads(json.dumps(DEFAULT_CHANNELS)),
            "change_log": [],
            "auto_tune_runs": [],
        }

    def parse_json_field(text, default):
        if text is None:
            return default, ""
        raw = str(text).strip()
        if raw == "":
            return default, ""
        try:
            return json.loads(raw), ""
        except Exception as exc:
            return default, f"Invalid JSON: {exc}"

    def build_channels_from_ui(
        ch1_gain,
        ch1_delay,
        ch1_polarity,
        ch1_peq,
        ch1_crossover,
        ch1_limiters,
        ch1_routing,
        ch2_gain,
        ch2_delay,
        ch2_polarity,
        ch2_peq,
        ch2_crossover,
        ch2_limiters,
        ch2_routing,
    ):
        ch1_peq_val, ch1_peq_err = parse_json_field(ch1_peq, [])
        ch1_cross_val, ch1_cross_err = parse_json_field(ch1_crossover, {})
        ch1_lim_val, ch1_lim_err = parse_json_field(ch1_limiters, {})
        ch1_route_val, ch1_route_err = parse_json_field(ch1_routing, {})
        ch2_peq_val, ch2_peq_err = parse_json_field(ch2_peq, [])
        ch2_cross_val, ch2_cross_err = parse_json_field(ch2_crossover, {})
        ch2_lim_val, ch2_lim_err = parse_json_field(ch2_limiters, {})
        ch2_route_val, ch2_route_err = parse_json_field(ch2_routing, {})

        channels = {
            "1": {
                "gain_db": ch1_gain,
                "delay_ms": ch1_delay,
                "polarity": ch1_polarity,
                "peq": ch1_peq_val,
                "crossover": ch1_cross_val,
                "limiters": ch1_lim_val,
                "routing": ch1_route_val,
            },
            "2": {
                "gain_db": ch2_gain,
                "delay_ms": ch2_delay,
                "polarity": ch2_polarity,
                "peq": ch2_peq_val,
                "crossover": ch2_cross_val,
                "limiters": ch2_lim_val,
                "routing": ch2_route_val,
            },
        }

        errors = [
            ch1_peq_err,
            ch1_cross_err,
            ch1_lim_err,
            ch1_route_err,
            ch2_peq_err,
            ch2_cross_err,
            ch2_lim_err,
            ch2_route_err,
        ]
        errors = [e for e in errors if e]
        return channels, errors

    return build_channels_from_ui, new_preset_template, new_profile_template, parse_json_field


@app.cell
def _(save_result_state):
    _ = save_result_state()
    presets_index = list_presets()
    profiles_index = list_profiles()
    return presets_index, profiles_index


@app.cell
def _():
    editor_state, set_editor_state = mo.state(
        {
            "kind": "profile",
            "data": new_profile_template(),
            "source_id": None,
        }
    )
    return editor_state, set_editor_state


@app.cell
def _():
    filter_text = mo.ui.text(label="Filter presets/profiles", value="")
    filter_text
    return (filter_text,)


@app.cell
def _(filter_text, presets_index):
    _filter_value = (filter_text.value or "").strip().lower()
    _preset_items = []
    for _item in presets_index or []:
        _name = str(_item.get("name", ""))
        _item_id = str(_item.get("id", ""))
        if _filter_value and _filter_value not in _name.lower() and _filter_value not in _item_id.lower():
            continue
        _preset_items.append((_item_id, _name))
    _preset_labels = [f"{_item_id}: {_name}" for _item_id, _name in _preset_items]
    preset_label_to_id = {label: _item_id for label, _item_id in zip(_preset_labels, [i[0] for i in _preset_items])}
    preset_select = mo.ui.dropdown(
        options=_preset_labels,
        value=_preset_labels[0] if _preset_labels else None,
        label="Presets",
    )
    preset_select
    return preset_label_to_id, preset_select


@app.cell
def _(filter_text, profiles_index):
    _filter_value = (filter_text.value or "").strip().lower()
    _profile_items = []
    for _item in profiles_index or []:
        _name = str(_item.get("name", ""))
        _item_id = str(_item.get("id", ""))
        if _filter_value and _filter_value not in _name.lower() and _filter_value not in _item_id.lower():
            continue
        _profile_items.append((_item_id, _name))
    _profile_labels = [f"{_item_id}: {_name}" for _item_id, _name in _profile_items]
    profile_label_to_id = {label: _item_id for label, _item_id in zip(_profile_labels, [i[0] for i in _profile_items])}
    profile_select = mo.ui.dropdown(
        options=_profile_labels,
        value=_profile_labels[0] if _profile_labels else None,
        label="Profiles",
    )
    profile_select
    return profile_label_to_id, profile_select


@app.cell
def _():
    load_preset_button = mo.ui.run_button(label="Load Preset")
    load_profile_button = mo.ui.run_button(label="Load Profile")
    new_preset_button = mo.ui.run_button(label="New Preset")
    new_profile_button = mo.ui.run_button(label="New Profile")
    derive_from_preset_button = mo.ui.run_button(label="New Profile from Preset")
    derive_from_profile_button = mo.ui.run_button(label="New Profile from Profile")
    return (
        derive_from_preset_button,
        derive_from_profile_button,
        load_preset_button,
        load_profile_button,
        new_preset_button,
        new_profile_button,
    )


@app.cell
def _(
    derive_from_preset_button,
    derive_from_profile_button,
    load_preset_button,
    load_profile_button,
    new_preset_button,
    new_profile_button,
    preset_label_to_id,
    preset_select,
    profile_label_to_id,
    profile_select,
    set_editor_state,
):
    if load_preset_button.value:
        _preset_id = preset_label_to_id.get(preset_select.value)
        _preset = load_preset(_preset_id) if _preset_id else None
        if _preset:
            set_editor_state({"kind": "preset", "data": _preset, "source_id": _preset_id})

    if load_profile_button.value:
        _profile_id = profile_label_to_id.get(profile_select.value)
        _profile = load_profile(_profile_id) if _profile_id else None
        if _profile:
            set_editor_state({"kind": "profile", "data": _profile, "source_id": _profile_id})

    if new_preset_button.value:
        set_editor_state({"kind": "preset", "data": new_preset_template(), "source_id": None})

    if new_profile_button.value:
        set_editor_state({"kind": "profile", "data": new_profile_template(), "source_id": None})

    if derive_from_preset_button.value:
        _preset_id = preset_label_to_id.get(preset_select.value)
        _preset = load_preset(_preset_id) if _preset_id else None
        if _preset:
            _profile = new_profile_template()
            _profile["name"] = f"{_preset.get('name', 'Preset')} (derived)"
            _profile["channels"] = _preset.get("channels", json.loads(json.dumps(DEFAULT_CHANNELS)))
            _profile["derived_from_preset_id"] = _preset_id
            set_editor_state({"kind": "profile", "data": _profile, "source_id": None})

    if derive_from_profile_button.value:
        _profile_id = profile_label_to_id.get(profile_select.value)
        _profile = load_profile(_profile_id) if _profile_id else None
        if _profile:
            _derived = new_profile_template()
            _derived["name"] = f"{_profile.get('name', 'Profile')} (derived)"
            _derived["channels"] = _profile.get("channels", json.loads(json.dumps(DEFAULT_CHANNELS)))
            _derived["parent_profile_id"] = _profile_id
            _derived["derived_from_preset_id"] = _profile.get("derived_from_preset_id")
            _derived["mounting_context"] = _profile.get("mounting_context", "")
            set_editor_state({"kind": "profile", "data": _derived, "source_id": None})

    return


@app.cell
def _(
    derive_from_preset_button,
    derive_from_profile_button,
    load_preset_button,
    load_profile_button,
    new_preset_button,
    new_profile_button,
    preset_select,
    profile_select,
):
    left_panel = mo.vstack(
        [
            mo.md("## Load / Derive"),
            preset_select,
            load_preset_button,
            derive_from_preset_button,
            profile_select,
            load_profile_button,
            derive_from_profile_button,
            new_preset_button,
            new_profile_button,
        ]
    )
    left_panel
    return (left_panel,)


@app.cell
def _(editor_state):
    _current = editor_state()
    current_kind = _current.get("kind")
    current_data = _current.get("data", {})
    current_kind, current_data
    return current_data, current_kind


@app.cell
def _(current_data, current_kind):
    name_input = mo.ui.text(label="Name", value=current_data.get("name", ""))
    tags_input = mo.ui.text(
        label="Tags (comma separated)",
        value=", ".join(current_data.get("tags", [])),
    )
    notes_input = mo.ui.text_area(label="Notes", value=current_data.get("notes", ""))

    if current_kind == "profile":
        mounting_context_input = mo.ui.text(
            label="Mounting Context",
            value=current_data.get("mounting_context", ""),
        )
        parent_profile_id = current_data.get("parent_profile_id")
        derived_from_preset_id = current_data.get("derived_from_preset_id")
    else:
        mounting_context_input = None
        parent_profile_id = None
        derived_from_preset_id = None

    name_input, tags_input, notes_input, mounting_context_input, parent_profile_id, derived_from_preset_id
    return (
        derived_from_preset_id,
        mounting_context_input,
        name_input,
        notes_input,
        parent_profile_id,
        tags_input,
    )


@app.cell
def _(current_data):
    _channels = current_data.get("channels", {})
    _ch1 = _channels.get("1", {})
    _ch2 = _channels.get("2", {})

    ch1_gain = mo.ui.number(label="Ch 1 Gain (dB)", value=_ch1.get("gain_db", 0.0))
    ch1_delay = mo.ui.number(label="Ch 1 Delay (ms)", value=_ch1.get("delay_ms", 0.0))
    ch1_polarity = mo.ui.dropdown(
        options=["normal", "inverted"],
        value=_ch1.get("polarity", "normal"),
        label="Ch 1 Polarity",
    )
    ch1_peq = mo.ui.text_area(
        label="Ch 1 PEQ (JSON list)",
        value=json.dumps(_ch1.get("peq", []), indent=2),
    )
    ch1_crossover = mo.ui.text_area(
        label="Ch 1 Crossover (JSON)",
        value=json.dumps(_ch1.get("crossover", {}), indent=2),
    )
    ch1_limiters = mo.ui.text_area(
        label="Ch 1 Limiters (JSON)",
        value=json.dumps(_ch1.get("limiters", {}), indent=2),
    )
    ch1_routing = mo.ui.text_area(
        label="Ch 1 Routing (JSON)",
        value=json.dumps(_ch1.get("routing", {}), indent=2),
    )

    ch2_gain = mo.ui.number(label="Ch 2 Gain (dB)", value=_ch2.get("gain_db", 0.0))
    ch2_delay = mo.ui.number(label="Ch 2 Delay (ms)", value=_ch2.get("delay_ms", 0.0))
    ch2_polarity = mo.ui.dropdown(
        options=["normal", "inverted"],
        value=_ch2.get("polarity", "normal"),
        label="Ch 2 Polarity",
    )
    ch2_peq = mo.ui.text_area(
        label="Ch 2 PEQ (JSON list)",
        value=json.dumps(_ch2.get("peq", []), indent=2),
    )
    ch2_crossover = mo.ui.text_area(
        label="Ch 2 Crossover (JSON)",
        value=json.dumps(_ch2.get("crossover", {}), indent=2),
    )
    ch2_limiters = mo.ui.text_area(
        label="Ch 2 Limiters (JSON)",
        value=json.dumps(_ch2.get("limiters", {}), indent=2),
    )
    ch2_routing = mo.ui.text_area(
        label="Ch 2 Routing (JSON)",
        value=json.dumps(_ch2.get("routing", {}), indent=2),
    )

    ch1_panel = mo.vstack(
        [
            mo.md("### Channel 1"),
            ch1_gain,
            ch1_delay,
            ch1_polarity,
            ch1_peq,
            ch1_crossover,
            ch1_limiters,
            ch1_routing,
        ]
    )
    ch2_panel = mo.vstack(
        [
            mo.md("### Channel 2"),
            ch2_gain,
            ch2_delay,
            ch2_polarity,
            ch2_peq,
            ch2_crossover,
            ch2_limiters,
            ch2_routing,
        ]
    )

    center_panel = mo.vstack([mo.md("## Channel Settings"), mo.hstack([ch1_panel, ch2_panel])])
    center_panel

    return (
        ch1_crossover,
        ch1_delay,
        ch1_gain,
        ch1_limiters,
        ch1_peq,
        ch1_polarity,
        ch1_routing,
        ch2_crossover,
        ch2_delay,
        ch2_gain,
        ch2_limiters,
        ch2_peq,
        ch2_polarity,
        ch2_routing,
        center_panel,
    )


@app.cell
def _(current_kind, derived_from_preset_id, mounting_context_input, name_input, notes_input, parent_profile_id, tags_input):
    _meta_rows = [
        mo.md("## Metadata"),
        name_input,
        tags_input,
        notes_input,
    ]
    if current_kind == "profile":
        _meta_rows.append(mounting_context_input)
        _meta_rows.append(mo.md(f"Parent Profile: `{parent_profile_id}`"))
        _meta_rows.append(mo.md(f"Derived From Preset: `{derived_from_preset_id}`"))
    meta_panel = mo.vstack(_meta_rows)
    meta_panel
    return (meta_panel,)


@app.cell
def _(current_data, current_kind, data_root):
    if current_kind != "profile":
        add_json_button = None
        add_mdat_button = None
        json_browser = None
        mdat_browser = None
        links_table = None
    else:
        _measurement_links = current_data.get("measurement_links", [])

        json_browser = mo.ui.file_browser(
            initial_path=str(data_root / "json"),
            multiple=False,
        )
        mdat_browser = mo.ui.file_browser(
            initial_path=str(data_root / "mdat"),
            multiple=False,
        )
        add_json_button = mo.ui.run_button(label="Add JSON Link")
        add_mdat_button = mo.ui.run_button(label="Add MDAT Link")

        links_table = mo.ui.table(_measurement_links, label="Measurement Links")

    return add_json_button, add_mdat_button, json_browser, mdat_browser, links_table


@app.cell
def _(current_data, current_kind, data_root):
    if current_kind != "profile":
        remove_link_select = None
        remove_link_button = None
    else:
        remove_link_select = mo.ui.multiselect(
            options=[
                f"{i}: {_link.get('kind')} {_link.get('relative_path')}"
                for i, _link in enumerate(current_data.get("measurement_links", []))
            ],
            value=[],
            label="Remove links",
        )
        remove_link_button = mo.ui.run_button(label="Remove Selected Links")
    return remove_link_button, remove_link_select


@app.cell
def _(
    add_json_button,
    add_mdat_button,
    current_kind,
    json_browser,
    links_table,
    mdat_browser,
    remove_link_button,
    remove_link_select,
):
    if current_kind != "profile":
        links_panel = None
    else:
        links_panel = mo.vstack(
            [
                mo.md("## Measurement Links"),
                json_browser,
                add_json_button,
                mdat_browser,
                add_mdat_button,
                remove_link_select,
                remove_link_button,
                links_table,
            ]
        )
        links_panel
    return (links_panel,)


@app.cell
def _(
    add_json_button,
    add_mdat_button,
    current_kind,
    editor_state,
    json_browser,
    mdat_browser,
    remove_link_button,
    remove_link_select,
    set_editor_state,
):
    if current_kind == "profile":
        _data = dict(editor_state().get("data", {}))
        _links = list(_data.get("measurement_links", []))

        if add_json_button is not None and add_json_button.value:
            _path = json_browser.path(index=0)
            if _path:
                try:
                    _rel_path = str(Path(_path).resolve().relative_to(get_data_root())).replace("\\", "/")
                    _links.append({"kind": "json", "relative_path": _rel_path})
                except Exception:
                    pass

        if add_mdat_button is not None and add_mdat_button.value:
            _path = mdat_browser.path(index=0)
            if _path:
                try:
                    _rel_path = str(Path(_path).resolve().relative_to(get_data_root())).replace("\\", "/")
                    _links.append({"kind": "mdat", "relative_path": _rel_path})
                except Exception:
                    pass

        if remove_link_button is not None and remove_link_button.value and remove_link_select is not None:
            _remove_indices = []
            for _label in remove_link_select.value:
                try:
                    _idx = int(_label.split(":", 1)[0])
                    _remove_indices.append(_idx)
                except Exception:
                    pass
            _links = [_link for i, _link in enumerate(_links) if i not in _remove_indices]

        _data["measurement_links"] = _links
        set_editor_state({"kind": "profile", "data": _data, "source_id": editor_state().get("source_id")})


@app.cell
def _():
    change_note_input = mo.ui.text(label="Change note (for profile save)", value="")
    change_note_input
    return (change_note_input,)


@app.cell
def _():
    save_preset_button = mo.ui.run_button(label="Save Preset")
    save_profile_button = mo.ui.run_button(label="Update Profile")
    save_profile_as_new_button = mo.ui.run_button(label="Save as New Profile")
    export_button = mo.ui.run_button(label="Export LEA Settings")
    return export_button, save_preset_button, save_profile_as_new_button, save_profile_button


@app.cell
def _(command_map, current_kind):
    _ws_default = os.getenv("LEA_IP")
    if _ws_default:
        _ws_default = f"ws://{_ws_default}:1234"
    else:
        _ws_default = "ws://192.168.4.73:1234"
    lea_ws = mo.ui.text(label="LEA WebSocket Address", value=_ws_default)
    dry_run_toggle = mo.ui.checkbox(label="Dry run (preview payloads only)", value=True)
    mute_before_toggle = mo.ui.checkbox(label="Mute before apply", value=True)
    mute_after_toggle = mo.ui.checkbox(label="Unmute after apply", value=True)
    apply_button = mo.ui.run_button(label="Apply to LEA")
    return (
        apply_button,
        dry_run_toggle,
        lea_ws,
        mute_after_toggle,
        mute_before_toggle,
    )


@app.cell
def _():
    apply_result_state, set_apply_result_state = mo.state({})
    export_result_state, set_export_result_state = mo.state({})
    save_result_state, set_save_result_state = mo.state({})
    return apply_result_state, export_result_state, save_result_state, set_apply_result_state, set_export_result_state, set_save_result_state


@app.cell
def _(command_map):
    def _validate_value(value, mapping):
        if mapping is None:
            return "Missing mapping"
        if "enum" in mapping and mapping["enum"] is not None:
            if value not in mapping["enum"]:
                return f"Value {value} not in enum"
        if "range" in mapping and mapping["range"] is not None:
            try:
                val = float(value)
            except Exception:
                return "Value must be numeric"
            min_v = mapping["range"].get("min")
            max_v = mapping["range"].get("max")
            if min_v is not None and val < float(min_v):
                return f"Value {val} below min"
            if max_v is not None and val > float(max_v):
                return f"Value {val} above max"
        return ""

    def _validate_peq(bands, mapping):
        if not isinstance(bands, list):
            return "PEQ must be a list"
        band_schema = mapping.get("band_schema", {}) if isinstance(mapping, dict) else {}
        errors = []
        for idx, band in enumerate(bands):
            if not isinstance(band, dict):
                errors.append(f"Band {idx} must be an object")
                continue
            for key, limits in band_schema.items():
                if key not in band:
                    continue
                value = band.get(key)
                if isinstance(limits, dict) and ("min" in limits or "max" in limits):
                    try:
                        val = float(value)
                        if "min" in limits and val < float(limits["min"]):
                            errors.append(f"Band {idx} {key} below min")
                        if "max" in limits and val > float(limits["max"]):
                            errors.append(f"Band {idx} {key} above max")
                    except Exception:
                        errors.append(f"Band {idx} {key} must be numeric")
                elif isinstance(limits, list):
                    if value not in limits:
                        errors.append(f"Band {idx} {key} not in enum")
        return "; ".join(errors)

    def build_lea_payloads(channels, command_map):
        payloads = []
        skipped = []
        errors = []
        request_id = 1
        channel_map = command_map.get("channels", {}) if isinstance(command_map, dict) else {}

        for ch, ch_data in channels.items():
            if not isinstance(ch_data, dict):
                continue
            for field, value in ch_data.items():
                mapping = channel_map.get(field)
                if not mapping or not mapping.get("supported"):
                    skipped.append({"channel": ch, "field": field, "reason": "unsupported"})
                    continue
                url = mapping.get("url", "").format(channel=ch)
                param = mapping.get("param")
                if not url or not param:
                    skipped.append({"channel": ch, "field": field, "reason": "missing mapping"})
                    continue
                if field == "peq":
                    err = _validate_peq(value, mapping)
                    if err:
                        errors.append({"channel": ch, "field": field, "error": err})
                        continue
                else:
                    err = _validate_value(value, mapping)
                    if err:
                        errors.append({"channel": ch, "field": field, "error": err})
                        continue
                payloads.append(
                    {
                        "leaApi": "1.0",
                        "url": url,
                        "method": mapping.get("method", "set"),
                        "params": {param: value},
                        "id": request_id,
                    }
                )
                request_id += 1
        return payloads, skipped, errors

    return build_lea_payloads

@app.cell
def _(
    apply_button,
    build_channels_from_ui,
    build_lea_payloads,
    ch1_crossover,
    ch1_delay,
    ch1_gain,
    ch1_limiters,
    ch1_peq,
    ch1_polarity,
    ch1_routing,
    ch2_crossover,
    ch2_delay,
    ch2_gain,
    ch2_limiters,
    ch2_peq,
    ch2_polarity,
    ch2_routing,
    command_map,
    dry_run_toggle,
    lea_ws,
    mute_after_toggle,
    mute_before_toggle,
    set_apply_result_state,
):
    mo.stop(not apply_button.value)

    _channels, _parse_errors = build_channels_from_ui(
        ch1_gain.value,
        ch1_delay.value,
        ch1_polarity.value,
        ch1_peq.value,
        ch1_crossover.value,
        ch1_limiters.value,
        ch1_routing.value,
        ch2_gain.value,
        ch2_delay.value,
        ch2_polarity.value,
        ch2_peq.value,
        ch2_crossover.value,
        ch2_limiters.value,
        ch2_routing.value,
    )

    _payloads, _skipped, _errors = build_lea_payloads(_channels, command_map)
    _errors.extend([{"channel": None, "field": "json", "error": e} for e in _parse_errors])

    _ws_address = lea_ws.value.strip()
    if not _ws_address:
        _errors.append({"channel": None, "field": "ws", "error": "WebSocket address required"})

    _mute_payloads = []
    _mute_mapping = command_map.get("channels", {}).get("mute", {}) if isinstance(command_map, dict) else {}
    _mute_supported = bool(_mute_mapping.get("supported"))
    _mute_url = _mute_mapping.get("url", "")
    _mute_param = _mute_mapping.get("param", "mute")
    _mute_method = _mute_mapping.get("method", "set")

    if mute_before_toggle.value and _mute_supported and _mute_url and _mute_param:
        for _ch in ("1", "2"):
            _mute_payloads.append(
                {
                    "leaApi": "1.0",
                    "url": _mute_url.format(channel=_ch),
                    "method": _mute_method,
                    "params": {_mute_param: True},
                    "id": 900 + int(_ch),
                }
            )

    _unmute_payloads = []
    if mute_after_toggle.value and _mute_supported and _mute_url and _mute_param:
        for _ch in ("1", "2"):
            _unmute_payloads.append(
                {
                    "leaApi": "1.0",
                    "url": _mute_url.format(channel=_ch),
                    "method": _mute_method,
                    "params": {_mute_param: False},
                    "id": 910 + int(_ch),
                }
            )

    if _errors:
        set_apply_result_state(
            {
                "status": "failed",
                "errors": _errors,
                "payloads": _payloads,
                "skipped": _skipped,
                "dry_run": True,
            }
        )
    elif dry_run_toggle.value:
        set_apply_result_state(
            {
                "status": "dry_run",
                "payloads": _mute_payloads + _payloads + _unmute_payloads,
                "skipped": _skipped,
                "dry_run": True,
            }
        )
    else:
        lea = Lea_Settings()
        _responses = []
        _responses.extend(lea.send_batch(_ws_address, _mute_payloads))
        _responses.extend(lea.send_batch(_ws_address, _payloads))
        _responses.extend(lea.send_batch(_ws_address, _unmute_payloads))

        set_apply_result_state(
            {
                "status": "sent",
                "payloads": _mute_payloads + _payloads + _unmute_payloads,
                "responses": _responses,
                "skipped": _skipped,
                "dry_run": False,
            }
        )


@app.cell
def _(
    apply_result_state,
    command_map_error,
    command_map_path,
    dry_run_toggle,
    lea_ws,
    mute_after_toggle,
    mute_before_toggle,
):
    _apply_state = apply_result_state()
    _info_lines = [
        f"Command map: `{command_map_path}`",
    ]
    if command_map_error:
        _info_lines.append(f"Command map warning: {command_map_error}")

    controls_panel = mo.vstack(
        [
            mo.md("## LEA Apply"),
            lea_ws,
            dry_run_toggle,
            mute_before_toggle,
            mute_after_toggle,
            mo.md("  ".join(_info_lines)),
        ]
    )

    if _apply_state:
        _status = _apply_state.get("status")
        if _status == "failed":
            status_md = mo.md(f"Apply failed: `{_apply_state.get('errors')}`")
        elif _status == "dry_run":
            status_md = mo.md("Dry run complete. Payloads generated.")
        else:
            status_md = mo.md("Commands sent to LEA.")
    else:
        status_md = mo.md("Apply status: idle")

    controls_panel, status_md
    return controls_panel, status_md


@app.cell
def _(
    build_channels_from_ui,
    change_note_input,
    ch1_crossover,
    ch1_delay,
    ch1_gain,
    ch1_limiters,
    ch1_peq,
    ch1_polarity,
    ch1_routing,
    ch2_crossover,
    ch2_delay,
    ch2_gain,
    ch2_limiters,
    ch2_peq,
    ch2_polarity,
    ch2_routing,
    current_kind,
    editor_state,
    name_input,
    notes_input,
    save_preset_button,
    save_profile_as_new_button,
    save_profile_button,
    set_editor_state,
    set_save_result_state,
    tags_input,
    mounting_context_input,
):
    mo.stop(not (save_preset_button.value or save_profile_button.value or save_profile_as_new_button.value))

    _channels, _parse_errors = build_channels_from_ui(
        ch1_gain.value,
        ch1_delay.value,
        ch1_polarity.value,
        ch1_peq.value,
        ch1_crossover.value,
        ch1_limiters.value,
        ch1_routing.value,
        ch2_gain.value,
        ch2_delay.value,
        ch2_polarity.value,
        ch2_peq.value,
        ch2_crossover.value,
        ch2_limiters.value,
        ch2_routing.value,
    )

    _tags = [t.strip() for t in (tags_input.value or "").split(",") if t.strip()]

    if current_kind == "preset" and save_preset_button.value:
        _data = dict(editor_state().get("data", {}))
        _data.update(
            {
                "name": name_input.value,
                "tags": _tags,
                "notes": notes_input.value,
                "channels": _channels,
            }
        )
        _errors, _cleaned = save_preset(_data)
        _errors.extend(_parse_errors)
        set_save_result_state({"status": "saved_preset", "errors": _errors, "item": _cleaned})
        set_editor_state({"kind": "preset", "data": _cleaned, "source_id": _cleaned.get("id")})

    elif current_kind == "profile" and (save_profile_button.value or save_profile_as_new_button.value):
        _data = dict(editor_state().get("data", {}))
        if save_profile_as_new_button.value:
            _data["id"] = str(uuid.uuid4())
            _data["created_at"] = datetime.now().isoformat(timespec="seconds")
        _data.update(
            {
                "name": name_input.value,
                "tags": _tags,
                "notes": notes_input.value,
                "channels": _channels,
            }
        )
        if mounting_context_input is not None:
            _data["mounting_context"] = mounting_context_input.value
        if change_note_input.value.strip():
            _data.setdefault("change_log", []).append(
                {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "note": change_note_input.value.strip(),
                    "diff": {},
                }
            )
        _errors, _cleaned = save_profile(_data)
        _errors.extend(_parse_errors)
        set_save_result_state({"status": "saved_profile", "errors": _errors, "item": _cleaned})
        set_editor_state({"kind": "profile", "data": _cleaned, "source_id": _cleaned.get("id")})


@app.cell
def _(
    export_button,
    set_export_result_state,
    command_map,
    build_channels_from_ui,
    build_lea_payloads,
    ch1_crossover,
    ch1_delay,
    ch1_gain,
    ch1_limiters,
    ch1_peq,
    ch1_polarity,
    ch1_routing,
    ch2_crossover,
    ch2_delay,
    ch2_gain,
    ch2_limiters,
    ch2_peq,
    ch2_polarity,
    ch2_routing,
    current_kind,
    editor_state,
):
    mo.stop(not export_button.value)

    _channels, _parse_errors = build_channels_from_ui(
        ch1_gain.value,
        ch1_delay.value,
        ch1_polarity.value,
        ch1_peq.value,
        ch1_crossover.value,
        ch1_limiters.value,
        ch1_routing.value,
        ch2_gain.value,
        ch2_delay.value,
        ch2_polarity.value,
        ch2_peq.value,
        ch2_crossover.value,
        ch2_limiters.value,
        ch2_routing.value,
    )

    _payloads, _skipped, _errors = build_lea_payloads(_channels, command_map)
    _errors.extend([{"channel": None, "field": "json", "error": e} for e in _parse_errors])

    _export_payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_kind": current_kind,
        "source_id": editor_state().get("source_id"),
        "name": editor_state().get("data", {}).get("name"),
        "channels": _channels,
        "payloads": _payloads,
        "skipped": _skipped,
        "errors": _errors,
    }

    _export_dir = get_tuning_exports_dir()
    _export_dir.mkdir(parents=True, exist_ok=True)
    _export_name = f"lea_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    _export_path = _export_dir / _export_name
    _export_path.write_text(json.dumps(_export_payload, indent=2), encoding="utf-8")

    set_export_result_state({"path": str(_export_path), "errors": _errors})


@app.cell
def _(apply_button, controls_panel, export_button, export_result_state, save_preset_button, save_profile_as_new_button, save_profile_button, save_result_state, status_md):
    action_panel = mo.vstack(
        [
            mo.md("## Actions"),
            save_preset_button,
            save_profile_button,
            save_profile_as_new_button,
            export_button,
            apply_button,
            status_md,
        ]
    )

    _save_state = save_result_state()
    _export_state = export_result_state()
    _feedback_lines = []
    if _save_state:
        _feedback_lines.append(f"Save: {_save_state.get('status')} errors={_save_state.get('errors')}")
    if _export_state:
        _feedback_lines.append(f"Exported: {_export_state.get('path')}")
    feedback_panel = mo.md("  ".join(_feedback_lines) if _feedback_lines else "")

    action_panel, feedback_panel
    return action_panel, feedback_panel


@app.cell
def _(current_data, current_kind):
    _parent = None
    if current_kind != "profile":
        compare_panel = mo.md("Profile comparison available when editing a profile.")
    else:
        _parent_id = current_data.get("parent_profile_id")
        if not _parent_id:
            compare_panel = mo.md("No parent profile set.")
        else:
            _parent = load_profile(_parent_id)
            if not _parent:
                compare_panel = mo.md("Parent profile not found.")
            else:
                _diffs = []
                for _ch in ("1", "2"):
                    _pch = _parent.get("channels", {}).get(_ch, {})
                    _cch = current_data.get("channels", {}).get(_ch, {})
                    for key in ("gain_db", "delay_ms", "polarity", "peq", "crossover", "limiters", "routing"):
                        if _pch.get(key) != _cch.get(key):
                            _diffs.append(
                                f"ch{_ch} {key}: {_pch.get(key)} -> {_cch.get(key)}"
                            )

                if not _diffs:
                    compare_panel = mo.md("No differences from parent.")
                else:
                    diff_md = "\n".join([f"- {d}" for d in _diffs])
                    compare_panel = mo.md(f"## Compare to Parent\n{diff_md}")

    return compare_panel, _parent


@app.cell
def _(action_panel, center_panel, compare_panel, controls_panel, left_panel, links_panel, meta_panel):
    _right_items = [meta_panel, links_panel, compare_panel]
    _right_items = [_item for _item in _right_items if _item is not None]
    _right_column = mo.vstack(_right_items) if _right_items else mo.md("")

    layout = mo.hstack(
        [
            mo.vstack([left_panel, controls_panel, action_panel]),
            center_panel,
            _right_column,
        ]
    )
    layout
    return (layout,)


if __name__ == "__main__":
    app.run()
