# Run a project script in its own PowerShell window so you can watch it live.
# Claude Code uses this for long jobs (experiments, downloads, scans).
#
#   .\open_window.ps1 scripts\run_experiment.py --limit 2
#   .\open_window.ps1 scripts\get_models.py --required --yes

param([Parameter(ValueFromRemainingArguments = $true)][string[]]$ScriptArgs)

$root = $PSScriptRoot
$vpy = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $vpy)) { Write-Host "No .venv yet - run bootstrap.ps1 first" -ForegroundColor Yellow; exit 1 }

$joined = ($ScriptArgs | ForEach-Object { if ($_ -match '\s') { "'$_'" } else { $_ } }) -join ' '
$cmd = @"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
`$env:PYTHONIOENCODING = 'utf-8'
`$host.UI.RawUI.WindowTitle = 'Reflection Lab - $($ScriptArgs[0])'
Set-Location '$root'
& '$vpy' $joined
Write-Host "``nFinished (exit code `$LASTEXITCODE). You can close this window." -ForegroundColor Green
"@

# -EncodedCommand avoids every quoting problem with spaces, quotes and newlines.
$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($cmd))
Start-Process powershell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $encoded)
Write-Host "Opened a new window: python $joined" -ForegroundColor Cyan
