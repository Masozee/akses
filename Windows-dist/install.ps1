# Windows PowerShell 5.1 or newer. Run as the user whose images will be synced.
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'This installer requires Windows.' }
$root = Join-Path $env:LOCALAPPDATA 'akses-sync'
$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$taskName = "Akses Sync - $sid"
# Probe real interpreters; Windows Store aliases can exist without Python installed.
$python = $null
foreach ($candidate in @('py', 'python', 'python3')) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $probeArgs = @('-c', 'import sys; assert sys.version_info >= (3, 10); print(sys.executable)')
        if ($candidate -eq 'py') { $probeArgs = @('-3') + $probeArgs }
        $found = & $candidate @probeArgs 2>$null
        if ($LASTEXITCODE -eq 0 -and $found) { $python = [string]($found | Select-Object -Last 1); break }
    }
}
if (-not $python) { throw 'Install Python 3.10+ from https://www.python.org/downloads/windows/ and rerun.' }
New-Item -ItemType Directory -Path $root -Force | Out-Null
# Protect credentials and code with a fresh ACL for this user and SYSTEM only.
$acl = New-Object Security.AccessControl.DirectorySecurity
$acl.SetAccessRuleProtection($true, $false)
foreach ($identity in @($sid, 'S-1-5-18')) {
    $account = New-Object Security.Principal.SecurityIdentifier($identity)
    $rule = New-Object Security.AccessControl.FileSystemAccessRule($account, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
    $acl.AddAccessRule($rule)
}
Set-Acl -LiteralPath $root -AclObject $acl
$configPath = Join-Path $root 'config.json'
if (-not (Test-Path $configPath)) {
    Write-Host 'Sync uploads images from your Desktop, Downloads, Documents and Pictures.'
    Write-Host 'This includes files in redirected OneDrive folders. Server filtering occurs AFTER upload.'
    Write-Host 'Use only your own computer and account. Installation does not upload images.'
    $url = Read-Host 'Server URL [https://apiresto.kapulaga.net]'
    if (-not $url) { $url = 'https://apiresto.kapulaga.net' }
    $uri = $null
    if (-not [Uri]::TryCreate($url, [UriKind]::Absolute, [ref]$uri) -or $uri.Scheme -ne 'https' -or -not $uri.Host) { throw 'A valid HTTPS URL is required.' }
    $email = Read-Host 'Account email'
    $secret = Read-Host 'Account password' -AsSecureString
    if (-not $email -or $secret.Length -eq 0) { throw 'Email and password are required.' }
    $folders = @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('MyDocuments'), [Environment]::GetFolderPath('MyPictures'))
    $shellFolders = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'
    $downloads = $shellFolders.'{374DE290-123F-4565-9164-39C4925E467B}'
    if ($downloads) { $folders += [Environment]::ExpandEnvironmentVariables($downloads) }
    else { $folders += Join-Path $env:USERPROFILE 'Downloads' }
    $credential = New-Object Management.Automation.PSCredential($email, $secret)
    $config = @{ base_url = $url.TrimEnd('/'); email = $email; password = $credential.GetNetworkCredential().Password; scan_dirs = @($folders | Where-Object { $_ } | Select-Object -Unique) }
    $config | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $configPath -Encoding UTF8
    $config = $null; $credential = $null; $secret = $null
} else { Write-Host "Keeping configuration: $configPath" }
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing -and $existing.State -eq 'Running') { throw 'Sync is running. Stop it in Task Scheduler before updating.' }
& $python -m venv (Join-Path $root 'venv')
if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed.' }
$venvPython = Join-Path $root 'venv\Scripts\python.exe'
& $venvPython -m pip install requests
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
Copy-Item (Join-Path $PSScriptRoot '..\Sync-dist\Sync.app\Contents\Resources\sync.py') $root -Force
Copy-Item (Join-Path $PSScriptRoot 'run-sync.py') $root -Force
Copy-Item (Join-Path $PSScriptRoot 'uninstall.ps1') $root -Force
$runner = Join-Path $root 'run-sync.py'
$action = New-ScheduledTaskAction -Execute $venvPython -Argument ('"' + $runner + '"') -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Daily -At '03:00'
$principal = New-ScheduledTaskPrincipal -UserId $sid -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 12)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Back up this user''s configured image folders to their akses server daily at 03:00.' -Force | Out-Null
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Programs')) 'Akses Sync.lnk'))
$link.TargetPath = $venvPython
$link.Arguments = '"' + $runner + '"'
$link.WorkingDirectory = $root
$link.Description = 'Upload images to your configured akses server'
$link.Save()
Write-Host "Installed in $root. Start menu: Akses Sync. Daily schedule: 03:00 while logged in and awake."
Write-Host 'No images uploaded during installation. Credentials are stored locally with a restricted Windows ACL.'
Write-Host "Log: $root\sync.log"
Write-Host "Preview without uploading images: & `"$venvPython`" `"$runner`" --dry-run"
