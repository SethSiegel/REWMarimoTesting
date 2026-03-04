from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    here = Path(__file__).resolve()
    candidates = [here.parent, *here.parents]
    for candidate in candidates:
        if (candidate / "pyproject.toml").exists() and (candidate / "notebooks").is_dir():
            return candidate
    return here.parent


def _artifact_name() -> str:
    return "REW_Dashboard_Launcher.exe" if sys.platform == "win32" else "REW_Dashboard_Launcher"


def _build_command() -> list[str]:
    uv = shutil.which("uv")
    repo = _project_root()
    launcher_dir = repo / "launcher"
    common = [
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        "REW_Dashboard_Launcher",
        "--distpath",
        str(launcher_dir / "dist"),
        "--workpath",
        str(launcher_dir / "build"),
        "--specpath",
        str(launcher_dir),
        str(repo / "launcher" / "launch_rew_dashboard.py"),
    ]
    if uv:
        return [uv, "tool", "run", "pyinstaller", *common]
    return [sys.executable, "-m", "PyInstaller", *common]


def main() -> int:
    repo = _project_root()
    cmd = _build_command()

    print("Building REW dashboard launcher...")
    print(f"Repo: {repo}")
    print(f"Command: {' '.join(cmd)}")

    try:
        rc = subprocess.call(cmd, cwd=repo)
    except Exception as exc:
        print(f"[ERROR] Build failed before execution: {exc}")
        return 1

    if rc != 0:
        print(f"[ERROR] Build failed with exit code {rc}.")
        return rc

    artifact = _artifact_name()
    dist_path = repo / "launcher" / "dist" / artifact
    launcher_copy_path = repo / "launcher" / artifact

    if not dist_path.exists():
        print(f"[ERROR] Build completed but artifact not found: {dist_path}")
        return 1

    shutil.copy2(dist_path, launcher_copy_path)
    print("")
    print(f"Build complete: {dist_path}")
    print(f"Copied to: {launcher_copy_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
