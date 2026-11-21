param(
    [string]$Distribution = 'Ubuntu',
    [Parameter(Mandatory = $true)][string]$WslUser,
    [Parameter(Mandatory = $true)][string]$WslRepo,
    [Parameter(Mandatory = $true)][string]$WslPython
)

$ErrorActionPreference = 'Stop'
$taskName = 'T1.AI-DataOps'
if ((Get-TimeZone).Id -ne 'China Standard Time') {
    throw 'The daily 14:30 trigger requires the Windows China Standard Time zone.'
}
foreach ($value in @($Distribution, $WslUser, $WslRepo, $WslPython)) {
    if ($value -match '[\x00-\x1f"]') {
        throw 'WSL task arguments must not contain quotes or control characters.'
    }
}

$identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing -and $existing.Description -ne 'T1.AI managed data collection in WSL') {
    throw "The task name $taskName already belongs to another application."
}

$runner = Join-Path $PSScriptRoot 'run-data-ops.ps1'
$arguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -Distribution "{1}" -WslUser "{2}" -WslRepo "{3}" -WslPython "{4}"' -f $runner, $Distribution, $WslUser, $WslRepo, $WslPython
$action = New-ScheduledTaskAction -Execute "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" `
    -Argument $arguments -WorkingDirectory (Split-Path -Parent $PSScriptRoot)
$trigger = New-ScheduledTaskTrigger -Daily -At '14:30'
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName $taskName -Description 'T1.AI managed data collection in WSL' `
    -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Get-ScheduledTask -TaskName $taskName | Select-Object TaskName, State
