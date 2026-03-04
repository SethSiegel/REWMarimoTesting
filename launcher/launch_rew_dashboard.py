from __future__ import annotations

import shutil
import subprocess
import sys
import traceback
from pathlib import Path


def _venv_paths(repo_dir: Path) -> tuple[Path, Path]:
    if sys.platform == "win32":
        return (
            repo_dir / ".venv" / "Scripts" / "marimo.exe",
            repo_dir / ".venv" / "Scripts" / "python.exe",
        )
    return (
        repo_dir / ".venv" / "bin" / "marimo",
        repo_dir / ".venv" / "bin" / "python",
    )


def _find_repo_dir() -> Path:
    candidates: list[Path] = []

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.extend([exe_dir, exe_dir.parent, Path.cwd()])
    else:
        script_dir = Path(__file__).resolve().parent
        candidates.extend([script_dir, script_dir.parent, Path.cwd()])

    seen = set()
    unique_candidates: list[Path] = []
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            unique_candidates.append(candidate)

    for candidate in unique_candidates:
        if (candidate / "notebooks").is_dir() and (candidate / "pyproject.toml").exists():
            return candidate

    return unique_candidates[0]


def _pick_command(repo_dir: Path) -> list[str] | None:
    venv_marimo, venv_python = _venv_paths(repo_dir)
    if venv_marimo.exists():
        return [str(venv_marimo), "run", "notebooks", "--sandbox"]

    if venv_python.exists():
        return [str(venv_python), "-m", "marimo", "run", "notebooks", "--sandbox"]

    uv_path = shutil.which("uv")
    if uv_path is not None:
        return [uv_path, "run", "marimo", "run", "notebooks", "--sandbox"]

    marimo_path = shutil.which("marimo")
    if marimo_path is not None:
        return [marimo_path, "run", "notebooks", "--sandbox"]

    return None


def _write_debug_log(repo_dir: Path, lines: list[str]) -> None:
    try:
        log_dir = repo_dir / "launcher"
        if not log_dir.exists():
            log_dir = repo_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "launcher_error.log"
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[INFO] Wrote debug log: {log_path}")
    except Exception:
        pass


def _pause_on_failure(exit_code: int) -> None:
    # Keep the window open on double-clicked .exe failures.
    if getattr(sys, "frozen", False) and exit_code != 0:
        print("")
        print("Launcher failed. Press Enter to close this window...")
        try:
            input()
        except EOFError:
            pass


def main() -> int:
    repo_dir = _find_repo_dir()
    expected_marimo, expected_python = _venv_paths(repo_dir)
    cmd = _pick_command(repo_dir)
    if cmd is None:
        print("[ERROR] Could not find marimo launcher.")
        print("Expected one of:")
        print(f"  - {expected_marimo}")
        print(f"  - {expected_python} -m marimo")
        print("  - uv in PATH")
        print("  - marimo in PATH")
        _write_debug_log(
            repo_dir,
            [
                "Could not find marimo launcher.",
                f"repo_dir={repo_dir}",
                f"expected_marimo={expected_marimo}",
                f"expected_python={expected_python}",
                f"uv_path={shutil.which('uv')}",
                f"marimo_path={shutil.which('marimo')}",
                f"cwd={Path.cwd()}",
                f"platform={sys.platform}",
                f"frozen={getattr(sys, 'frozen', False)}",
            ],
        )
        return 1

    print("Launching marimo dashboard...")
    print(" ".join(cmd))
    print(f"Working directory: {repo_dir}")

    try:
        rc = subprocess.call(cmd, cwd=repo_dir)
        if rc != 0:
            print(f"[ERROR] marimo exited with code {rc}.")
            _write_debug_log(
                repo_dir,
                [
                    f"marimo exited with code {rc}",
                    f"cmd={cmd}",
                    f"repo_dir={repo_dir}",
                    f"cwd={Path.cwd()}",
                    f"frozen={getattr(sys, 'frozen', False)}",
                ],
            )
        return rc
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"[ERROR] Failed to launch dashboard: {exc}")
        _write_debug_log(
            repo_dir,
            [
                f"Failed to launch dashboard: {exc}",
                f"cmd={cmd}",
                f"repo_dir={repo_dir}",
                f"cwd={Path.cwd()}",
                "traceback:",
                traceback.format_exc(),
            ],
        )
        return 1


if __name__ == "__main__":
    _exit_code = main()
    _pause_on_failure(_exit_code)
    sys.exit(_exit_code)
