param(
  [Parameter(Mandatory=$true)][string]$Target
)
$ErrorActionPreference="Stop"
$root=Split-Path -Parent $PSScriptRoot
$source=Join-Path $root "examples\test-nodejs-web-app"
$targetFull=[IO.Path]::GetFullPath($Target)
if ((Split-Path $targetFull -Leaf) -ne "test-nodejs-web-app") {
  throw "Refusing automatic scaffolding: expected a directory named test-nodejs-web-app."
}
if (-not (Test-Path (Join-Path $source "server.js"))) {
  throw "Example app files are missing from the agent repository."
}
if (Test-Path $targetFull) {
  $items=@(Get-ChildItem -LiteralPath $targetFull -Force)
  if ($items.Count -gt 0) {
    throw "Target directory is not empty; refusing to overwrite files: $targetFull"
  }
} else {
  New-Item -ItemType Directory -Force -Path $targetFull | Out-Null
}
$node=Get-Command node.exe -ErrorAction SilentlyContinue
if (-not $node) { throw "Node.js >=20 is required: https://nodejs.org/" }
$version=& $node.Source -p "Number(process.versions.node.split('.')[0])"
if ([int]$version -lt 20) { throw "Node.js 20 or higher is required." }
$git=Get-Command git.exe -ErrorAction SilentlyContinue
if (-not $git) { throw "Git must be installed: https://git-scm.com/" }

Write-Host "Creating test project at $targetFull..." -ForegroundColor Cyan
Get-ChildItem -LiteralPath $source -Force | Copy-Item -Destination $targetFull -Recurse -Force
Push-Location $targetFull
try {
  & $node.Source --test
  if ($LASTEXITCODE -ne 0) { throw "Initial Node.js tests failed; app not activated." }
  & $node.Source --check ".\server.js"
  if ($LASTEXITCODE -ne 0) { throw "server.js syntax failed." }
  & $node.Source --check ".\public\app.js"
  if ($LASTEXITCODE -ne 0) { throw "public/app.js syntax failed." }

  & $git.Source init -b main | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "Local Git initialization failed." }
  & $git.Source add .
  if ($LASTEXITCODE -ne 0) { throw "Git staging failed." }
  & $git.Source -c "user.name=Agent Lab Setup" -c "user.email=bootstrap@local.invalid" commit -m "chore: bootstrap working Node.js demo baseline" | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "Git baseline commit failed." }
} finally {
  Pop-Location
}
Write-Host "Node.js test project created and tested. No database required." -ForegroundColor Green
