param(
  [Parameter(Mandatory=$true)][string]$Target
)
# Safe, resumable bootstrap. Preserve unrelated files, reject conflicting demo files.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$source = Join-Path $root "examples\test-nodejs-web-app"
$targetFull = [IO.Path]::GetFullPath($Target)
if ((Split-Path $targetFull -Leaf) -ne "test-nodejs-web-app") {
  throw "Automatic scaffolding is restricted to a directory named test-nodejs-web-app."
}
if (-not (Test-Path -LiteralPath (Join-Path $source "server.js") -PathType Leaf)) {
  throw "The checked-in Node.js demo source files are missing."
}
$node = Get-Command node.exe -ErrorAction SilentlyContinue
if (-not $node) { throw "Node.js 20+ required: https://nodejs.org/" }
$version = & $node.Source -p "Number(process.versions.node.split('.')[0])"
if ([int]$version -lt 20) { throw "Node.js 20 or newer is required." }
$git = Get-Command git.exe -ErrorAction SilentlyContinue
if (-not $git) { throw "Git required: https://git-scm.com/" }

$sourceRoot = (Get-Item -LiteralPath $source).FullName.TrimEnd('\', '/')
$required = @{}
Get-ChildItem -LiteralPath $sourceRoot -Recurse -File -Force | ForEach-Object {
  $relative = $_.FullName.Substring($sourceRoot.Length).TrimStart('\', '/')
  $required[$relative] = $_.FullName
}
if ($required.Count -lt 6) { throw "Demo source is incomplete; refusing setup." }

if (-not (Test-Path -LiteralPath $targetFull)) {
  New-Item -ItemType Directory -Path $targetFull -Force | Out-Null
}
$targetRoot = (Get-Item -LiteralPath $targetFull).FullName.TrimEnd('\', '/')
if ((Get-Item -LiteralPath $targetRoot).Attributes -band [IO.FileAttributes]::ReparsePoint) {
  throw "Refusing to bootstrap into a symbolic link or junction: $targetFull"
}
if (Test-Path -LiteralPath (Join-Path $targetRoot ".git")) {
  throw "Target already has Git metadata. Run the normal launcher instead."
}

# Preflight BEFORE any changes. Preserve unrelated files as untracked. Existing
# demo files must be byte-for-byte identical to prevent overwriting user edits.
$existing = @(Get-ChildItem -LiteralPath $targetRoot -Recurse -File -Force)
$extra = @()
$matching = 0
foreach ($file in $existing) {
  if ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw "Refusing to follow a symbolic link: $($file.FullName)"
  }
  $relative = $file.FullName.Substring($targetRoot.Length).TrimStart('\', '/')
  if (-not $required.ContainsKey($relative)) {
    # e.g. filestructure.txt. Never copy over, remove, read or stage these files.
    $extra += $relative
    continue
  }
  $expectedHash = (Get-FileHash -LiteralPath $required[$relative] -Algorithm SHA256).Hash
  $actualHash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
  if ($expectedHash -ne $actualHash) {
    throw "Existing file '$relative' differs from the demo template. Nothing was overwritten. Back up or use your existing project manually."
  }
  $matching++
}
# Reject directory junctions too, so a missing file cannot be written outside target.
foreach ($directory in @(Get-ChildItem -LiteralPath $targetRoot -Recurse -Directory -Force)) {
  if ($directory.Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw "Refusing to enter a linked directory: $($directory.FullName)"
  }
}
if ($matching -gt 0) {
  Write-Host "Recognized $matching existing demo file(s). Resuming without overwriting." -ForegroundColor Cyan
} else {
  Write-Host "Creating the Node.js demo in the selected project directory..." -ForegroundColor Cyan
}
if ($extra.Count -gt 0) {
  Write-Warning ("Preserving " + $extra.Count + " existing non-template file(s) as untracked.")
  foreach ($relative in @($extra | Sort-Object)) {
    Write-Host ("  Preserved: " + $relative)
  }
}

$added = 0
foreach ($relative in @($required.Keys | Sort-Object)) {
  $destination = Join-Path $targetRoot $relative
  if (-not (Test-Path -LiteralPath $destination)) {
    $parent = Split-Path -Parent $destination
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    Copy-Item -LiteralPath $required[$relative] -Destination $destination -ErrorAction Stop
    $added++
  }
}
Write-Host "Verified demo files: $matching; copied missing demo files: $added; preserved other files: $($extra.Count)" -ForegroundColor Cyan

Push-Location $targetRoot
try {
  & $node.Source --test
  if ($LASTEXITCODE -ne 0) { throw "Demo tests failed; retained files for investigation." }
  & $node.Source --check ".\server.js"
  if ($LASTEXITCODE -ne 0) { throw "server.js syntax failed." }
  & $node.Source --check ".\public\app.js"
  if ($LASTEXITCODE -ne 0) { throw "public/app.js syntax failed." }

  & $git.Source init -b main | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "Local Git init failed; source files were preserved." }
  # Only the known demo template is staged, never arbitrary unknown files.
  foreach ($relative in @($required.Keys | Sort-Object)) {
    & $git.Source add -- $relative
    if ($LASTEXITCODE -ne 0) { throw "Could not stage demo file: $relative" }
  }
  & $git.Source -c "user.name=Agent Lab Setup" -c "user.email=bootstrap@local.invalid" commit -m "chore: bootstrap working Node.js demo baseline" | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "Git baseline commit failed. Your source files remain intact." }
} finally {
  Pop-Location
}
Write-Host "Demo project verified, Git initialized, and all files preserved." -ForegroundColor Green
