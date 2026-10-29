# Windows acceptance tests for safe, repeatable demo initialization.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$bootstrap = Join-Path $root "scripts\bootstrap-test-project.ps1"
$source = Join-Path $root "examples\test-nodejs-web-app"
$working = Join-Path ([IO.Path]::GetTempPath()) ("unified-demo-" + [guid]::NewGuid().ToString("N"))
try {
  # Fresh folder: generate and initialize Git.
  $fresh = Join-Path $working "fresh\test-nodejs-web-app"
  & $bootstrap -Target $fresh
  if (-not (Test-Path -LiteralPath (Join-Path $fresh ".git"))) {
    throw "Fresh demo did not initialize Git."
  }
  $commit = & git -C $fresh rev-parse HEAD
  if ($LASTEXITCODE -ne 0 -or -not $commit) { throw "Fresh demo baseline commit missing." }
  Write-Host "PASS: fresh demo"

  # Interrupted copy: preserve matching files, fill missing files, then initialize Git.
  $partial = Join-Path $working "partial\test-nodejs-web-app"
  New-Item -ItemType Directory -Force -Path $partial | Out-Null
  Copy-Item -LiteralPath (Join-Path $source "package.json") -Destination (Join-Path $partial "package.json")
  Copy-Item -LiteralPath (Join-Path $source "server.js") -Destination (Join-Path $partial "server.js")
  $before = (Get-FileHash -LiteralPath (Join-Path $partial "server.js") -Algorithm SHA256).Hash
  & $bootstrap -Target $partial
  $after = (Get-FileHash -LiteralPath (Join-Path $partial "server.js") -Algorithm SHA256).Hash
  if ($before -ne $after) { throw "Existing demo files were modified." }
  if (-not (Test-Path -LiteralPath (Join-Path $partial ".git"))) {
    throw "Interrupted demo was not recovered."
  }
  Write-Host "PASS: interrupted copy safely resumed"

  # Unknown data: reject without altering it or initializing Git.
  $unknown = Join-Path $working "unknown\test-nodejs-web-app"
  New-Item -ItemType Directory -Force -Path $unknown | Out-Null
  $unknownFile = Join-Path $unknown "do-not-touch.txt"
  Set-Content -LiteralPath $unknownFile -Value "personal work" -NoNewline
  $rejected = $false
  try { & $bootstrap -Target $unknown } catch {
    if ($_.Exception.Message -match "Existing unknown file") { $rejected = $true }
    else { throw }
  }
  if (-not $rejected -or -not (Test-Path -LiteralPath $unknownFile) -or
      (Test-Path -LiteralPath (Join-Path $unknown ".git"))) {
    throw "Unknown files were not handled safely."
  }
  Write-Host "PASS: unknown existing files left untouched"

  # Edited template: reject instead of replacing user modifications.
  $modified = Join-Path $working "modified\test-nodejs-web-app"
  New-Item -ItemType Directory -Force -Path $modified | Out-Null
  $modifiedFile = Join-Path $modified "server.js"
  Set-Content -LiteralPath $modifiedFile -Value "console.log('user-modified')" -NoNewline
  $rejected = $false
  try { & $bootstrap -Target $modified } catch {
    if ($_.Exception.Message -match "differs from the demo template") { $rejected = $true }
    else { throw }
  }
  if (-not $rejected -or (Test-Path -LiteralPath (Join-Path $modified ".git"))) {
    throw "User modifications were not protected."
  }
  Write-Host "PASS: modified files left untouched"
} finally {
  if (Test-Path -LiteralPath $working) {
    Remove-Item -LiteralPath $working -Recurse -Force
  }
}
