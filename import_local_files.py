import os
from pathlib import Path
import psycopg
import hashlib
import json
import uuid
from datetime import datetime

from project_paths import get_data_root, get_mdat_dir, get_json_dir


def get_db_conn():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "testingdb-postgres"),
        user=os.getenv("POSTGRES_USER", "rew_app"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
    )


def ensure_host(cur, host_name, base_url):
    cur.execute(
        "SELECT id FROM file_host WHERE host_name = %s AND base_url = %s",
        (host_name, base_url),
    )
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        "INSERT INTO file_host (host_name, base_url) VALUES (%s, %s) RETURNING id",
        (host_name, base_url),
    )
    return cur.fetchone()[0]


def file_already_indexed(cur, host_id, kind, relative_path):
    cur.execute(
        """
        SELECT 1
        FROM measurement_file
        WHERE host_id = %s AND kind = %s AND relative_path = %s
        LIMIT 1
        """,
        (host_id, kind, relative_path),
    )
    return cur.fetchone() is not None


def file_by_path(cur, host_id, relative_path):
    cur.execute(
        """
        SELECT id, kind
        FROM measurement_file
        WHERE host_id = %s AND relative_path = %s
        LIMIT 1
        """,
        (host_id, relative_path),
    )
    return cur.fetchone()


def iter_files(root_dir, pattern):
    return sorted(Path(root_dir).glob(pattern))


def sha256_file(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def parse_timestamp(value):
    if not value:
        return None
    raw = str(value)
    try:
        return datetime.fromisoformat(raw)
    except Exception:
        pass
    for fmt in ("%Y-%b-%d %H:%M:%S", "%Y-%b-%d %H:%M"):
        try:
            return datetime.strptime(raw, fmt)
        except Exception:
            continue
    return None


def parse_measurement_json(path, relative_path=None):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("Meta Data", {}) if isinstance(data, dict) else {}
    measurement_title = meta.get("Measurement") or data.get("filename")
    if not measurement_title:
        measurement_title = Path(path).stem
    measurement_uuid = meta.get("UUID") or meta.get("uuid")

    measurement_id = None
    if measurement_uuid:
        try:
            measurement_id = str(uuid.UUID(str(measurement_uuid)))
        except Exception:
            measurement_id = None
    if measurement_id is None:
        if relative_path:
            measurement_id = str(uuid.uuid5(uuid.NAMESPACE_URL, relative_path))
        else:
            measurement_id = str(uuid.uuid4())

    freq_values = data.get("Freq(Hz)") if isinstance(data, dict) else None
    spl_values = data.get("SPL(dB)") if isinstance(data, dict) else None

    def _summary(values):
        if not isinstance(values, list) or not values:
            return None, None, None
        try:
            float_values = [float(v) for v in values]
        except Exception:
            return None, None, None
        return min(float_values), max(float_values), len(float_values)

    freq_min, freq_max, freq_count = _summary(freq_values)
    spl_min, spl_max, spl_count = _summary(spl_values)

    return {
        "id": measurement_id,
        "title": measurement_title,
        "unit_type": None,
        "unit_number": None,
        "smoothing": meta.get("Smoothing"),
        "start_freq": meta.get("Start Frequency"),
        "end_freq": meta.get("End Frequency"),
        "ppo": data.get("ppo") if isinstance(data, dict) else None,
        "freq_step": data.get("freqStep") if isinstance(data, dict) else None,
        "rew_version": meta.get("REW Version"),
        "notes": meta.get("notes") or meta.get("Notes"),
        "measured_at": parse_timestamp(meta.get("Dated") or meta.get("Date")),
        "freq_min": freq_min,
        "freq_max": freq_max,
        "freq_count": freq_count,
        "spl_min": spl_min,
        "spl_max": spl_max,
        "spl_count": spl_count,
    }


def import_files(
    host_name="MrWorldWide",
    base_url="http://placeholder.local",
    conn=None,
    data_root_override=None,
):

    if data_root_override is not None:
        data_root = Path(data_root_override).expanduser().resolve()
        mdat_dir = data_root / "mdat"
        json_dir = data_root / "json"
    else:
        data_root = get_data_root()
        mdat_dir = get_mdat_dir()
        json_dir = get_json_dir()

    external_conn = conn is not None
    if conn is None:
        conn = get_db_conn()

    try:
        with conn.cursor() as cur:
            cur.execute(
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
            host_id = ensure_host(cur, host_name, base_url)

            # MDAT files
            for path in iter_files(mdat_dir, "*.mdat"):
                relative_path = str(path.relative_to(data_root)).replace("\\", "/")
                checksum = sha256_file(path)
                if file_already_indexed(cur, host_id, "mdat", relative_path):
                    cur.execute(
                        """
                        UPDATE measurement_file
                        SET file_size_bytes = %s,
                            checksum_sha256 = %s
                        WHERE host_id = %s AND kind = %s AND relative_path = %s
                        """,
                        (path.stat().st_size, checksum, host_id, "mdat", relative_path),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO measurement_file
                            (measurement_id, kind, host_id, relative_path, file_size_bytes, checksum_sha256)
                        VALUES
                            (NULL, %s, %s, %s, %s, %s)
                        """,
                        ("mdat", host_id, relative_path, path.stat().st_size, checksum),
                    )

            # JSON files
            for path in iter_files(json_dir, "**/*.json"):
                relative_path = str(path.relative_to(data_root)).replace("\\", "/")
                kind = "json"
                checksum = sha256_file(path)
                measurement_data = parse_measurement_json(path, relative_path=relative_path)

                measurement_id = measurement_data["id"]
                cur.execute(
                    """
                    INSERT INTO measurement
                        (id, title, unit_type, unit_number, smoothing,
                         start_freq, end_freq, ppo, freq_step, rew_version,
                         notes, measured_at,
                         freq_min, freq_max, freq_count,
                         spl_min, spl_max, spl_count)
                    VALUES
                        (%s, %s, %s, %s, %s,
                         %s, %s, %s, %s, %s,
                         %s, %s,
                         %s, %s, %s,
                         %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        unit_type = EXCLUDED.unit_type,
                        unit_number = EXCLUDED.unit_number,
                        smoothing = EXCLUDED.smoothing,
                        start_freq = EXCLUDED.start_freq,
                        end_freq = EXCLUDED.end_freq,
                        ppo = EXCLUDED.ppo,
                        freq_step = EXCLUDED.freq_step,
                        rew_version = EXCLUDED.rew_version,
                        notes = EXCLUDED.notes,
                        measured_at = EXCLUDED.measured_at,
                        freq_min = EXCLUDED.freq_min,
                        freq_max = EXCLUDED.freq_max,
                        freq_count = EXCLUDED.freq_count,
                        spl_min = EXCLUDED.spl_min,
                        spl_max = EXCLUDED.spl_max,
                        spl_count = EXCLUDED.spl_count
                    """,
                    (
                        measurement_id,
                        measurement_data["title"],
                        measurement_data["unit_type"],
                        measurement_data["unit_number"],
                        measurement_data["smoothing"],
                        measurement_data["start_freq"],
                        measurement_data["end_freq"],
                        measurement_data["ppo"],
                        measurement_data["freq_step"],
                        measurement_data["rew_version"],
                        measurement_data["notes"],
                        measurement_data["measured_at"],
                        measurement_data["freq_min"],
                        measurement_data["freq_max"],
                        measurement_data["freq_count"],
                        measurement_data["spl_min"],
                        measurement_data["spl_max"],
                        measurement_data["spl_count"],
                    ),
                )

                existing = file_by_path(cur, host_id, relative_path)
                if existing:
                    cur.execute(
                        """
                        UPDATE measurement_file
                        SET measurement_id = %s,
                            kind = %s,
                            file_size_bytes = %s,
                            checksum_sha256 = %s
                        WHERE host_id = %s AND relative_path = %s
                        """,
                        (
                            measurement_id,
                            kind,
                            path.stat().st_size,
                            checksum,
                            host_id,
                            relative_path,
                        ),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO measurement_file
                            (measurement_id, kind, host_id, relative_path, file_size_bytes, checksum_sha256)
                        VALUES
                            (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            measurement_id,
                            kind,
                            host_id,
                            relative_path,
                            path.stat().st_size,
                            checksum,
                        ),
                    )

        conn.commit()
    finally:
        if not external_conn:
            conn.close()


def main():
    import_files()


if __name__ == "__main__":
    main()
