# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.19.0",
#     "psycopg[binary]==3.3.2",
#     "matplotlib==3.10.8",
#     "pyzmq>=27.1.0",
#     "requests>=2.32.5",
# ]
# ///

import marimo

__generated_with = "0.19.11"
app = marimo.App()

with app.setup:
    import sys
    import pathlib as _pathlib
    repo_root = _pathlib.Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    import marimo as mo
    import os
    from datetime import datetime
    import psycopg
    import json
    import matplotlib.pyplot as plt
    from project_paths import get_data_root
    from import_local_files import import_files


@app.cell
def _():
    mo.md(r"""
    # REW Metadata Dashboard
    Browse measurements stored in Postgres.
    """)
    return


@app.cell
def _():
    mo.md(r"""
    ## Connection
    Set database connection values (defaults from `.env`).
    """)
    return


@app.cell
def _():
    db_host = mo.ui.text(label="Host", value=os.getenv("POSTGRES_HOST", "localhost"))
    db_port = mo.ui.text(label="Port", value=os.getenv("POSTGRES_PORT", "5432"))
    db_name = mo.ui.text(label="Database", value=os.getenv("POSTGRES_DB", "testingdb-postgres"))
    db_user = mo.ui.text(label="User", value=os.getenv("POSTGRES_USER", "rew_app"))
    db_pass = mo.ui.text(label="Password", value=os.getenv("POSTGRES_PASSWORD", ""))
    db_host, db_port, db_name, db_user, db_pass
    return db_host, db_name, db_pass, db_port, db_user


@app.cell
def _():
    connect_button = mo.ui.run_button(label="Connect")
    connect_button
    return (connect_button,)


@app.cell
def _():
    connect_last_value, set_connect_last_value = mo.state(0)
    records_state, set_records_state = mo.state([])
    last_refresh_state, set_last_refresh_state = mo.state(None)
    connect_last_value, records_state, last_refresh_state
    return (
        connect_last_value,
        last_refresh_state,
        records_state,
        set_connect_last_value,
        set_last_refresh_state,
        set_records_state,
    )


@app.cell
def _(
    connect_button,
    connect_last_value,
    db_host,
    db_name,
    db_pass,
    db_port,
    db_user,
    set_connect_last_value,
    set_last_refresh_state,
    set_records_state,
    title_filter,
    unit_number_filter,
    unit_type_filter,
):
    mo.stop(not connect_button.value, mo.md("Click **Connect** to load data."))
    mo.stop(connect_button.value <= connect_last_value(), mo.md("Click **Connect** to reconnect."))

    _conn = psycopg.connect(
        host=db_host.value.strip(),
        port=int(db_port.value.strip()),
        dbname=db_name.value.strip(),
        user=db_user.value.strip(),
        password=db_pass.value,
    )
    _conn.autocommit = True
    try:
        with _conn.cursor() as _cur:
            _cur.execute(
                """
                ALTER TABLE measurement
                ADD COLUMN IF NOT EXISTS freq_min DOUBLE PRECISION,
                ADD COLUMN IF NOT EXISTS freq_max DOUBLE PRECISION,
                ADD COLUMN IF NOT EXISTS freq_count INTEGER,
                ADD COLUMN IF NOT EXISTS spl_min DOUBLE PRECISION,
                ADD COLUMN IF NOT EXISTS spl_max DOUBLE PRECISION,
                ADD COLUMN IF NOT EXISTS spl_count INTEGER,
                ADD COLUMN IF NOT EXISTS parent_mdat TEXT
                """
            )

        _query = """
            SELECT
                COALESCE(
                    m.title,
                    CASE
                        WHEN f.kind = 'mdat' THEN regexp_replace(f.relative_path, '^mdat/', '')
                        ELSE ''
                    END
                ) AS title,
                f.id AS file_id,
                m.id AS measurement_id,
                m.smoothing,
                m.start_freq,
                m.end_freq,
                m.rew_version,
                m.measured_at,
                COALESCE(to_jsonb(m) ->> 'parent_mdat', '') AS parent_mdat,
                COALESCE(f.kind, '') AS kind,
                COALESCE(f.relative_path, '') AS relative_path,
                COALESCE(h.base_url, '') AS base_url
            FROM measurement_file f
            LEFT JOIN measurement m ON f.measurement_id = m.id
            LEFT JOIN file_host h ON h.id = f.host_id
            WHERE
                (COALESCE(m.title, '') ILIKE %(title)s OR %(title)s = '%%')
                AND (COALESCE(m.unit_type, '') ILIKE %(unit_type)s OR %(unit_type)s = '%%')
                AND (COALESCE(m.unit_number, '') ILIKE %(unit_number)s OR %(unit_number)s = '%%')
            ORDER BY f.created_at DESC
            LIMIT 500
        """

        _params = {
            "title": f"%{title_filter.value.strip()}%" if title_filter.value else "%%",
            "unit_type": f"%{unit_type_filter.value.strip()}%" if unit_type_filter.value else "%%",
            "unit_number": f"%{unit_number_filter.value.strip()}%" if unit_number_filter.value else "%%",
        }

        with _conn.cursor() as _cur:
            _cur.execute(_query, _params)
            _rows = _cur.fetchall()
            _columns = [desc.name for desc in _cur.description]

        _records = []
        for _row in _rows:
            _record = dict(zip(_columns, _row))
            for _key, _value in _record.items():
                if _value is None:
                    _record[_key] = ""
            _records.append(_record)
    finally:
        _conn.close()

    set_records_state(_records)
    set_connect_last_value(connect_button.value)
    set_last_refresh_state(datetime.now())
    return


@app.cell
def _():
    mo.md(r"""
    ## Import
    Sync local JSON/MDAT files into Postgres.
    """)
    return


@app.cell
def _():
    import_local_root = repo_root / "data"
    import_shared_root = get_data_root()
    copy_to_shared = mo.ui.checkbox(
        value=True,
        label="Copy local files to shared data folder (REW_DATA_DIR)",
    )
    mo.md(rf"**Importing from:** `{str(import_local_root)}`")
    mo.md(rf"**Shared data folder:** `{str(import_shared_root)}`")
    copy_to_shared
    return copy_to_shared, import_local_root, import_shared_root


@app.cell
def _():
    import_button = mo.ui.run_button(label="Import Local Files")
    import_button
    return (import_button,)


@app.cell
def _(
    copy_to_shared,
    db_host,
    db_name,
    db_pass,
    db_port,
    db_user,
    import_button,
    import_local_root,
    import_shared_root,
    set_last_refresh_state,
    set_records_state,
    title_filter,
    unit_number_filter,
    unit_type_filter,
):
    mo.stop(not import_button.value, mo.md("Click **Import Local Files** to run."))
    copy_root = import_shared_root if copy_to_shared.value else None
    _conn = psycopg.connect(
        host=db_host.value.strip(),
        port=int(db_port.value.strip()),
        dbname=db_name.value.strip(),
        user=db_user.value.strip(),
        password=db_pass.value,
    )
    _conn.autocommit = True
    try:
        import_files(conn=_conn, data_root_override=import_local_root, copy_to_shared_root=copy_root)
        _query = """
            SELECT
                COALESCE(
                    m.title,
                    CASE
                        WHEN f.kind = 'mdat' THEN regexp_replace(f.relative_path, '^mdat/', '')
                        ELSE ''
                    END
                ) AS title,
                f.id AS file_id,
                m.id AS measurement_id,
                m.smoothing,
                m.start_freq,
                m.end_freq,
                m.rew_version,
                m.measured_at,
                COALESCE(to_jsonb(m) ->> 'parent_mdat', '') AS parent_mdat,
                COALESCE(f.kind, '') AS kind,
                COALESCE(f.relative_path, '') AS relative_path,
                COALESCE(h.base_url, '') AS base_url
            FROM measurement_file f
            LEFT JOIN measurement m ON f.measurement_id = m.id
            LEFT JOIN file_host h ON h.id = f.host_id
            WHERE
                (COALESCE(m.title, '') ILIKE %(title)s OR %(title)s = '%%')
                AND (COALESCE(m.unit_type, '') ILIKE %(unit_type)s OR %(unit_type)s = '%%')
                AND (COALESCE(m.unit_number, '') ILIKE %(unit_number)s OR %(unit_number)s = '%%')
            ORDER BY f.created_at DESC
            LIMIT 500
        """

        _params = {
            "title": f"%{title_filter.value.strip()}%" if title_filter.value else "%%",
            "unit_type": f"%{unit_type_filter.value.strip()}%" if unit_type_filter.value else "%%",
            "unit_number": f"%{unit_number_filter.value.strip()}%" if unit_number_filter.value else "%%",
        }

        with _conn.cursor() as _cur:
            _cur.execute(_query, _params)
            _rows = _cur.fetchall()
            _columns = [desc.name for desc in _cur.description]

        _records = []
        for _row in _rows:
            _record = dict(zip(_columns, _row))
            for _key, _value in _record.items():
                if _value is None:
                    _record[_key] = ""
            _records.append(_record)
    finally:
        _conn.close()
    set_records_state(_records)
    set_last_refresh_state(datetime.now())
    mo.md("Import complete.")
    return


@app.cell
def _():
    mo.md(r"""
    ## Filters
    Use these to narrow results.
    """)
    return


@app.cell
def _(last_refresh_state):
    if last_refresh_state() is None:
        mo.md("**Last refreshed:** —")
    else:
        mo.md(rf"**Last refreshed:** `{last_refresh_state().strftime('%Y-%m-%d %H:%M:%S')}`")
    return


@app.cell
def _():
    title_filter = mo.ui.text(label="Title contains", value="")
    unit_type_filter = mo.ui.text(label="Unit type", value="")
    unit_number_filter = mo.ui.text(label="Unit number", value="")
    title_filter, unit_type_filter, unit_number_filter
    return title_filter, unit_number_filter, unit_type_filter


@app.cell
def _():
    refresh_button = mo.ui.run_button(label="Refresh Table")
    refresh_button
    return (refresh_button,)


@app.cell
def _(
    db_host,
    db_name,
    db_pass,
    db_port,
    db_user,
    refresh_button,
    set_last_refresh_state,
    set_records_state,
    title_filter,
    unit_number_filter,
    unit_type_filter,
):
    mo.stop(not refresh_button.value, mo.md("Click **Refresh Table** to query."))
    _conn = psycopg.connect(
        host=db_host.value.strip(),
        port=int(db_port.value.strip()),
        dbname=db_name.value.strip(),
        user=db_user.value.strip(),
        password=db_pass.value,
    )
    _conn.autocommit = True
    try:
        _query = """
            SELECT
                COALESCE(
                    m.title,
                    CASE
                        WHEN f.kind = 'mdat' THEN regexp_replace(f.relative_path, '^mdat/', '')
                        ELSE ''
                    END
                ) AS title,
                f.id AS file_id,
                m.id AS measurement_id,
                m.smoothing,
                m.start_freq,
                m.end_freq,
                m.rew_version,
                m.measured_at,
                COALESCE(to_jsonb(m) ->> 'parent_mdat', '') AS parent_mdat,
                COALESCE(f.kind, '') AS kind,
                COALESCE(f.relative_path, '') AS relative_path,
                COALESCE(h.base_url, '') AS base_url
            FROM measurement_file f
            LEFT JOIN measurement m ON f.measurement_id = m.id
            LEFT JOIN file_host h ON h.id = f.host_id
            WHERE
                (COALESCE(m.title, '') ILIKE %(title)s OR %(title)s = '%%')
                AND (COALESCE(m.unit_type, '') ILIKE %(unit_type)s OR %(unit_type)s = '%%')
                AND (COALESCE(m.unit_number, '') ILIKE %(unit_number)s OR %(unit_number)s = '%%')
            ORDER BY f.created_at DESC
            LIMIT 500
        """

        _params = {
            "title": f"%{title_filter.value.strip()}%" if title_filter.value else "%%",
            "unit_type": f"%{unit_type_filter.value.strip()}%" if unit_type_filter.value else "%%",
            "unit_number": f"%{unit_number_filter.value.strip()}%" if unit_number_filter.value else "%%",
        }

        with _conn.cursor() as _cur:
            _cur.execute(_query, _params)
            _rows = _cur.fetchall()
            _columns = [desc.name for desc in _cur.description]

        _records = []
        for _row in _rows:
            _record = dict(zip(_columns, _row))
            for _key, _value in _record.items():
                if _value is None:
                    _record[_key] = ""
            _records.append(_record)
    finally:
        _conn.close()
    set_records_state(_records)
    set_last_refresh_state(datetime.now())
    return


@app.cell
def _(records_state):
    mo.ui.table(records_state(), label="Measurements")
    return


@app.cell
def _():
    mo.md(r"""
    ## Plot JSON
    Select a JSON file to plot SPL vs Frequency.
    """)
    return


@app.cell
def _(records_state):
    json_paths = [r.get("relative_path") for r in records_state() if r.get("kind") == "json"]
    plot_select = mo.ui.dropdown(
        options=json_paths,
        value=json_paths[0] if json_paths else None,
        label="Select JSON file",
    )
    plot_select
    return (plot_select,)


@app.cell
def _(plot_select):
    mo.stop(not plot_select.value, mo.md("Select a JSON file to plot."))

    shared_root = get_data_root()
    local_root = repo_root / "data"
    json_path_shared = shared_root / plot_select.value
    json_path_local = local_root / plot_select.value

    if json_path_shared.exists():
        json_path = json_path_shared
    elif json_path_local.exists():
        json_path = json_path_local
        mo.md(rf"Using local file: `{str(json_path_local)}`")
    else:
        mo.stop(
            True,
            mo.md(
                rf"File not found in shared or local data folders. Checked:"
                f"\n- `{str(json_path_shared)}`"
                f"\n- `{str(json_path_local)}`"
            ),
        )

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    freq = data.get("Freq(Hz)", [])
    spl = data.get("SPL(dB)", [])

    fig, ax = plt.subplots()
    ax.semilogx(freq, spl)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("SPL (dB)")
    ax.set_title(data.get("filename", "SPL vs Frequency"))
    ax.grid(True, which="both", ls="--", alpha=0.4)

    fig
    return


@app.cell
def _():
    mo.md(r"""
    ## Delete Entry
    Delete a file pointer from the database (requires password).
    """)
    return


@app.cell
def _(records_state):
    file_id_items = []
    for r in records_state():
        file_id = r.get("file_id")
        if not file_id:
            continue
        title = r.get("title") or r.get("relative_path") or "Untitled"
        label = f"{file_id}: {title}"
        file_id_items.append((label, file_id))

    file_id_items.sort(key=lambda x: x[0])
    delete_labels = [label for label, _ in file_id_items]
    label_to_id = {label: file_id for label, file_id in file_id_items}

    delete_file_ids = mo.ui.multiselect(
        options=delete_labels,
        value=delete_labels[:1] if delete_labels else [],
        label="Select file_ids to delete",
    )
    delete_file_ids
    return delete_file_ids, label_to_id


@app.cell
def _(delete_file_ids, label_to_id):
    selected_ids = [label_to_id[label] for label in delete_file_ids.value]
    return (selected_ids,)


@app.cell
def _():
    delete_password = mo.ui.text(label="Delete password", value="")
    delete_password
    return (delete_password,)


@app.cell
def _():
    delete_button = mo.ui.run_button(label="Delete Selected Entry")
    delete_button
    return (delete_button,)


@app.cell
def _(
    db_host,
    db_name,
    db_pass,
    db_port,
    db_user,
    delete_button,
    delete_password,
    selected_ids,
    set_last_refresh_state,
    set_records_state,
    title_filter,
    unit_number_filter,
    unit_type_filter,
):
    mo.stop(not delete_button.value, mo.md("Click **Delete Selected Entry** to proceed."))
    mo.stop(delete_password.value.strip() != "12354", mo.md("Invalid password."))
    mo.stop(not selected_ids, mo.md("No files selected."))

    _conn = psycopg.connect(
        host=db_host.value.strip(),
        port=int(db_port.value.strip()),
        dbname=db_name.value.strip(),
        user=db_user.value.strip(),
        password=db_pass.value,
    )
    _conn.autocommit = True
    try:
        with _conn.cursor() as _cur:
            _cur.execute(
                "DELETE FROM measurement_file WHERE id = ANY(%s)",
                (selected_ids,),
            )
        _query = """
            SELECT
                COALESCE(
                    m.title,
                    CASE
                        WHEN f.kind = 'mdat' THEN regexp_replace(f.relative_path, '^mdat/', '')
                        ELSE ''
                    END
                ) AS title,
                f.id AS file_id,
                m.id AS measurement_id,
                m.smoothing,
                m.start_freq,
                m.end_freq,
                m.rew_version,
                m.measured_at,
                COALESCE(to_jsonb(m) ->> 'parent_mdat', '') AS parent_mdat,
                COALESCE(f.kind, '') AS kind,
                COALESCE(f.relative_path, '') AS relative_path,
                COALESCE(h.base_url, '') AS base_url
            FROM measurement_file f
            LEFT JOIN measurement m ON f.measurement_id = m.id
            LEFT JOIN file_host h ON h.id = f.host_id
            WHERE
                (COALESCE(m.title, '') ILIKE %(title)s OR %(title)s = '%%')
                AND (COALESCE(m.unit_type, '') ILIKE %(unit_type)s OR %(unit_type)s = '%%')
                AND (COALESCE(m.unit_number, '') ILIKE %(unit_number)s OR %(unit_number)s = '%%')
            ORDER BY f.created_at DESC
            LIMIT 500
        """

        _params = {
            "title": f"%{title_filter.value.strip()}%" if title_filter.value else "%%",
            "unit_type": f"%{unit_type_filter.value.strip()}%" if unit_type_filter.value else "%%",
            "unit_number": f"%{unit_number_filter.value.strip()}%" if unit_number_filter.value else "%%",
        }

        with _conn.cursor() as _cur:
            _cur.execute(_query, _params)
            _rows = _cur.fetchall()
            _columns = [desc.name for desc in _cur.description]

        _records = []
        for _row in _rows:
            _record = dict(zip(_columns, _row))
            for _key, _value in _record.items():
                if _value is None:
                    _record[_key] = ""
            _records.append(_record)
    finally:
        _conn.close()
    set_records_state(_records)
    set_last_refresh_state(datetime.now())
    mo.md(f"Deleted {len(selected_ids)} entries.")
    return


if __name__ == "__main__":
    app.run()
