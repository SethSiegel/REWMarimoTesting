# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.19.0",
#     "psycopg[binary]==3.3.2",
#     "matplotlib==3.10.8",
#     "pyzmq>=27.1.0",
#     "numpy>=2.0.0",
#     "plotly>=5.22.0",
# ]
# [tool.marimo.opengraph]
# title = "REW Statistical Analysis Dashboard"
# description = "Build tolerance curves and statistical summaries from JSON measurements in Postgres."
# ///

import marimo

__generated_with = "0.19.11"
app = marimo.App(app_title="REW Statistical Analysis Dashboard")


with app.setup:
    import sys
    import pathlib
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    import os
    import json
    from datetime import datetime
    import psycopg
    import numpy as np
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import marimo as mo
    from project_paths import get_data_root


@app.cell
def _():
    mo.md(
        r"""
    # REW Statistical Analysis Dashboard
    Analyze JSON measurement sets from Postgres and build tolerance-band views.
    """
    )
    return


@app.cell
def _():
    mo.md(
        r"""
    ## Database Connection
    Loads JSON-linked measurement records from Postgres.
    """
    )
    return


@app.cell
def _():
    ana_db_host = mo.ui.text(label="Host", value=os.getenv("POSTGRES_HOST", "localhost"))
    ana_db_port = mo.ui.text(label="Port", value=os.getenv("POSTGRES_PORT", "5432"))
    ana_db_name = mo.ui.text(label="Database", value=os.getenv("POSTGRES_DB", "testingdb-postgres"))
    ana_db_user = mo.ui.text(label="User", value=os.getenv("POSTGRES_USER", "rew_app"))
    ana_db_pass = mo.ui.text(label="Password", value=os.getenv("POSTGRES_PASSWORD", ""))
    ana_db_host, ana_db_port, ana_db_name, ana_db_user, ana_db_pass
    return ana_db_host, ana_db_name, ana_db_pass, ana_db_port, ana_db_user


@app.cell
def _():
    ana_load_button = mo.ui.run_button(label="Load JSON Records From Database")
    ana_load_button
    return (ana_load_button,)


@app.cell
def _():
    ana_records_state, ana_set_records_state = mo.state([])
    ana_loaded_at_state, ana_set_loaded_at_state = mo.state(None)
    ana_load_status_state, ana_set_load_status_state = mo.state("idle")
    ana_load_error_state, ana_set_load_error_state = mo.state("")
    ana_load_diag_state, ana_set_load_diag_state = mo.state({})
    return (
        ana_load_error_state,
        ana_load_diag_state,
        ana_load_status_state,
        ana_loaded_at_state,
        ana_records_state,
        ana_set_load_error_state,
        ana_set_load_diag_state,
        ana_set_load_status_state,
        ana_set_loaded_at_state,
        ana_set_records_state,
    )


@app.cell
def _(
    ana_db_host,
    ana_db_name,
    ana_db_pass,
    ana_db_port,
    ana_db_user,
    ana_load_button,
    ana_set_load_error_state,
    ana_set_load_diag_state,
    ana_set_load_status_state,
    ana_set_loaded_at_state,
    ana_set_records_state,
):
    mo.stop(not ana_load_button.value, mo.md("Click **Load JSON Records From Database** to begin."))

    _records = []
    _load_status = "ok"
    _load_error = ""
    _load_diag = {}
    _conn = None
    with mo.status.spinner(title="Loading JSON records from Postgres..."):
        try:
            _conn = psycopg.connect(
                host=ana_db_host.value.strip(),
                port=int(ana_db_port.value.strip()),
                dbname=ana_db_name.value.strip(),
                user=ana_db_user.value.strip(),
                password=ana_db_pass.value,
                connect_timeout=5,
                options="-c statement_timeout=12000 -c lock_timeout=3000",
            )
            _conn.autocommit = True
            _query = """
                SELECT
                    COALESCE(m.title, '') AS title,
                    f.id AS file_id,
                    m.id AS measurement_id,
                    COALESCE(m.unit_type, '') AS unit_type,
                    COALESCE(m.unit_number, '') AS unit_number,
                    COALESCE(to_jsonb(m) ->> 'parent_mdat', '') AS parent_mdat,
                    m.measured_at,
                    COALESCE(f.relative_path, '') AS relative_path,
                    COALESCE(h.base_url, '') AS base_url
                FROM measurement_file f
                LEFT JOIN measurement m ON f.measurement_id = m.id
                LEFT JOIN file_host h ON h.id = f.host_id
                WHERE
                    LOWER(COALESCE(f.kind, '')) = 'json'
                    OR LOWER(COALESCE(f.relative_path, '')) LIKE '%.json'
                ORDER BY f.created_at DESC
                LIMIT 1500
            """
            with _conn.cursor() as _cur:
                _cur.execute(
                    """
                    SELECT
                        COUNT(*) AS total_files,
                        COUNT(*) FILTER (
                            WHERE LOWER(COALESCE(kind, '')) = 'json'
                        ) AS kind_json_files,
                        COUNT(*) FILTER (
                            WHERE LOWER(COALESCE(relative_path, '')) LIKE '%.json'
                        ) AS path_json_files
                    FROM measurement_file
                    """
                )
                _diag_row = _cur.fetchone()
                _load_diag = {
                    "total_files": int(_diag_row[0] or 0),
                    "kind_json_files": int(_diag_row[1] or 0),
                    "path_json_files": int(_diag_row[2] or 0),
                }
                _cur.execute(_query)
                _rows = _cur.fetchall()
                _cols = [d.name for d in _cur.description]
            for _row in _rows:
                _record = dict(zip(_cols, _row))
                for _k, _v in _record.items():
                    if _v is None:
                        _record[_k] = ""
                _records.append(_record)
        except Exception as _db_exc:
            _load_status = "error"
            _load_error = str(_db_exc)
        finally:
            if _conn is not None:
                _conn.close()

    ana_set_records_state(_records)
    ana_set_loaded_at_state(datetime.now())
    ana_set_load_status_state(_load_status)
    ana_set_load_error_state(_load_error)
    ana_set_load_diag_state(_load_diag)
    return


@app.cell
def _(
    ana_load_diag_state,
    ana_load_error_state,
    ana_load_status_state,
    ana_loaded_at_state,
    ana_records_state,
):
    _loaded_at = ana_loaded_at_state()
    _count = len(ana_records_state())
    _diag = ana_load_diag_state()
    if _loaded_at is None:
        mo.md("No records loaded yet.")
    elif ana_load_status_state() == "error":
        mo.md(
            "Load failed.  "
            f"\nError: `{ana_load_error_state()}`  "
            f"\nLast attempted at `{_loaded_at.strftime('%Y-%m-%d %H:%M:%S')}`"
        )
    else:
        mo.md(
            f"Loaded `{_count}` JSON records at `{_loaded_at.strftime('%Y-%m-%d %H:%M:%S')}`.  "
            f"\nDiagnostics: total files=`{_diag.get('total_files', 0)}`, "
            f"kind=json=`{_diag.get('kind_json_files', 0)}`, "
            f"path ends .json=`{_diag.get('path_json_files', 0)}`"
        )
    return


@app.cell
def _():
    mo.md(
        r"""
    ## JSON Records
    Filter by MDAT name and source folder, then choose records for analysis.
    """
    )
    return


@app.cell
def _(ana_records_state):
    _folders = set()
    for _record in ana_records_state():
        _relative_path = str(_record.get("relative_path") or "").strip()
        _relative_parent = pathlib.Path(_relative_path).parent.as_posix() if _relative_path else ""
        _folder = "" if _relative_parent == "." else _relative_parent
        _folders.add(_folder)

    _folder_options = ["All folders"]
    _folder_options.extend(sorted(f if f else "(root)" for f in _folders))
    ana_folder_dropdown = mo.ui.dropdown(
        options=_folder_options,
        value="All folders",
        label="Folder",
    )
    return (ana_folder_dropdown,)


@app.cell
def _():
    ana_mdat_filter = mo.ui.text(label="MDAT filter", value="")
    ana_folder_filter = mo.ui.text(label="Folder filter", value="")
    ana_suffix_filter = mo.ui.dropdown(
        options=["All", "Ends with -1", "Ends with -2", "Ends with -1 or -2"],
        value="All",
        label="Title suffix",
    )
    return ana_folder_filter, ana_mdat_filter, ana_suffix_filter


@app.cell
def _(ana_folder_dropdown, ana_folder_filter, ana_mdat_filter, ana_suffix_filter):
    mo.vstack(
        [
            mo.hstack([ana_mdat_filter, ana_suffix_filter], justify="start", gap=1),
            mo.hstack([ana_folder_dropdown, ana_folder_filter], justify="start", gap=1),
        ],
        gap=0.6,
    )
    return


@app.cell
def _():
    mo.md(
        r"""
    **Selection workflow**
    1. Filter records by MDAT/folder.
    2. Use the selector below to choose records for analysis.
    3. Confirm selection in the "Selected Records" table.
    """
    )
    return


@app.cell
def _(ana_folder_dropdown, ana_folder_filter, ana_mdat_filter, ana_records_state, ana_suffix_filter):
    _records = ana_records_state()
    _mdat_query = ana_mdat_filter.value.strip().lower()
    _folder_query = ana_folder_filter.value.strip().lower()
    _folder_dropdown_value = (ana_folder_dropdown.value or "All folders").strip()
    _folder_dropdown_target = "" if _folder_dropdown_value == "(root)" else _folder_dropdown_value
    _suffix_choice = (ana_suffix_filter.value or "All").strip()
    ana_filtered_records = []

    for _record in _records:
        _relative_path = str(_record.get("relative_path") or "").strip()
        _relative_parent = pathlib.Path(_relative_path).parent.as_posix() if _relative_path else ""
        _folder = "" if _relative_parent == "." else _relative_parent
        _parent_mdat = str(_record.get("parent_mdat") or "").strip()
        _title = str(_record.get("title") or "").strip()

        if _mdat_query and _mdat_query not in _parent_mdat.lower():
            continue
        if _folder_dropdown_value != "All folders" and _folder != _folder_dropdown_target:
            continue
        if _folder_query and _folder_query not in _folder.lower():
            continue
        if _suffix_choice != "All":
            _title_lower = _title.lower()
            if _suffix_choice == "Ends with -1" and not _title_lower.endswith("-1"):
                continue
            if _suffix_choice == "Ends with -2" and not _title_lower.endswith("-2"):
                continue
            if _suffix_choice == "Ends with -1 or -2" and not (
                _title_lower.endswith("-1") or _title_lower.endswith("-2")
            ):
                continue

        _enriched_record = dict(_record)
        _enriched_record["_folder"] = _folder
        _enriched_record["_parent_mdat"] = _parent_mdat
        _enriched_record["_title"] = _title
        ana_filtered_records.append(_enriched_record)

    ana_filtered_records.sort(
        key=lambda r: (
            str(r.get("_parent_mdat", "")).lower(),
            str(r.get("_title", "")).lower(),
            str(r.get("file_id", "")),
        )
    )
    return (ana_filtered_records,)


@app.cell
def _(ana_filtered_records):
    ana_record_items = []
    for _r in ana_filtered_records:
        _file_id = _r.get("file_id")
        if not _file_id:
            continue
        _title = _r.get("_title") or "(untitled)"
        _unit_type = _r.get("unit_type") or "?"
        _unit_number = _r.get("unit_number") or "?"
        _parent = _r.get("_parent_mdat") or "-"
        _folder = _r.get("_folder") or "-"
        _label = f"{_title} | MDAT:{_parent} | FILE:{_file_id}"
        ana_record_items.append((_label, _r))

    ana_record_items.sort(key=lambda x: x[0])
    ana_record_label_to_record = {lbl: rec for lbl, rec in ana_record_items}
    ana_record_select = mo.ui.multiselect(
        options=[lbl for lbl, _ in ana_record_items],
        value=[],
        label="Select records for statistical analysis (multi-select)",
    )
    ana_record_select
    return ana_record_items, ana_record_label_to_record, ana_record_select


@app.cell
def _(ana_record_items, ana_record_label_to_record, ana_record_select):
    ana_selected_records = [
        ana_record_label_to_record[lbl]
        for lbl in ana_record_select.value
        if lbl in ana_record_label_to_record
    ]
    ana_selection_status_md = mo.md(
        f"Selected `{len(ana_selected_records)}` of `{len(ana_record_items)}` filtered records."
    )
    ana_selection_status_md
    return (ana_selected_records,)


@app.cell
def _(ana_selected_records):
    _selected_rows = []
    for _record in ana_selected_records:
        _selected_rows.append(
            {
                "mdat_name": _record.get("_parent_mdat", ""),
                "measurement_title": _record.get("_title", ""),
                "folder": _record.get("_folder", ""),
                "file_id": _record.get("file_id", ""),
                "measurement_id": _record.get("measurement_id", ""),
            }
        )
    _selected_tbl = mo.ui.table(_selected_rows, label="Selected Records")
    _selected_tbl
    return


@app.cell
def _():
    mo.md(
        r"""
    ## Analysis Controls
    Configure tolerance-band and statistical analysis.
    """
    )
    return


@app.cell
def _():
    _bench_options = ["None"]
    bench_path_map = {}
    _shared_root = get_data_root()
    _local_root = repo_root / "data"
    for _root in (_shared_root, _local_root):
        _bench_dir = _root / "benchmarks"
        if not (_bench_dir.exists() and _bench_dir.is_dir()):
            continue
        for _path in sorted(_bench_dir.glob("*.json")):
            _label = _path.name
            if _label not in bench_path_map:
                bench_path_map[_label] = _path
                _bench_options.append(_label)

    ana_benchmark_select = mo.ui.dropdown(
        options=_bench_options,
        value="None",
        label="Benchmark overlay",
    )
    ana_benchmark_select
    return ana_benchmark_select, bench_path_map


@app.cell
def _():
    ana_tol_db = mo.ui.number(start=0.1, stop=24.0, step=0.1, value=3.0, label="Tolerance (dB)")
    ana_min_hz = mo.ui.number(start=10.0, stop=1000.0, step=1.0, value=20.0, label="Min Freq (Hz)")
    ana_max_hz = mo.ui.number(start=200.0, stop=40000.0, step=10.0, value=20000.0, label="Max Freq (Hz)")
    ana_ppo = mo.ui.number(start=3, stop=96, step=1, value=24, label="Points/Octave")
    ana_band_select = mo.ui.dropdown(
        options=[
            "Full Range",
            "Sub-bass (20-60 Hz)",
            "Bass (60-250 Hz)",
            "Low-mid (250-500 Hz)",
            "Mid (500-2000 Hz)",
            "Upper-mid (2000-4000 Hz)",
            "Presence (4000-6000 Hz)",
            "Brilliance (6000-20000 Hz)",
        ],
        value="Full Range",
        label="Frequency Band",
    )
    ana_run_button = mo.ui.run_button(label="Run Statistical Analysis")
    ana_tol_db, ana_min_hz, ana_max_hz, ana_ppo, ana_band_select, ana_run_button
    return ana_band_select, ana_max_hz, ana_min_hz, ana_ppo, ana_run_button, ana_tol_db


@app.cell
def _():
    ana_result_state, ana_set_result_state = mo.state(None)
    return ana_result_state, ana_set_result_state


@app.cell
def _(
    bench_path_map,
    ana_benchmark_select,
    ana_band_select,
    ana_max_hz,
    ana_min_hz,
    ana_ppo,
    ana_run_button,
    ana_selected_records,
    ana_load_status_state,
    ana_loaded_at_state,
    ana_set_result_state,
    ana_tol_db,
):
    mo.stop(not ana_run_button.value, mo.md("Click **Run Statistical Analysis** to start."))
    if ana_loaded_at_state() is None:
        ana_set_result_state(None)
        mo.stop(True, mo.md("No database records loaded. Click **Load JSON Records From Database** first."))
    if ana_load_status_state() == "error":
        ana_set_result_state(None)
        mo.stop(True, mo.md("Database load failed. Reconnect and click **Load JSON Records From Database**."))
    if not ana_selected_records:
        ana_set_result_state(None)
        mo.stop(True, mo.md("Select at least one JSON record."))

    _data_root = get_data_root()
    _local_root = repo_root / "data"
    _load_errors = []
    _curve_data = []

    for _record in ana_selected_records:
        _relative = str(_record.get("relative_path") or "").strip()
        _base_url = str(_record.get("base_url") or "").strip()
        _title = str(_record.get("title") or _relative or f"file_{_record.get('file_id')}")

        _candidates = []
        if _relative:
            _relative_path = pathlib.Path(_relative)
            if _relative_path.is_absolute():
                _candidates.append(_relative_path)
            _candidates.append(_data_root / _relative_path)
            _candidates.append(_local_root / _relative_path)
        if _base_url and _relative:
            _candidates.append(pathlib.Path(_base_url) / pathlib.Path(_relative))

        _existing_path = None
        for _p in _candidates:
            if _p.exists() and _p.is_file():
                _existing_path = _p
                break

        if _existing_path is None:
            _load_errors.append(f"{_title}: file not found (relative_path={_relative})")
            continue

        try:
            _payload = json.loads(_existing_path.read_text(encoding="utf-8"))
        except Exception as _read_exc:
            _load_errors.append(f"{_title}: read error ({_read_exc})")
            continue

        _freq = _payload.get("Freq(Hz)", [])
        _spl = _payload.get("SPL(dB)", [])
        if not isinstance(_freq, list) or not isinstance(_spl, list):
            _load_errors.append(f"{_title}: invalid JSON schema")
            continue
        if len(_freq) < 2 or len(_freq) != len(_spl):
            _load_errors.append(f"{_title}: invalid data lengths")
            continue

        _freq_np = np.asarray(_freq, dtype=float)
        _spl_np = np.asarray(_spl, dtype=float)
        _valid_mask = np.isfinite(_freq_np) & np.isfinite(_spl_np) & (_freq_np > 0)
        _freq_np = _freq_np[_valid_mask]
        _spl_np = _spl_np[_valid_mask]
        if _freq_np.size < 2:
            _load_errors.append(f"{_title}: not enough valid points")
            continue

        _order = np.argsort(_freq_np)
        _freq_sorted = _freq_np[_order]
        _spl_sorted = _spl_np[_order]
        _freq_unique, _unique_idx = np.unique(_freq_sorted, return_index=True)
        _spl_unique = _spl_sorted[_unique_idx]
        if _freq_unique.size < 2:
            _load_errors.append(f"{_title}: not enough unique freq points")
            continue

        _curve_data.append(
            {
                "title": _title,
                "freq": _freq_unique,
                "spl": _spl_unique,
                "source_path": str(_existing_path),
            }
        )

    if not _curve_data:
        ana_set_result_state(None)
        mo.stop(
            True,
            mo.md("No valid curves loaded. Check selected records and file paths."),
        )

    _user_min = float(ana_min_hz.value)
    _user_max = float(ana_max_hz.value)
    _min_overlap = max(float(np.min(c["freq"])) for c in _curve_data)
    _max_overlap = min(float(np.max(c["freq"])) for c in _curve_data)
    _band_label = (ana_band_select.value or "Full Range").strip()
    _band_min = None
    _band_max = None
    _band_map = {
        "Sub-bass (20-60 Hz)": (20.0, 60.0),
        "Bass (60-250 Hz)": (60.0, 250.0),
        "Low-mid (250-500 Hz)": (250.0, 500.0),
        "Mid (500-2000 Hz)": (500.0, 2000.0),
        "Upper-mid (2000-4000 Hz)": (2000.0, 4000.0),
        "Presence (4000-6000 Hz)": (4000.0, 6000.0),
        "Brilliance (6000-20000 Hz)": (6000.0, 20000.0),
    }
    if _band_label in _band_map:
        _band_min, _band_max = _band_map[_band_label]

    _analysis_min = max(_user_min, _min_overlap)
    _analysis_max = min(_user_max, _max_overlap)
    if _band_min is not None and _band_max is not None:
        _analysis_min = max(_analysis_min, _band_min)
        _analysis_max = min(_analysis_max, _band_max)
    if _analysis_max <= _analysis_min:
        ana_set_result_state(None)
        mo.stop(
            True,
            mo.md("No overlapping frequency range across selected curves."),
        )

    _benchmark_label = None
    _benchmark_curve = None
    _benchmark_warning = None
    _selected_benchmark = (ana_benchmark_select.value or "").strip()
    if _selected_benchmark and _selected_benchmark != "None":
        _benchmark_label = _selected_benchmark
        _bench_path = bench_path_map.get(_selected_benchmark)
        if _bench_path is None or not _bench_path.exists():
            _benchmark_warning = f"Benchmark '{_selected_benchmark}' not found."
        else:
            try:
                _bench_payload = json.loads(_bench_path.read_text(encoding="utf-8"))
                _bench_freq = _bench_payload.get("Freq(Hz)", [])
                _bench_spl = _bench_payload.get("SPL(dB)", [])
                if not isinstance(_bench_freq, list) or not isinstance(_bench_spl, list):
                    _benchmark_warning = (
                        f"Benchmark '{_selected_benchmark}' is missing Freq(Hz)/SPL(dB)."
                    )
                else:
                    _bench_freq_np = np.asarray(_bench_freq, dtype=float) if _bench_freq else np.array([])
                    _bench_spl_np = np.asarray(_bench_spl, dtype=float) if _bench_spl else np.array([])

                    # If lengths mismatch, attempt reconstruction using Meta Data.
                    if _bench_freq_np.size != _bench_spl_np.size:
                        _meta = _bench_payload.get("Meta Data") if isinstance(_bench_payload, dict) else {}
                        _start = None
                        _end = None
                        if isinstance(_meta, dict):
                            _start = _meta.get("Start Frequency")
                            _end = _meta.get("End Frequency")
                        if _start is not None and _end is not None and _bench_spl_np.size >= 2:
                            try:
                                _start_f = float(_start)
                                _end_f = float(_end)
                                if _start_f > 0 and _end_f > _start_f:
                                    _bench_freq_np = np.geomspace(
                                        _start_f,
                                        _end_f,
                                        int(_bench_spl_np.size),
                                    )
                                    _benchmark_warning = (
                                        f"Benchmark '{_selected_benchmark}' had mismatched lengths; "
                                        "reconstructed frequency grid from metadata."
                                    )
                                else:
                                    _benchmark_warning = (
                                        f"Benchmark '{_selected_benchmark}' has invalid metadata frequency range."
                                    )
                            except Exception:
                                _benchmark_warning = (
                                    f"Benchmark '{_selected_benchmark}' could not rebuild frequency grid."
                                )
                        else:
                            _benchmark_warning = (
                                f"Benchmark '{_selected_benchmark}' has mismatched lengths and no usable metadata."
                            )

                    # If we have a shorter freq list (common in benchmarks), slice SPL to match.
                    if _bench_freq_np.size > 0 and _bench_spl_np.size > 0:
                        if _bench_freq_np.size != _bench_spl_np.size:
                            if _bench_freq_np.size < _bench_spl_np.size:
                                _bench_spl_np = _bench_spl_np[: _bench_freq_np.size]
                                _benchmark_warning = (
                                    f"Benchmark '{_selected_benchmark}' SPL truncated to match frequency length."
                                    if _benchmark_warning is None else _benchmark_warning
                                )
                            else:
                                _benchmark_warning = (
                                    f"Benchmark '{_selected_benchmark}' has invalid data lengths."
                                )

                    _bench_mask = (
                        np.isfinite(_bench_freq_np)
                        & np.isfinite(_bench_spl_np)
                        & (_bench_freq_np > 0)
                    )
                    _bench_freq_np = _bench_freq_np[_bench_mask]
                    _bench_spl_np = _bench_spl_np[_bench_mask]
                    if _bench_freq_np.size < 2:
                        _benchmark_warning = (
                            f"Benchmark '{_selected_benchmark}' has insufficient valid points."
                        )
                    else:
                        _bench_order = np.argsort(_bench_freq_np)
                        _bench_freq_sorted = _bench_freq_np[_bench_order]
                        _bench_spl_sorted = _bench_spl_np[_bench_order]
                        _in_range = (
                            (_bench_freq_sorted >= _analysis_min)
                            & (_bench_freq_sorted <= _analysis_max)
                        )
                        if np.count_nonzero(_in_range) < 2:
                            _benchmark_warning = (
                                f"Benchmark '{_selected_benchmark}' does not overlap the analysis range."
                            )
                        else:
                            _benchmark_curve = {
                                "label": _benchmark_label,
                                "freq": _bench_freq_sorted[_in_range],
                                "spl": _bench_spl_sorted[_in_range],
                                "source_path": str(_bench_path),
                            }
            except Exception as _bench_exc:
                _benchmark_warning = (
                    f"Benchmark '{_selected_benchmark}' read error ({_bench_exc})."
                )

    _ppo = int(ana_ppo.value)
    _octaves = np.log2(_analysis_max / _analysis_min)
    _grid_points = max(16, int(_octaves * _ppo) + 1)
    _grid_hz = np.geomspace(_analysis_min, _analysis_max, _grid_points)
    _log_grid = np.log10(_grid_hz)

    _matrix_rows = []
    _titles = []
    for _curve in _curve_data:
        _interp = np.interp(_log_grid, np.log10(_curve["freq"]), _curve["spl"])
        _matrix_rows.append(_interp)
        _titles.append(_curve["title"])

    _matrix = np.asarray(_matrix_rows, dtype=float)
    _mean_curve = np.mean(_matrix, axis=0)
    _median_curve = np.median(_matrix, axis=0)
    _p10_curve = np.percentile(_matrix, 10, axis=0)
    _p90_curve = np.percentile(_matrix, 90, axis=0)
    _std_curve = np.std(_matrix, axis=0)

    _tol = float(ana_tol_db.value)
    _summary_rows = []
    _per_curve_metrics = []
    for _idx, _title in enumerate(_titles):
        _curve_vals = _matrix[_idx]
        _deviation = _curve_vals - _mean_curve
        _abs_dev = np.abs(_deviation)
        _max_dev = float(np.max(_abs_dev))
        _mean_abs_dev = float(np.mean(_abs_dev))
        _rms_dev = float(np.sqrt(np.mean(np.square(_deviation))))
        _pct_within = float(np.mean(_abs_dev <= _tol) * 100.0)
        _summary_rows.append(
            {
                "title": _title,
                "max_abs_deviation_db": round(_max_dev, 3),
                "within_tolerance": _max_dev <= _tol,
            }
        )
        _per_curve_metrics.append(
            {
                "title": _title,
                "max_abs_deviation_db": _max_dev,
                "rms_deviation_db": _rms_dev,
                "mean_abs_deviation_db": _mean_abs_dev,
                "pct_within_tolerance": _pct_within,
            }
        )

    def _dist_stats(values):
        _arr = np.asarray(values, dtype=float)
        return {
            "min": float(np.min(_arr)),
            "p25": float(np.percentile(_arr, 25)),
            "median": float(np.percentile(_arr, 50)),
            "p75": float(np.percentile(_arr, 75)),
            "max": float(np.max(_arr)),
            "mean": float(np.mean(_arr)),
            "std": float(np.std(_arr)),
        }

    _metric_map = {
        "max_abs_deviation_db": [m["max_abs_deviation_db"] for m in _per_curve_metrics],
        "rms_deviation_db": [m["rms_deviation_db"] for m in _per_curve_metrics],
        "mean_abs_deviation_db": [m["mean_abs_deviation_db"] for m in _per_curve_metrics],
        "pct_within_tolerance": [m["pct_within_tolerance"] for m in _per_curve_metrics],
    }
    _distribution_rows = []
    for _metric_name, _values in _metric_map.items():
        _stats = _dist_stats(_values)
        _distribution_rows.append(
            {
                "metric": _metric_name,
                "min": round(_stats["min"], 3),
                "p25": round(_stats["p25"], 3),
                "median": round(_stats["median"], 3),
                "p75": round(_stats["p75"], 3),
                "max": round(_stats["max"], 3),
                "mean": round(_stats["mean"], 3),
                "std": round(_stats["std"], 3),
            }
        )

    _fig = go.Figure()
    for _curve_idx in range(_matrix.shape[0]):
        _fig.add_trace(
            go.Scatter(
                x=_grid_hz,
                y=_matrix[_curve_idx],
                mode="lines",
                line=dict(color="#909090", width=1),
                opacity=0.30,
                name=_titles[_curve_idx],
                showlegend=False,
                hovertemplate=(
                    "Freq: %{x:.2f} Hz<br>"
                    "SPL: %{y:.2f} dB<br>"
                    f"Curve: {_titles[_curve_idx]}"
                    "<extra></extra>"
                ),
            )
        )

    _fig.add_trace(
        go.Scatter(
            x=_grid_hz,
            y=_p10_curve,
            mode="lines",
            line=dict(color="rgba(158,202,225,0.0)", width=1),
            name="P10-P90 band",
            showlegend=False,
            hoverinfo="skip",
        )
    )
    _fig.add_trace(
        go.Scatter(
            x=_grid_hz,
            y=_p90_curve,
            mode="lines",
            line=dict(color="rgba(158,202,225,0.6)", width=1),
            fill="tonexty",
            fillcolor="rgba(158,202,225,0.35)",
            name="P10-P90 band",
            hoverinfo="skip",
        )
    )
    _fig.add_trace(
        go.Scatter(
            x=_grid_hz,
            y=_mean_curve,
            mode="lines",
            line=dict(color="#2ecc71", width=2.4),
            name="Mean",
            hovertemplate="Mean<br>Freq: %{x:.2f} Hz<br>SPL: %{y:.2f} dB<extra></extra>",
        )
    )
    _fig.add_trace(
        go.Scatter(
            x=_grid_hz,
            y=_median_curve,
            mode="lines",
            line=dict(color="#f39c12", width=2.0, dash="dash"),
            name="Median",
            hovertemplate="Median<br>Freq: %{x:.2f} Hz<br>SPL: %{y:.2f} dB<extra></extra>",
        )
    )
    _fig.add_trace(
        go.Scatter(
            x=_grid_hz,
            y=_mean_curve + _tol,
            mode="lines",
            line=dict(color="#cb181d", width=1.8, dash="dot"),
            name=f"+/-{_tol:.2f} dB tolerance",
            hovertemplate="Tolerance upper<br>Freq: %{x:.2f} Hz<br>SPL: %{y:.2f} dB<extra></extra>",
        )
    )
    _fig.add_trace(
        go.Scatter(
            x=_grid_hz,
            y=_mean_curve - _tol,
            mode="lines",
            line=dict(color="#cb181d", width=1.8, dash="dot"),
            name=f"+/-{_tol:.2f} dB tolerance",
            showlegend=False,
            hovertemplate="Tolerance lower<br>Freq: %{x:.2f} Hz<br>SPL: %{y:.2f} dB<extra></extra>",
        )
    )
    if _benchmark_curve is not None:
        _fig.add_trace(
            go.Scatter(
                x=_benchmark_curve["freq"],
                y=_benchmark_curve["spl"],
                mode="lines",
                line=dict(color="#d4a017", width=2.2),
                name=f"Benchmark: {_benchmark_curve['label']}",
                hovertemplate="Benchmark<br>Freq: %{x:.2f} Hz<br>SPL: %{y:.2f} dB<extra></extra>",
            )
        )

    _fig.update_layout(
        title="Tolerance and Statistical Curves",
        xaxis=dict(title="Frequency (Hz)", type="log"),
        yaxis=dict(title="SPL (dB)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="closest",
        margin=dict(l=60, r=20, t=60, b=50),
        template="plotly_white",
    )

    _max_dev_values = _metric_map["max_abs_deviation_db"]
    _pct_values = _metric_map["pct_within_tolerance"]
    _titles_for_bins = [m["title"] for m in _per_curve_metrics]

    def _build_hist(values, titles, bins, range_override=None):
        _pairs = [
            (float(v), t)
            for v, t in zip(values, titles)
            if v is not None and np.isfinite(v)
        ]
        if not _pairs:
            return np.array([]), np.array([]), np.array([]), []

        _vals = np.array([v for v, _ in _pairs], dtype=float)
        _titles = [t for _, t in _pairs]

        _range = range_override
        if _range is None:
            _min = float(np.min(_vals))
            _max = float(np.max(_vals))
            if _min == _max:
                _pad = 0.5 if _min == 0 else max(abs(_min) * 0.01, 0.5)
                _range = (_min - _pad, _max + _pad)
                bins = 1
        _unique_count = len(np.unique(_vals))
        if _unique_count < bins:
            bins = max(1, _unique_count)

        try:
            hist, edges = np.histogram(_vals, bins=bins, range=_range)
        except ValueError:
            _min = float(np.min(_vals))
            _max = float(np.max(_vals))
            if _min == _max:
                _pad = 0.5 if _min == 0 else max(abs(_min) * 0.01, 0.5)
            else:
                _pad = max(abs(_max - _min) * 0.05, 0.5)
            _range = (_min - _pad, _max + _pad)
            hist, edges = np.histogram(_vals, bins=1, range=_range)
        bin_centers = (edges[:-1] + edges[1:]) / 2.0
        widths = edges[1:] - edges[:-1]
        bin_items = [[] for _ in range(len(hist))]
        for _val, _title in zip(_vals, _titles):
            _idx = np.searchsorted(edges, _val, side="right") - 1
            _idx = max(0, min(int(_idx), len(hist) - 1))
            bin_items[_idx].append(_title)

        def _format_titles(items, max_items=10):
            if not items:
                return "None"
            shown = items[:max_items]
            extra = len(items) - len(shown)
            extra_text = f"<br>+{extra} more" if extra > 0 else ""
            return "<br>".join(shown) + extra_text

        hovertext = []
        for i in range(len(hist)):
            hovertext.append(
                f"Range: {edges[i]:.3f} – {edges[i+1]:.3f}"
                f"<br>Count: {hist[i]}"
                f"<br>Measurements:<br>{_format_titles(bin_items[i])}"
            )
        return bin_centers, hist, widths, hovertext

    _within_count = sum(1 for v in _max_dev_values if v <= _tol)
    _max_centers, _max_hist, _max_widths, _max_hover = _build_hist(
        _max_dev_values,
        _titles_for_bins,
        bins=24,
    )
    _pct_centers, _pct_hist, _pct_widths, _pct_hover = _build_hist(
        _pct_values,
        _titles_for_bins,
        bins=20,
        range_override=(0, 100),
    )

    _dist_fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            f"Max Abs Deviation Distribution (within tol: {_within_count}/{len(_max_dev_values)})",
            "Percent Within Tolerance Distribution",
        ),
        horizontal_spacing=0.18,
    )
    _dist_fig.add_trace(
        go.Bar(
            x=_max_centers,
            y=_max_hist,
            width=_max_widths,
            marker=dict(color="#9ecae1"),
            hovertext=_max_hover,
            hoverinfo="text",
            name="Max abs deviation",
        ),
        row=1,
        col=1,
    )
    _dist_fig.add_vline(
        x=_tol,
        line_dash="dash",
        line_color="#cb181d",
        annotation_text=f"Tolerance ({_tol:.2f} dB)",
        annotation_position="top right",
        row=1,
        col=1,
    )

    _median_pct = float(np.percentile(_pct_values, 50))
    _dist_fig.add_trace(
        go.Bar(
            x=_pct_centers,
            y=_pct_hist,
            width=_pct_widths,
            marker=dict(color="#c7e9c0"),
            hovertext=_pct_hover,
            hoverinfo="text",
            name="Percent within tolerance",
        ),
        row=1,
        col=2,
    )
    _dist_fig.add_vline(
        x=_median_pct,
        line_dash="dash",
        line_color="#238b45",
        annotation_text=f"Median {_median_pct:.2f}%",
        annotation_position="top right",
        row=1,
        col=2,
    )

    _dist_fig.update_xaxes(title_text="Max abs deviation (dB)", row=1, col=1)
    _dist_fig.update_yaxes(title_text="Count", row=1, col=1)
    _dist_fig.update_xaxes(title_text="Percent within tolerance (%)", range=[0, 100], row=1, col=2)
    _dist_fig.update_yaxes(title_text="Count", row=1, col=2)
    _dist_fig.update_layout(
        margin=dict(l=70, r=40, t=70, b=60),
        template="plotly_white",
        showlegend=False,
        height=420,
    )
    _dist_fig.update_xaxes(showgrid=True, gridcolor="rgba(0,0,0,0.08)")
    _dist_fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.08)")

    _result_payload = {
        "status": "ok",
        "selected_count": len(ana_selected_records),
        "valid_count": len(_curve_data),
        "freq_min_hz": _analysis_min,
        "freq_max_hz": _analysis_max,
        "grid_points": _grid_points,
        "tolerance_db": _tol,
        "band_label": _band_label,
        "band_min_hz": _band_min,
        "band_max_hz": _band_max,
        "summary_rows": _summary_rows,
        "distribution_rows": _distribution_rows,
        "per_curve_metrics": _per_curve_metrics,
        "load_errors": _load_errors,
        "figure": _fig,
        "dist_fig": _dist_fig,
        "source_files": [c["source_path"] for c in _curve_data],
        "std_curve_mean_db": float(np.mean(_std_curve)),
        "benchmark_label": _benchmark_curve["label"] if _benchmark_curve else None,
        "benchmark_source_path": _benchmark_curve["source_path"] if _benchmark_curve else None,
        "benchmark_warning": _benchmark_warning,
    }

    ana_set_result_state(_result_payload)
    return


@app.cell
def _(ana_result_state):
    _result = ana_result_state()
    if _result is None:
        mo.md("No analysis computed yet.")
    else:
        _header = (
            f"Selected: `{_result['selected_count']}` | "
            f"Valid curves: `{_result['valid_count']}` | "
            f"Range: `{_result['freq_min_hz']:.2f}-{_result['freq_max_hz']:.2f} Hz` | "
            f"Grid points: `{_result['grid_points']}` | "
            f"Mean std-dev: `{_result['std_curve_mean_db']:.3f} dB`"
        )
        mo.md(_header)
        if _result.get("band_label") and _result.get("band_label") != "Full Range":
            mo.md(f"Band: `{_result['band_label']}`")
        if _result.get("benchmark_label"):
            mo.md(f"Benchmark overlay: `{_result['benchmark_label']}`")
        mo.ui.table(_result["summary_rows"], label="Tolerance Summary")
        mo.md("## Group Distribution Summary")
        mo.ui.table(_result["distribution_rows"], label="Group Metric Distribution (per-curve)")
        if _result["load_errors"]:
            mo.md("### Load Warnings")
            for _err in _result["load_errors"]:
                mo.md(f"- {_err}")
        if _result.get("benchmark_warning"):
            mo.md("### Benchmark Warning")
            mo.md(f"- {_result['benchmark_warning']}")
    return


@app.cell
def _(ana_result_state):
    _result = ana_result_state()
    mo.stop(_result is None, mo.md("Run analysis to generate aggregate stats."))
    _per_curve = _result.get("per_curve_metrics", [])
    _widgets = [mo.md("## Aggregate Stats")]
    if not _per_curve:
        _widgets.append(mo.md("Re-run analysis to populate aggregate and per-curve stats."))
    else:
        _max_vals = [r["max_abs_deviation_db"] for r in _per_curve]
        _pct_vals = [r["pct_within_tolerance"] for r in _per_curve]
        _agg_rows = [
            {"metric": "curve_count", "value": len(_per_curve)},
            {"metric": "freq_min_hz", "value": round(_result["freq_min_hz"], 3)},
            {"metric": "freq_max_hz", "value": round(_result["freq_max_hz"], 3)},
            {"metric": "grid_points", "value": int(_result["grid_points"])},
            {"metric": "tolerance_db", "value": round(_result["tolerance_db"], 3)},
            {"metric": "mean_std_dev_db", "value": round(_result["std_curve_mean_db"], 3)},
            {"metric": "median_max_abs_dev_db", "value": round(float(np.percentile(_max_vals, 50)), 3)},
            {"metric": "mean_pct_within_tolerance", "value": round(float(np.mean(_pct_vals)), 2)},
            {"metric": "min_pct_within_tolerance", "value": round(float(np.min(_pct_vals)), 2)},
            {"metric": "max_pct_within_tolerance", "value": round(float(np.max(_pct_vals)), 2)},
        ]
        _widgets.append(mo.ui.table(_agg_rows, label="Aggregate Stats"))

        _per_curve_rows = []
        for _row in _per_curve:
            _per_curve_rows.append(
                {
                    "title": _row.get("title", ""),
                    "max_abs_deviation_db": round(float(_row["max_abs_deviation_db"]), 3),
                    "rms_deviation_db": round(float(_row["rms_deviation_db"]), 3),
                    "mean_abs_deviation_db": round(float(_row["mean_abs_deviation_db"]), 3),
                    "pct_within_tolerance": round(float(_row["pct_within_tolerance"]), 2),
                    "within_tolerance": float(_row["max_abs_deviation_db"]) <= float(_result["tolerance_db"]),
                }
            )
        _widgets.append(mo.ui.table(_per_curve_rows, label="Per-Curve Stats"))
    mo.vstack(_widgets)
    return


@app.cell
def _(ana_result_state):
    _result = ana_result_state()
    mo.stop(_result is None, mo.md("Run analysis to generate distribution plots."))
    _dist_fig = _result.get("dist_fig")
    mo.stop(_dist_fig is None, mo.md("Distribution plots are not available yet."))
    mo.md("## Distribution Plots")
    mo.md(
        "Chart help: "
        "<span title='Shows the distribution of each curve maximum absolute deviation from the mean across the analysis band.'>"
        "Max Abs Deviation Distribution [?]</span>"
        " | "
        "<span title='Shows the distribution of the percent of frequency points within tolerance for each curve.'>"
        "Percent Within Tolerance Distribution [?]</span>"
    )
    _dist_fig
    return


@app.cell
def _(ana_result_state):
    _result = ana_result_state()
    mo.stop(_result is None, mo.md("Run analysis to generate plot output."))
    _figure = _result.get("figure")
    mo.stop(_figure is None, mo.md("No analysis figure is available yet."))
    mo.md("## Statistical Plot")
    _figure
    return


if __name__ == "__main__":
    app.run()
