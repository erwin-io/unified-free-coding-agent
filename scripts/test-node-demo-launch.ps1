# Windows acceptance: start, reuse, reject foreign ports, and report startup logs.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$helper = Join-Path $root "scripts\ensure-node-demo.ps1"
$source = Join-Path $root "examples\test-nodejs-web-app"
$node = (Get-Command node.exe -ErrorAction Stop).Source
$temp = Join-Path ([IO.Path]::GetTempPath()) ("unified-demo-launch-" + [guid]::NewGuid().ToString("N"))
$childIds = New-Object System.Collections.ArrayList

function Free-Port {
  $tcp = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
  $tcp.Start()
  $port = $tcp.LocalEndpoint.Port
  $tcp.Stop()
  return $port
}
function Started {
  param([int]$Port)
  try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $async = $tcp.BeginConnect("127.0.0.1",$Port,$null,$null)
    $ok = $async.AsyncWaitHandle.WaitOne(500)
    if ($ok) { $tcp.EndConnect($async) }
    $tcp.Close()
    return $ok
  } catch { return $false }
}
New-Item -ItemType Directory -Force -Path $temp | Out-Null
try {
  # Real Node full-stack demo, generated from repository source.
  $project = Join-Path $temp "project"
  Copy-Item -LiteralPath $source -Destination $project -Recurse
  $runtime = Join-Path $temp "runtime"
  $port1 = Free-Port
  & $helper -ProjectPath $project -RuntimePath $runtime -Port $port1 -WaitSeconds 15
  $demoPid = [int](Get-Content -LiteralPath (Join-Path $runtime "demo.pid") -Raw)
  [void]$childIds.Add($demoPid)
  $health = Invoke-RestMethod "http://127.0.0.1:$port1/api/health"
  if ($health.application -ne "test-nodejs-web-app") { throw "Demo API identity mismatch." }
  Write-Host "PASS: real Node demo started and passed health"
  & $helper -ProjectPath $project -RuntimePath $runtime -Port $port1
  $secondPid = [int](Get-Content -LiteralPath (Join-Path $runtime "demo.pid") -Raw)
  if ($secondPid -ne $demoPid) { throw "Healthy demo must reuse the existing process." }
  Write-Host "PASS: healthy server reused without duplicate"

  # Validate start/stop controls and identity verification.
  $appControl = Join-Path $root "scripts\app-control.ps1"
  & $appControl -Action status -ProjectPath $project -RuntimePath $runtime -Port $port1
  & $appControl -Action stop -ProjectPath $project -RuntimePath $runtime -Port $port1
  if (Started -Port $port1) { throw "Stop-app left the Node demo listening." }
  if (Test-Path -LiteralPath (Join-Path $runtime "demo.pid")) {
    throw "Successful stop left a tracked PID."
  }
  Write-Host "PASS: explicit app stop released the port without closing other services"
  & $appControl -Action start -ProjectPath $project -RuntimePath $runtime -Port $port1
  $restarted = [int](Get-Content -LiteralPath (Join-Path $runtime "demo.pid") -Raw)
  [void]$childIds.Add($restarted)
  if (-not (Started -Port $port1)) { throw "Start-app did not restart the demo." }
  Write-Host "PASS: explicit start brought the demo back online"



  # A foreign listener must remain running and must not be killed.
  $foreignDir = Join-Path $temp "foreign"
  New-Item -ItemType Directory -Force -Path $foreignDir | Out-Null
  $foreignSource = @'
const http = require("node:http");
http.createServer((_req,res)=>{
  res.writeHead(200,{"Content-Type":"application/json"});
  res.end(JSON.stringify({status:"ok",application:"other-app"}));
}).listen(Number(process.env.PORT),"127.0.0.1");
'@
  Set-Content -LiteralPath (Join-Path $foreignDir "foreign.cjs") -Value $foreignSource
  $port2 = Free-Port
  $savedPort = $env:PORT
  try {
    $env:PORT = [string]$port2
    $foreign = Start-Process -FilePath $node -WorkingDirectory $foreignDir -PassThru -ArgumentList @("foreign.cjs")
  } finally { [Environment]::SetEnvironmentVariable("PORT",$savedPort,"Process") }
  [void]$childIds.Add($foreign.Id)
  for ($i=0; $i -lt 15 -and -not (Started -Port $port2); $i++) {
    Start-Sleep -Milliseconds 400
  }
  if (-not (Started -Port $port2)) { throw "Failed to start foreign test listener." }
  $refused = $false
  try {
    & $helper -ProjectPath $project -RuntimePath $runtime -Port $port2 -WaitSeconds 3
  } catch {
    if ($_.Exception.Message -match "occupied") { $refused = $true }
    else { throw }
  }
  if (-not $refused) { throw "Expected explicit foreign port rejection." }
  if (-not (Get-Process -Id $foreign.Id -ErrorAction SilentlyContinue)) {
    throw "Foreign service was stopped unexpectedly."
  }
  Write-Host "PASS: port conflicts do not stop foreign services"

  $stopRejected = $false
  try {
    & $appControl -Action stop -ProjectPath $project -RuntimePath $runtime -Port $port2
  } catch {
    if ($_.Exception.Message -match "not a verified Node.js demo") {
      $stopRejected = $true
    } else { throw }
  }
  if (-not $stopRejected -or -not (Get-Process -Id $foreign.Id -ErrorAction SilentlyContinue)) {
    throw "The stop control must refuse to kill a different application on another port."
  }
  Write-Host "PASS: app stop never kills an unrelated Node process"


  # Failure logs must explain why the app crashed.
  $broken = Join-Path $temp "broken"
  New-Item -ItemType Directory -Force -Path $broken | Out-Null
  Set-Content -LiteralPath (Join-Path $broken "server.js") -Value "throw new Error('DEMO_TEST_FAILURE');"
  $brokenRuntime = Join-Path $temp "broken-runtime"
  $port3 = Free-Port
  $reported = $false
  try {
    & $helper -ProjectPath $broken -RuntimePath $brokenRuntime -Port $port3 -WaitSeconds 5
  } catch {
    if ($_.Exception.Message -match "DEMO_TEST_FAILURE") { $reported = $true }
    else { throw "Missing underlying Node error: $($_.Exception.Message)" }
  }
  if (-not $reported) { throw "Startup failure did not expose actionable Node error." }
  Write-Host "PASS: crashed server reports actual error and log"
} finally {
  foreach ($childId in $childIds) {
    $proc = Get-Process -Id $childId -ErrorAction SilentlyContinue
    if ($proc) { Stop-Process -Id $childId -Force -ErrorAction SilentlyContinue }
  }
  if (Test-Path -LiteralPath $temp) {
    Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
  }
}
