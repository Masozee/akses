param([switch]$Purge)
$ErrorActionPreference = 'Stop'
$root = Join-Path $env:LOCALAPPDATA 'akses-sync'
$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$taskName = "Akses Sync - $sid"
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask -TaskName $taskName
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}
$link = Join-Path ([Environment]::GetFolderPath('Programs')) 'Akses Sync.lnk'
Remove-Item -LiteralPath $link -Force -ErrorAction SilentlyContinue
if ($Purge) { Remove-Item -LiteralPath $root -Recurse -Force }
else {
    foreach ($name in @('venv', 'sync.py', 'run-sync.py')) {
        $path = Join-Path $root $name
        if (Test-Path $path) { Remove-Item -LiteralPath $path -Recurse -Force }
    }
    Write-Host "Kept configuration, cache and logs in $root. Use -Purge to remove all local data."
}
Write-Host 'Removed Akses Sync and its schedule.'
