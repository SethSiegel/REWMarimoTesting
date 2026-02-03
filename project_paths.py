from pathlib import Path
import os

_dotenv_loaded = False


def _load_dotenv():
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    repo_root = get_repo_root()
    dotenv_path = repo_root / ".env"
    if not dotenv_path.exists():
        _dotenv_loaded = True
        return
    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
    _dotenv_loaded = True


def get_repo_root(start_path=None):
    start = Path(start_path or __file__).resolve()
    for parent in [start, *start.parents]:
        if (parent / ".git").exists():
            return parent
    return start.parent


def get_data_root():
    _load_dotenv()
    env_path = os.getenv("REW_DATA_DIR")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return get_repo_root() / "data"


def get_mdat_dir():
    return get_data_root() / "mdat"


def get_json_dir():
    return get_data_root() / "json"


def get_txt_dir():
    return get_data_root() / "txt"


def get_stepped_sine_dir():
    return get_data_root() / "stepped-sine"


def ensure_data_dirs():
    for directory in (get_mdat_dir(), get_json_dir(), get_txt_dir(), get_stepped_sine_dir()):
        directory.mkdir(parents=True, exist_ok=True)
