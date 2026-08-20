$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) {
    $Python = 'python'
}
$LogDir = Join-Path $Root 'runtime\logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Out = Join-Path $LogDir 'bob-autopilot.out.log'
$Err = Join-Path $LogDir 'bob-autopilot.err.log'
$Proc = Start-Process -FilePath $Python -ArgumentList @('-u', (Join-Path $Root 'runtime\bob_autopilot_daemon.py')) -WorkingDirectory $Root -RedirectStandardOutput $Out -RedirectStandardError $Err -PassThru
Write-Output "BOB autopilot started PID=$($Proc.Id)"
Write-Output "Log: $Out"
