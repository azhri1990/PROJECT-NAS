param(
    [ValidateSet('status','stop','install','uninstall')]
    [string]$Action = 'status'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PidLock = Join-Path $Root 'runtime\bob-autopilot.pidlock'
$TaskName = 'PROJECT-NAS-BOB-Autopilot'

switch ($Action) {
    'status' {
        $StatusPath = Join-Path $Root 'runtime\bob-autopilot-status.json'
        if (Test-Path $StatusPath) {
            Get-Content $StatusPath -Raw
        } else {
            Write-Output 'BOB_AUTOPILOT=NOT_RUNNING'
        }
    }
    'stop' {
        if (Test-Path $PidLock) {
            $Pid = (Get-Content $PidLock -Raw).Trim()
            if ($Pid -match '^\d+$') {
                Stop-Process -Id ([int]$Pid) -Force -ErrorAction SilentlyContinue
            }
            Remove-Item $PidLock -Force -ErrorAction SilentlyContinue
        }
        Write-Output 'BOB_AUTOPILOT=STOPPED'
    }
    'install' {
        $Launcher = Join-Path $Root 'tools\start-bob-autopilot.ps1'
        $Command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$Launcher`""
        schtasks.exe /Create /TN $TaskName /SC ONLOGON /TR $Command /F | Out-Null
        Write-Output "BOB_AUTOPILOT=INSTALLED TASK=$TaskName"
    }
    'uninstall' {
        schtasks.exe /Delete /TN $TaskName /F | Out-Null
        Write-Output "BOB_AUTOPILOT=UNINSTALLED TASK=$TaskName"
    }
}
