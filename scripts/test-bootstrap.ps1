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

  # Extra data: preserve without staging, even when there are no demo files yet.
  $unknown = Join-Path $working "unknown\test-nodejs-web-app"
  New-Item -ItemType Directory -Force -Path $unknown | Out-Null
  $unknownFile = Join-Path $unknown "filestructure.txt"
  Set-Content -LiteralPath $unknownFile -Value "personal work" -NoNewline
  $beforeHash = (Get-FileHash -LiteralPath $unknownFile -Algorithm SHA256).Hash
  & $bootstrap -Target $unknown
  $afterHash = (Get-FileHash -LiteralPath $unknownFile -Algorithm SHA256).Hash
  if ($beforeHash -ne $afterHash -or
      -not (Test-Path -LiteralPath (Join-Path $unknown ".git")) -or
      -not (Test-Path -LiteralPath (Join-Path $unknown "server.js"))) {
    throw "Extra file preservation or demo initialization failed."
  }
  $tracked = & git -C $unknown ls-files
  if ($tracked -contains "filestructure.txt") {
    throw "Unrelated existing file must remain untracked."
  }
  $status = & git -C $unknown status --short -- filestructure.txt
  if ($status -notmatch "^\?\? filestructure.txt") {
    throw "Existing extra file must remain untouched and untracked."
  }
  Write-Host "PASS: existing extra files preserved without staging"

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
