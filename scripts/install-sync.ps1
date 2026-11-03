# Download and install for the current Windows user.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$work = Join-Path ([IO.Path]::GetTempPath()) ('akses-sync-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $work | Out-Null
try {
    $zip = Join-Path $work 'sync.zip'
    Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/Masozee/akses/archive/refs/heads/main.zip' -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $work
    & (Join-Path $work 'akses-main\Windows-dist\install.ps1')
} finally {
    Remove-Item -LiteralPath $work -Recurse -Force
}
