param(
  [ValidateSet("start","stop","status")][string]$Action = "status",
  [Parameter(Mandatory=$true)][string]$ProjectPath,
  [Parameter(Mandatory=$true)][string]$RuntimePath,
  [ValidateRange(1,65535)][int]$Port = 3000,
  [switch]$AllowUntracked
)
$ErrorActionPreference = "Stop"
$project = [IO.Path]::GetFullPath($ProjectPath)
$runtime = [IO.Path]::GetFullPath($RuntimePath)
$scriptPath = Join-Path $project "server.js"
if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
  throw "This project does not contain server.js: $project"
}
if ($Port -eq 4030) { throw "Port 4030 is reserved for the AI router." }
if ($Action -eq "start") {
  & (Join-Path $PSScriptRoot "ensure-node-demo.ps1") -ProjectPath $project -RuntimePath $runtime -Port $Port
  return
}
$listening = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
  Where-Object { $_.LocalAddress -in @("127.0.0.1","0.0.0.0","::1","::") })
$owners = @($listening | Select-Object -ExpandProperty OwningProcess -Unique)
if ($owners.Count -eq 0) {
  Write-Host "STOPPED: No application listening on port $Port."
  return
}
if ($owners.Count -ne 1) { throw "Ambiguous listening processes. No process stopped." }
$targetPid = [int]$owners[0]
$proc = Get-CimInstance Win32_Process -Filter "ProcessId = $targetPid" -ErrorAction SilentlyContinue
if (-not $proc) { throw "Process disappeared. Retry the command." }
$command = [string]$proc.CommandLine
$exe = [string]$proc.ExecutablePath
if ([IO.Path]::GetFileName($exe) -ine "node.exe" -or $command -notlike "*server.js*") {
  throw "PID $targetPid is not a verified Node.js demo. No process stopped."
}
$healthOk = $false
try {
  $health = Invoke-RestMethod "http://127.0.0.1:$Port/api/health" -TimeoutSec 2
  $healthOk = $health.application -eq "test-nodejs-web-app" -and $health.status -eq "ok"
} catch {}
$pidFile = Join-Path $runtime "demo.pid"
$tracked = $false
if (Test-Path -LiteralPath $pidFile) {
  $saved = (Get-Content -LiteralPath $pidFile -Raw).Trim()
  if ($saved -match "^[0-9]+$") { $tracked = ([int]$saved -eq $targetPid) }
}
$exact = $command.ToLowerInvariant().Contains(
  [IO.Path]::GetFullPath($scriptPath).ToLowerInvariant())
$verified = $exact -or ($tracked -and $healthOk)
if ($Action -eq "status") {
  Write-Host "Port: $Port | PID: $targetPid | Project: $project"
  Write-Host "Health: $healthOk | tracked: $tracked | exact source path: $exact"
  Write-Host "Command: $command"
  Write-Host "Safe to stop without an override: $verified"
  return
}
if (-not $verified -and -not ($AllowUntracked -and $healthOk)) {
  throw "Refusing to stop unknown Node PID $targetPid. Inspect -Action status. If the process is yours, explicitly authorize -AllowUntracked."
}
if (-not $verified) {
  Write-Warning "Stopping an untracked Node process at explicit owner request."
}
Write-Host "Stopping only the selected Node app PID $targetPid..." -ForegroundColor Cyan
Stop-Process -Id $targetPid -ErrorAction Stop
for ($attempt = 0; $attempt -lt 20; $attempt++) {
  Start-Sleep -Milliseconds 250
  $remaining = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.OwningProcess -eq $targetPid })
  if ($remaining.Count -eq 0) { break }
}
$remaining = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
  Where-Object { $_.OwningProcess -eq $targetPid })
if ($remaining.Count -gt 0) { throw "PID $targetPid is still listening; stop not verified." }
if ($tracked -and (Test-Path -LiteralPath $pidFile)) {
  Remove-Item -LiteralPath $pidFile -Force
}
Write-Host "STOPPED PID $targetPid. AI router and other Node apps were not touched." -ForegroundColor Green
