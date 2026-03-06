Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoDir = Split-Path -Parent $scriptDir
Set-Location $repoDir

if (Test-Path ".\.venv\Scripts\python.exe") {
  & ".\.venv\Scripts\python.exe" ".\launcher\build_rew_dashboard.py"
} elseif (Get-Command uv -ErrorAction SilentlyContinue) {
  uv run python .\launcher\build_rew_dashboard.py
} else {
  python .\launcher\build_rew_dashboard.py
}
