# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.19.0",
#     "psycopg[binary]==3.3.2",
#     "matplotlib==3.10.8",
# ]
# ///

import marimo

__generated_with = "0.19.7"
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
    return (db_host, db_port, db_name, db_user, db_pass)


@app.cell
def _(db_host, db_name, db_pass, db_port, db_user):
    connect_button = mo.ui.run_button(label="Connect")
    connect_button
    return (connect_button,)


@app.cell
def _(connect_button, db_host, db_name, db_pass, db_port, db_user):
    mo.stop(not connect_button.value, mo.md("Click **Connect** to load data."))

    conn = psycopg.connect(
        host=db_host.value.strip(),
        port=int(db_port.value.strip()),
        dbname=db_name.value.strip(),
        user=db_user.value.strip(),
        password=db_pass.value,
    )
    return (conn,)


@app.cell
def _(conn):
    with conn.cursor() as _cur:
        _cur.execute(
            """
            ALTER TABLE measurement
            ADD COLUMN IF NOT EXISTS freq_min DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS freq_max DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS freq_count INTEGER,
            ADD COLUMN IF NOT EXISTS spl_min DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS spl_max DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS spl_count INTEGER
            """
        )
    conn.commit()
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
    import_button = mo.ui.run_button(label="Import Local Files")
    import_button
    return (import_button,)


@app.cell
def _(import_button):
    mo.stop(not import_button.value, mo.md("Click **Import Local Files** to run."))
    import_files()
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
def _():
    title_filter = mo.ui.text(label="Title contains", value="")
    unit_type_filter = mo.ui.text(label="Unit type", value="")
    unit_number_filter = mo.ui.text(label="Unit number", value="")
    title_filter, unit_type_filter, unit_number_filter
    return (title_filter, unit_type_filter, unit_number_filter)


@app.cell
def _():
    refresh_button = mo.ui.run_button(label="Refresh Table")
    refresh_button
    return (refresh_button,)


@app.cell
def _(
    conn,
    refresh_button,
    title_filter,
    unit_number_filter,
    unit_type_filter,
):
    _ = refresh_button.value
    query = """
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

    params = {
        "title": f"%{title_filter.value.strip()}%" if title_filter.value else "%%",
        "unit_type": f"%{unit_type_filter.value.strip()}%" if unit_type_filter.value else "%%",
        "unit_number": f"%{unit_number_filter.value.strip()}%" if unit_number_filter.value else "%%",
    }

    with conn.cursor() as _cur:
        _cur.execute(query, params)
        rows = _cur.fetchall()
        columns = [desc.name for desc in _cur.description]

    records = []
    for row in rows:
        record = dict(zip(columns, row))
        for key, value in record.items():
            if value is None:
                record[key] = ""
        records.append(record)
    return (records,)


@app.cell
def _(records):
    mo.ui.table(records, label="Measurements")
    return


@app.cell
def _():
    mo.md(r"""
    ## Plot JSON
    Select a JSON file to plot SPL vs Frequency.
    """)
    return


@app.cell
def _(records):
    json_paths = [r.get("relative_path") for r in records if r.get("kind") == "json"]
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

    data_root = get_data_root()
    json_path = data_root / plot_select.value
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
    return (fig,)




@app.cell
def _():
    mo.md(r"""
    ## Delete Entry
    Delete a file pointer from the database (requires password).
    """)
    return


@app.cell
def _(records):
    file_id_options = [r.get("file_id") for r in records if r.get("file_id")]
    delete_file_id = mo.ui.dropdown(
        options=file_id_options,
        value=file_id_options[0] if file_id_options else None,
        label="Select file_id to delete",
    )
    delete_file_id
    return (delete_file_id,)


@app.cell
def _():
    delete_password = mo.ui.text(label="Delete password", value="")
    delete_password
    return (delete_password,)


@app.cell
def _(conn, delete_file_id, delete_password):
    delete_button = mo.ui.run_button(label="Delete Selected Entry")
    delete_button
    return (delete_button,)


@app.cell
def _(conn, delete_button, delete_file_id, delete_password):
    mo.stop(not delete_button.value, mo.md("Click **Delete Selected Entry** to proceed."))
    mo.stop(delete_password.value.strip() != "12354", mo.md("Invalid password."))
    mo.stop(not delete_file_id.value, mo.md("No file selected."))

    with conn.cursor() as _cur:
        _cur.execute(
            "DELETE FROM measurement_file WHERE id = %s",
            (delete_file_id.value,),
        )
    conn.commit()
    mo.md("Entry deleted.")
    return


if __name__ == "__main__":
    app.run()
