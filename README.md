# REW Marimo Testing

This repository contains two marimo notebooks launched from the marimo browser dashboard:
1. `notebooks/REW_interface.py` for REW automation + LEA calibration.
2. `notebooks/marimo_db_app.py` for browsing/importing measurement data in Postgres.

## How To Launch Through The Dashboard
1. Install dependencies:
```bash
uv sync
```
2. Start marimo in notebook tile view for this repo:
```bash
uv run marimo edit notebooks
```
3. In the browser dashboard, open:
```text
REW Sweep + Export Tool
REW Metadata Dashboard
```

## What Each Program Does
1. `notebooks/REW_interface.py`
Connects to REW API, runs LEA I/O calibration from a WebSocket LEA address, runs sine/stepped-sine measurement flows, and saves `.mdat` and JSON outputs.

2. `notebooks/marimo_db_app.py`
Connects to Postgres, imports local `data/mdat` and `data/json` files into DB tables, and displays/filters measurement metadata.

3. Core modules used by notebooks
`REWAutomation.py`: REW HTTP API wrapper.  
`LEA_controls.py`: LEA WebSocket command/response handling.  
`REW_measurements.py`: measurement + calibration workflow logic.  
`import_local_files.py`: filesystem-to-Postgres import.  
`project_paths.py`: data-root and `.env` path resolution.

## Per-User Variables To Update (Private Config)
Use a private `.env` file at repo root. Do not commit real secrets.

Variables each user should set:
1. `LEA_IP`
LEA amplifier IP (no `ws://`, no port), for example `192.168.4.73`.  
Note: current calibration notebook uses the on-page `LEA WebSocket Address` field; keep `LEA_IP` in `.env` for consistency/documentation.

2. `POSTGRES_HOST`
Postgres server host (for local Docker, typically `localhost`).

3. `POSTGRES_PORT`
Postgres port (typically `5432`).

4. `POSTGRES_DB`
Database name used by the dashboard import/view app.

5. `POSTGRES_USER`
Database username.

6. `POSTGRES_PASSWORD`
Database password.

7. `REW_DATA_DIR` (optional)
Shared data directory override. If omitted, project-local `data/` is used.

Suggested `.env` template:
```env
LEA_IP=192.168.4.73
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=testingdb-postgres
POSTGRES_USER=rew_app
POSTGRES_PASSWORD=change_me
REW_DATA_DIR=/absolute/path/to/rew_data
```

## Data Storage Behavior
If `REW_DATA_DIR` is set and writable, the app stores data under:
`mdat/`, `json/`, `txt/`, and `stepped-sine/`.

If `REW_DATA_DIR` is not set, the project falls back to:
`data/mdat`, `data/json`, `data/txt`, and `data/stepped-sine`.

## Postgres Service (Optional Docker)
Start Postgres with:
```bash
docker compose up -d postgres
```

This uses `.env` values via `docker-compose.yml`.

## Notes
1. `main.py` is currently empty and not used as an app entrypoint.
2. `.DS_Store` files are ignored by git.
