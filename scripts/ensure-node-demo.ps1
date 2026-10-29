param(
  [Parameter(Mandatory=$true)][string]$ProjectPath,
  [Parameter(Mandatory=$true)][string]$RuntimePath,
  [ValidateRange(1,65535)][int]$Port = 3000,
  [ValidateRange(2,60)][int]$WaitSeconds = 15,
  [switch]$OpenBrowser
)
# Reusable non-destructive launcher for the Node UI/API demo.
# An unavailable app must never prevent the coding agent from opening.
$ErrorActionPreference = "Stop"
$project = [IO.Path]::GetFullPath($ProjectPath)
$runtime = [IO.Path]::GetFullPath($RuntimePath)
if (-not (Test-Path -LiteralPath (Join-Path $project "server.js") -PathType Leaf)) {
  throw "No server.js exists in the selected Node.js project: $project"
}
$node = Get-Command node.exe -ErrorAction SilentlyContinue
if (-not $node) { throw "Node.js is not installed or node.exe is not on PATH." }
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
$address = "http://127.0.0.1:$Port"
$healthUrl = "$address/api/health"

function Test-DemoHealth {
  try {
    $result = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2 -ErrorAction Stop
    return ($result.status -eq "ok" -and $result.application -eq "test-nodejs-web-app")
  } catch { return $false }
}
function Test-Listening {
  $socket = New-Object System.Net.Sockets.TcpClient
  try {
    $async = $socket.BeginConnect("127.0.0.1", $Port, $null, $null)
    if (-not $async.AsyncWaitHandle.WaitOne(500)) { return $false }
    $socket.EndConnect($async)
    return $socket.Connected
  } catch { return $false }
  finally { $socket.Close() }
}
# Reuse a healthy server; don't start a duplicate process or alter it.
if (Test-DemoHealth) {
  Write-Host "Node.js demo API already running: $address" -ForegroundColor Green
  if ($OpenBrowser) { Start-Process $address }
  return
}
# Do not kill or restart a foreign server or a broken user-run process.
if (Test-Listening) {
  throw "Port $Port is occupied, but /api/health does not identify the expected demo. Nothing was stopped. Inspect the listening process."
}
$runId = (Get-Date -Format "yyyyMMdd-HHmmss") + "-" + [guid]::NewGuid().ToString("N").Substring(0,8)
$stdout = Join-Path $runtime ("demo-" + $runId + ".out.log")
$stderr = Join-Path $runtime ("demo-" + $runId + ".err.log")
$previousPort = [Environment]::GetEnvironmentVariable("PORT", "Process")
try {
  $env:PORT = [string]$Port
  $child = Start-Process -FilePath $node.Source -WorkingDirectory $project -PassThru -ArgumentList @("server.js") -RedirectStandardOutput $stdout -RedirectStandardError $stderr
} finally {
  [Environment]::SetEnvironmentVariable("PORT", $previousPort, "Process")
}
$child.Id | Set-Content -LiteralPath (Join-Path $runtime "demo.pid")
$stdout | Set-Content -LiteralPath (Join-Path $runtime "demo.latest.out.path")
$stderr | Set-Content -LiteralPath (Join-Path $runtime "demo.latest.err.path")
$started = $false
for ($attempt = 0; $attempt -lt $WaitSeconds; $attempt++) {
  if (Test-DemoHealth) { $started = $true; break }
  $child.Refresh()
  if ($child.HasExited) { break }
  Start-Sleep -Seconds 1
}
if (-not $started) {
  # The child is one this script just started. No unrelated process is touched.
  $child.Refresh()
  if (-not $child.HasExited) { Stop-Process -Id $child.Id -ErrorAction SilentlyContinue }
  $details = ""
  if (Test-Path -LiteralPath $stderr) {
    $details = (Get-Content -LiteralPath $stderr -Tail 16 -ErrorAction SilentlyContinue | Out-String).Trim()
  }
  if (-not $details -and (Test-Path -LiteralPath $stdout)) {
    $details = (Get-Content -LiteralPath $stdout -Tail 12 -ErrorAction SilentlyContinue | Out-String).Trim()
  }
  if (-not $details) { $details = "No startup log available." }
  throw "Node demo failed its health check at $healthUrl. Logs: $stderr. Recent output: $details"
}
Write-Host "Node.js UI and API ready: $address" -ForegroundColor Green
if ($OpenBrowser) { Start-Process $address }
