"""Restart only the recognized VisitReady Streamlit server on port 8502."""

import os
from pathlib import Path
import subprocess
import time


STOP_VISITREADY = r"""
$ErrorActionPreference = 'Stop'
$visitProcessIds = @(Get-NetTCPConnection -LocalPort 8502 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique)
foreach ($visitProcessId in $visitProcessIds) {
    $visitServer = Get-CimInstance Win32_Process -Filter "ProcessId = $visitProcessId"
    if ($null -eq $visitServer) { continue }
    if ($visitServer.Name -notmatch '^python.*\.exe$' -or
        $visitServer.CommandLine -notmatch '\s-m\s+streamlit\s+run\s+' -or
        $visitServer.CommandLine -notmatch 'app\.py') {
        throw 'Port 8502 belongs to an unrecognized application. Nothing was stopped.'
    }
}
foreach ($visitProcessId in $visitProcessIds) {
    Write-Host 'Stopping the current VisitReady server...'
    Stop-Process -Id $visitProcessId -ErrorAction SilentlyContinue
}
"""


def main() -> int:
    app_directory = Path(__file__).resolve().parent
    python = app_directory / ".venv" / "Scripts" / "python.exe"
    if not python.is_file() or not (app_directory / "app.py").is_file():
        print("Run this shortcut from your VisitReady project folder.")
        return 1
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", STOP_VISITREADY],
            check=False,
        )
    except OSError as exc:
        print(f"Unable to restart VisitReady: {exc}")
        return 1
    if result.returncode:
        print("VisitReady could not be restarted. See the message above.")
        return result.returncode
    time.sleep(0.5)
    os.chdir(app_directory)
    print("Starting VisitReady at http://localhost:8502/", flush=True)
    print("Leave this window open while using the app.", flush=True)
    try:
        os.execv(str(python), [str(python), "-m", "streamlit", "run", "app.py", "--server.port", "8502"])
    except OSError as exc:
        print(f"Unable to start VisitReady: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
