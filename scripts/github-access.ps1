param([ValidateSet("connect","status")][string]$Action="status")
$ErrorActionPreference="Stop"
$root=Split-Path -Parent $PSScriptRoot
$gh=Get-Command gh.exe -ErrorAction SilentlyContinue
if (-not $gh) { throw "GitHub CLI is not installed. Run: winget install --id GitHub.cli -e" }
if ($Action -eq "connect") {
  Write-Host "Authorize GitHub CLI using your own browser. Credentials stay local." -ForegroundColor Cyan
  & $gh.Source auth login --hostname github.com --git-protocol https --web
  if ($LASTEXITCODE -ne 0) { throw "GitHub CLI authentication failed or was cancelled." }
}
& $gh.Source auth status --hostname github.com 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "GitHub CLI is not authenticated. Run CONNECT-GITHUB.bat once."
}
Write-Host "GitHub CLI authenticated. No token was printed or passed to cloud models." -ForegroundColor Green
$env:UNIFIED_AGENT_ROOT=$root
# The authenticated CLI is separate from the ChatGPT GitHub connector.
if ($env:PROJECT_PATH -and (Test-Path -LiteralPath (Join-Path $env:PROJECT_PATH ".git"))) {
  Push-Location $env:PROJECT_PATH
  try {
    $origin=& git remote get-url origin 2>$null
    if ($LASTEXITCODE -eq 0 -and $origin) {
      Write-Host ("Target project Git remote: " + $origin)
      & $gh.Source repo view --json nameWithOwner,defaultBranchRef,isPrivate
      if ($LASTEXITCODE -ne 0) {
        Write-Warning "Authenticated, but access to the project's GitHub repo is unverified."
      }
    } else {
      Write-Host "Target project has no origin remote. Remote GitHub access not yet configured."
    }
  } finally { Pop-Location }
}
