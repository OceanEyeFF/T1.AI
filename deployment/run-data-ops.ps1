param(
    [Parameter(Mandatory = $true)][string]$Distribution,
    [Parameter(Mandatory = $true)][string]$WslUser,
    [Parameter(Mandatory = $true)][string]$WslRepo,
    [Parameter(Mandatory = $true)][string]$WslPython
)

$repo = Split-Path -Parent $PSScriptRoot
$runDirectory = Join-Path $repo 'workspace\runs\data_ops'
New-Item -ItemType Directory -Path $runDirectory -Force -ErrorAction Stop | Out-Null
$log = Join-Path $runDirectory 'task.log'
"Started $(Get-Date -Format o)" | Set-Content -LiteralPath $log -Encoding UTF8

$wsl = Join-Path $env:WINDIR 'System32\wsl.exe'
& $wsl -d $Distribution -u $WslUser --cd $WslRepo --exec $WslPython -m scripts.data_ops daily 2>&1 |
    ForEach-Object { ([string]$_ -replace '\x00', '') } |
    Out-File -LiteralPath $log -Encoding utf8 -Append
$result = $LASTEXITCODE
"Finished $(Get-Date -Format o) with exit code $result" |
    Out-File -LiteralPath $log -Encoding utf8 -Append
exit $result
