# Reflection Lab bootstrap (Windows PowerShell)
# Creates .venv, installs the Python packages, then runs the environment check.
#
#   powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1            # normal
#   powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1 -WithCli   # also install the litert-lm CLI
#
# Safe to run again: it skips what already exists.

param([switch]$WithCli)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Step($msg) { Write-Host "`n>> $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "   OK  $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "   !!  $msg" -ForegroundColor Yellow }

Step "Looking for Python 3.12 or 3.11"
$py = $null
foreach ($v in @("3.12", "3.11", "3.13")) {
    try {
        $out = & py "-$v" -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) { $py = @("py", "-$v"); Ok "found Python $v at $out"; break }
    } catch {}
}
if (-not $py) {
    try {
        $ver = & python -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($ver -and [version]$ver -ge [version]"3.11") { $py = @("python"); Ok "using python $ver" }
    } catch {}
}
if (-not $py) {
    Warn "Python 3.11+ not found. Install it with:  winget install Python.Python.3.12"
    exit 1
}

Step "Creating virtual environment .venv"
if (Test-Path ".venv\Scripts\python.exe") { Ok ".venv already exists" }
else {
    if ($py.Count -gt 1) { & $py[0] $py[1] -m venv .venv } else { & $py[0] -m venv .venv }
    Ok "created .venv"
}
$vpy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

Step "Upgrading pip"
& $vpy -m pip install --upgrade pip

Step "Installing packages from requirements.txt (litert-lm-api, huggingface_hub, rich, psutil)"
& $vpy -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Warn "pip install failed - see the messages above"; exit 1 }
Ok "packages installed"

if ($WithCli) {
    Step "Installing the litert-lm command-line tool (optional fallback runtime)"
    & $vpy -m pip install litert-lm
    if ($LASTEXITCODE -ne 0) { Warn "litert-lm CLI install failed (optional, you can ignore this)" }
}

Step "Environment check"
& $vpy scripts\check_env.py --probe-api

Write-Host "`nDone. Activate the environment in new terminals with:  .\.venv\Scripts\Activate.ps1" -ForegroundColor Green
