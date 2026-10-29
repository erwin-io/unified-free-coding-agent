param([ValidateSet("start","router","worker","once","status","doctor","test","init-project")][string]$Mode="start")
$ErrorActionPreference="Stop"
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Edit .env: API keys, PROJECT_PATH, and optional email settings; then rerun." -ForegroundColor Yellow
  Start-Process notepad.exe -ArgumentList (Join-Path $root ".env")
  exit 0
}
Get-Content ".env" | ForEach-Object {
  $line=$_.Trim()
  if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
    $pair=$line.Split("=",2)
    [Environment]::SetEnvironmentVariable($pair[0].Trim(),$pair[1].Trim().Trim('"').Trim("'"),"Process")
  }
}
$python=Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -m venv .venv }
  elseif (Get-Command python -ErrorAction SilentlyContinue) { & python -m venv .venv }
  else { throw "Install Python 3.10+ from https://www.python.org/downloads/" }
}
if (-not (Test-Path $python)) { throw "Python environment failed." }
$ver=& $python -c "import sys; print(sys.version_info.major*100+sys.version_info.minor)"
if ([int]$ver -lt 310) { throw "Python 3.10+ required." }
& $python -m pip install -q -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed." }
$runtime=Join-Path $root ".agent-runtime"
New-Item -ItemType Directory -Force $runtime | Out-Null
$env:OPENCODE_CONFIG=Join-Path $root "opencode.jsonc"
$env:OPENCODE_CONFIG_DIR=Join-Path $root ".opencode"
$project=if ($env:PROJECT_PATH) { [IO.Path]::GetFullPath($env:PROJECT_PATH) } else { $root }
if ($Mode -eq "test") { & $python -m unittest discover -s tests -v; exit $LASTEXITCODE }
if ($Mode -eq "router") { & $python -m uvicorn router.app:app --host 127.0.0.1 --port 4030; exit $LASTEXITCODE }
if ($Mode -eq "worker") { & $python -m automation.cli worker; exit $LASTEXITCODE }
if ($Mode -in @("once","status","doctor","init-project")) { & $python -m automation.cli $Mode; exit $LASTEXITCODE }
if (-not (Test-Path (Join-Path $project ".git"))) { throw "PROJECT_PATH must be a local Git repository: $project" }
& $python -m unittest discover -s tests -q
if ($LASTEXITCODE -ne 0) { throw "Self-tests failed. Router not started." }
& $python -m automation.cli init-project
$npm=Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npm) { throw "Install Node.js LTS from https://nodejs.org/" }
$installed= & $npm.Source list -g "@opencode/cli" --depth=0 2>&1 | Out-String
if ($installed -notmatch "@opencode/cli@") {
  Write-Host "Installing official OpenCode 2..." -ForegroundColor Cyan
  & $npm.Source install -g "@opencode/cli"
  if ($LASTEXITCODE -ne 0) { throw "OpenCode installation failed." }
}
$oc=Get-Command opencode.cmd -ErrorAction SilentlyContinue
if (-not $oc) { $oc=Get-Command opencode -ErrorAction SilentlyContinue }
if (-not $oc) { throw "OpenCode missing. Restart PowerShell and retry." }
$online=$false
try { $health=Invoke-RestMethod "http://127.0.0.1:4030/health" -TimeoutSec 2; $online=($health.status -eq "ok" -and $health.mode -eq "FREE_ONLY") } catch {}
if (-not $online) {
  Write-Host "Starting local gateway..." -ForegroundColor Cyan
  $p=Start-Process -FilePath $python -WorkingDirectory $root -PassThru -ArgumentList @("-m","uvicorn","router.app:app","--host","127.0.0.1","--port","4030") -RedirectStandardOutput (Join-Path $runtime "router.out.log") -RedirectStandardError (Join-Path $runtime "router.err.log")
  $p.Id | Set-Content (Join-Path $runtime "router.pid")
  Start-Sleep -Seconds 3
}
try {
  $health=Invoke-RestMethod "http://127.0.0.1:4030/health" -TimeoutSec 5
  if ($health.mode -ne "FREE_ONLY") { throw "Unexpected router process." }
} catch { throw "Router failed to start. Check .agent-runtime\router.err.log" }
Write-Host "Local free-only router online." -ForegroundColor Green
& $python -m automation.cli doctor
if ($env:AUTONOMOUS_ENABLED -eq "true" -and $env:AUTONOMOUS_AUTO_APPROVE -eq "true") {
  $wp=Start-Process -FilePath $python -WorkingDirectory $root -PassThru -ArgumentList @("-m","automation.cli","worker") -RedirectStandardOutput (Join-Path $runtime "worker.out.log") -RedirectStandardError (Join-Path $runtime "worker.err.log")
  $wp.Id | Set-Content (Join-Path $runtime "worker.pid")
  Write-Warning "Autonomous worker enabled; use ONLY a non-sensitive test repository."
}
Write-Host "Opening OpenCode in $project ..." -ForegroundColor Cyan
Set-Location $project
& $oc.Source $project
