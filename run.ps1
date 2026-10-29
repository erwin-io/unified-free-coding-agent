param(
  [ValidateSet("start","router","worker","once","status","doctor","test","init-project")][string]$Mode="start",
  [ValidateSet("auto","node-web","angular-node","micropython","cpp")][string]$Stack="auto"
)
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
if (-not (Test-Path (Join-Path $project ".git"))) {
  $selectedStack = $Stack
  if ($selectedStack -eq "auto" -and $env:PROJECT_STACK) { $selectedStack = $env:PROJECT_STACK }
  if ((Split-Path $project -Leaf) -eq "test-nodejs-web-app" -and $selectedStack -eq "auto") {
    $selectedStack = "node-web"
  }
  if ($selectedStack -eq "auto") {
    throw "A new project needs a stack: set PROJECT_STACK in .env or run .\run.ps1 -Stack node-web|angular-node|micropython|cpp."
  }
  if ($selectedStack -notin @("node-web","angular-node","micropython","cpp")) {
    throw "Unsupported PROJECT_STACK: $selectedStack"
  }
  if ((Split-Path $project -Leaf) -eq "test-nodejs-web-app" -and $selectedStack -eq "node-web") {
    # Existing demo recovery logic also protects pre-existing unrelated files.
    & (Join-Path $root "scripts\bootstrap-test-project.ps1") -Target $project
  } else {
    & $python -m automation.scaffold --stack $selectedStack --target $project
    if ($LASTEXITCODE -ne 0) { throw "Project scaffold halted. No source was overwritten." }
  }
  if (-not (Test-Path (Join-Path $project ".git"))) { throw "Project scaffold did not create a verified Git baseline." }
}
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
if ($online -and $health.revision -ne "2026-10-30-capacity-recovery") {
  $routerPidFile = Join-Path $runtime "router.pid"
  if (-not (Test-Path $routerPidFile)) {
    throw "Router is outdated, but no local PID record exists. Close the router manually and retry."
  }
  $pidText = (Get-Content $routerPidFile -Raw).Trim()
  if ($pidText -notmatch "^[0-9]+$") { throw "Invalid local router PID record." }
  $routerPid = [int]$pidText
  $owned = Get-CimInstance Win32_Process -Filter "ProcessId = $routerPid" -ErrorAction SilentlyContinue
  if (-not $owned) { throw "Router PID record is stale. Close the process on port 4030 manually." }
  $expected = [IO.Path]::GetFullPath($python)
  $actual = [IO.Path]::GetFullPath($owned.ExecutablePath)
  if ($actual -ine $expected -or
      $owned.CommandLine -notlike "*uvicorn router.app:app*" -or
      $owned.CommandLine -notmatch "--port 4030") {
    throw "Port 4030 is not verified as this installation's router. Refusing to stop an unknown process."
  }
  Write-Host "Restarting the old router that belongs to this installation..." -ForegroundColor Cyan
  Stop-Process -Id $routerPid -ErrorAction Stop
  Start-Sleep -Seconds 2
  $online = $false
}
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
$vs=Get-Command code.cmd -ErrorAction SilentlyContinue
if (-not $vs) { $vs=Get-Command code -ErrorAction SilentlyContinue }
if ($vs) {
  try {
    $exts= & $vs.Source --list-extensions | Out-String
    if ($exts -notmatch "sst-dev.opencode-v2") {
      Write-Host "Installing OpenCode VS Code integration (beta)..." -ForegroundColor Cyan
      & $vs.Source --install-extension sst-dev.opencode-v2 | Out-Null
    }
    Start-Process -FilePath $vs.Source -ArgumentList @($project) | Out-Null
  } catch {
    Write-Warning "VS Code extension setup skipped; OpenCode CLI remains available."
  }
}
$demoManifest=Join-Path $project "package.json"
if (Test-Path $demoManifest) {
  $demo=Get-Content -LiteralPath $demoManifest -Raw | ConvertFrom-Json
  if ($demo.name -eq "unified-agent-test-web-app") {
    # Test failures must not block the editor: a coding agent may be needed to fix them.
    $checksPassed = $true
    Push-Location $project
    try {
      & $npm.Source test
      if ($LASTEXITCODE -ne 0) {
        $checksPassed = $false
        Write-Warning "Node demo API tests failed (exit $LASTEXITCODE). The agent can inspect and repair them."
      }
      & $npm.Source run lint
      if ($LASTEXITCODE -ne 0) {
        $checksPassed = $false
        Write-Warning "Node demo syntax checks failed (exit $LASTEXITCODE)."
      }
    } finally { Pop-Location }
    if (-not $checksPassed) {
      Write-Warning "Node checks are NOT passing. Do not treat the app as validated."
    }
    try {
      & (Join-Path $root "scripts\ensure-node-demo.ps1") -ProjectPath $project -RuntimePath $runtime -Port 3000 -OpenBrowser
    } catch {
      Write-Warning ("Node demo startup problem: " + $_.Exception.Message)
      Write-Warning "Continuing to OpenCode so you can inspect and fix the Node project. Router and project files are unaffected."
    }
  }
}
# Start the generated Angular + Node.js starter through the same launcher.
if (Test-Path $demoManifest) {
  $appManifest = Get-Content -LiteralPath $demoManifest -Raw | ConvertFrom-Json
  if ($appManifest.name -eq "unified-angular-node-starter") {
    if (-not (Test-Path (Join-Path $project "frontend\package.json"))) {
      throw "Angular project is missing frontend package.json."
    }
    $apiReady = $false
    $uiReady = $false
    try {
      $apiStatus = Invoke-RestMethod "http://127.0.0.1:3001/api/health" -TimeoutSec 2
      $apiReady = $apiStatus.service -eq "angular-node-api"
    } catch {}
    try {
      $frontendStatus = Invoke-WebRequest "http://127.0.0.1:4200/" -UseBasicParsing -TimeoutSec 2
      $uiReady = $frontendStatus.StatusCode -eq 200
    } catch {}
    if (-not $apiReady -and -not $uiReady) {
      Write-Host "Starting Angular + Node.js development servers..." -ForegroundColor Cyan
      $dev = Start-Process -FilePath "cmd.exe" -WorkingDirectory $project -PassThru -ArgumentList @("/d","/s","/c","npm run dev") -RedirectStandardOutput (Join-Path $runtime "angular.out.log") -RedirectStandardError (Join-Path $runtime "angular.err.log")
      $dev.Id | Set-Content (Join-Path $runtime "angular.pid")
      for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Seconds 2
        try {
          $apiStatus = Invoke-RestMethod "http://127.0.0.1:3001/api/health" -TimeoutSec 2
          $frontendStatus = Invoke-WebRequest "http://127.0.0.1:4200/" -UseBasicParsing -TimeoutSec 2
          $apiReady = $apiStatus.service -eq "angular-node-api"
          $uiReady = $frontendStatus.StatusCode -eq 200
          if ($apiReady -and $uiReady) { break }
        } catch {}
        if ($dev.HasExited) { break }
      }
    }
    if (-not $apiReady -or -not $uiReady) {
      throw "Angular UI or Node API not ready. Inspect .agent-runtime\angular.err.log and verify ports 4200/3001."
    }
    Write-Host "Angular UI: http://127.0.0.1:4200" -ForegroundColor Green
    Write-Host "Node API: http://127.0.0.1:3001/api/health" -ForegroundColor Green
    Start-Process "http://127.0.0.1:4200"
  }
}
Write-Host "Approved tasks: $project\.agent\BACKLOG.md" -ForegroundColor Cyan
Write-Host "Validation: existing project tests or .agent\validation.json" -ForegroundColor Cyan
Write-Host "Opening OpenCode in $project ..." -ForegroundColor Cyan
Set-Location $project
& $oc.Source $project
