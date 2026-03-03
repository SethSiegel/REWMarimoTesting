# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.19.0",
#     "psycopg[binary]==3.3.2",
#     "matplotlib==3.10.8",
#     "pyzmq>=27.1.0",
#     "numpy>=2.0.0",
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
    ana_last_load_click_state, ana_set_last_load_click_state = mo.state(0)
    ana_load_status_state, ana_set_load_status_state = mo.state("idle")
    ana_load_error_state, ana_set_load_error_state = mo.state("")
    ana_load_diag_state, ana_set_load_diag_state = mo.state({})
    return (
        ana_load_error_state,
        ana_load_diag_state,
        ana_last_load_click_state,
        ana_load_status_state,
        ana_loaded_at_state,
        ana_records_state,
        ana_set_load_error_state,
        ana_set_load_diag_state,
        ana_set_last_load_click_state,
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
    ana_last_load_click_state,
    ana_load_button,
    ana_set_load_error_state,
    ana_set_load_diag_state,
    ana_set_last_load_click_state,
    ana_set_load_status_state,
    ana_set_loaded_at_state,
    ana_set_records_state,
):
    mo.stop(not ana_load_button.value, mo.md("Click **Load JSON Records From Database** to begin."))
    mo.stop(
        ana_load_button.value <= ana_last_load_click_state(),
        mo.md("Records already loaded for this click."),
    )

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
    ana_set_last_load_click_state(ana_load_button.value)
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
def _(ana_records_state):
    _tbl = mo.ui.table(ana_records_state(), label="JSON Records")
    _tbl
    return


@app.cell
def _(ana_records_state):
    _records = ana_records_state()
    _items = []
    for _r in _records:
        _file_id = _r.get("file_id")
        if not _file_id:
            continue
        _title = _r.get("title") or "(untitled)"
        _unit_type = _r.get("unit_type") or "?"
        _unit_number = _r.get("unit_number") or "?"
        _parent = _r.get("parent_mdat") or "-"
        _label = f"{_file_id} | {_title} | {_unit_type}-{_unit_number} | parent:{_parent}"
        _items.append((_label, _r))

    _items.sort(key=lambda x: x[0])
    ana_record_label_to_record = {lbl: rec for lbl, rec in _items}
    ana_record_select = mo.ui.multiselect(
        options=[lbl for lbl, _ in _items],
        value=[],
        label="Select records for statistical analysis",
    )
    ana_record_select
    return ana_record_label_to_record, ana_record_select


@app.cell
def _(ana_record_label_to_record, ana_record_select):
    ana_selected_records = [
        ana_record_label_to_record[lbl]
        for lbl in ana_record_select.value
        if lbl in ana_record_label_to_record
    ]
    return (ana_selected_records,)


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
    ana_tol_db = mo.ui.number(start=0.1, stop=24.0, step=0.1, value=3.0, label="Tolerance (dB)")
    ana_min_hz = mo.ui.number(start=10.0, stop=1000.0, step=1.0, value=20.0, label="Min Freq (Hz)")
    ana_max_hz = mo.ui.number(start=200.0, stop=40000.0, step=10.0, value=20000.0, label="Max Freq (Hz)")
    ana_ppo = mo.ui.number(start=3, stop=96, step=1, value=24, label="Points/Octave")
    ana_run_button = mo.ui.run_button(label="Run Statistical Analysis")
    ana_tol_db, ana_min_hz, ana_max_hz, ana_ppo, ana_run_button
    return ana_max_hz, ana_min_hz, ana_ppo, ana_run_button, ana_tol_db


@app.cell
def _():
    ana_result_state, ana_set_result_state = mo.state(None)
    ana_last_run_click_state, ana_set_last_run_click_state = mo.state(0)
    return (
        ana_last_run_click_state,
        ana_result_state,
        ana_set_last_run_click_state,
        ana_set_result_state,
    )


@app.cell
def _(
    ana_last_run_click_state,
    ana_max_hz,
    ana_min_hz,
    ana_ppo,
    ana_records_state,
    ana_run_button,
    ana_selected_records,
    ana_set_last_run_click_state,
    ana_set_result_state,
    ana_tol_db,
):
    mo.stop(not ana_run_button.value, mo.md("Click **Run Statistical Analysis** to compute curves."))
    mo.stop(
        ana_run_button.value <= ana_last_run_click_state(),
        mo.md("Analysis already computed for this click."),
    )
    mo.stop(not ana_selected_records, mo.md("Select at least one JSON record."))

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

    mo.stop(not _curve_data, mo.md("No valid curves loaded. Check selected records and file paths."))

    _user_min = float(ana_min_hz.value)
    _user_max = float(ana_max_hz.value)
    _min_overlap = max(float(np.min(c["freq"])) for c in _curve_data)
    _max_overlap = min(float(np.max(c["freq"])) for c in _curve_data)
    _analysis_min = max(_user_min, _min_overlap)
    _analysis_max = min(_user_max, _max_overlap)
    mo.stop(_analysis_max <= _analysis_min, mo.md("No overlapping frequency range across selected curves."))

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
    for _idx, _title in enumerate(_titles):
        _curve_vals = _matrix[_idx]
        _deviation = np.abs(_curve_vals - _mean_curve)
        _max_dev = float(np.max(_deviation))
        _summary_rows.append(
            {
                "title": _title,
                "max_abs_deviation_db": round(_max_dev, 3),
                "within_tolerance": _max_dev <= _tol,
            }
        )

    _fig, _ax = plt.subplots(figsize=(11, 6))
    for _curve_idx in range(_matrix.shape[0]):
        _ax.semilogx(_grid_hz, _matrix[_curve_idx], color="#909090", alpha=0.30, linewidth=1.0)
    _ax.fill_between(_grid_hz, _p10_curve, _p90_curve, color="#9ecae1", alpha=0.35, label="P10-P90 band")
    _ax.semilogx(_grid_hz, _mean_curve, color="#045a8d", linewidth=2.4, label="Mean")
    _ax.semilogx(_grid_hz, _median_curve, color="#238b45", linewidth=2.0, linestyle="--", label="Median")
    _ax.semilogx(_grid_hz, _mean_curve + _tol, color="#cb181d", linestyle=":", linewidth=1.8, label=f"+/-{_tol:.2f} dB tolerance")
    _ax.semilogx(_grid_hz, _mean_curve - _tol, color="#cb181d", linestyle=":", linewidth=1.8)
    _ax.set_xlabel("Frequency (Hz)")
    _ax.set_ylabel("SPL (dB)")
    _ax.set_title("Tolerance and Statistical Curves")
    _ax.grid(True, which="both", linestyle="--", alpha=0.35)
    _ax.legend(loc="best")

    _result_payload = {
        "status": "ok",
        "selected_count": len(ana_selected_records),
        "valid_count": len(_curve_data),
        "freq_min_hz": _analysis_min,
        "freq_max_hz": _analysis_max,
        "grid_points": _grid_points,
        "tolerance_db": _tol,
        "summary_rows": _summary_rows,
        "load_errors": _load_errors,
        "figure": _fig,
        "source_files": [c["source_path"] for c in _curve_data],
        "std_curve_mean_db": float(np.mean(_std_curve)),
    }

    ana_set_result_state(_result_payload)
    ana_set_last_run_click_state(ana_run_button.value)
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
        mo.ui.table(_result["summary_rows"], label="Tolerance Summary")
        if _result["load_errors"]:
            mo.md("### Load Warnings")
            for _err in _result["load_errors"]:
                mo.md(f"- {_err}")
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
