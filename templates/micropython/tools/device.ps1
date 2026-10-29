param(
  [Parameter(Mandatory=$true)][string]$Port,
  [ValidateSet("list","repl","upload")][string]$Action = "list",
  [switch]$ConfirmUpload
)
$ErrorActionPreference="Stop"
if ($Port -notmatch '^(COM[0-9]+|/dev/[-_a-zA-Z0-9/.]+)$') {
  throw "Specify an exact serial port, e.g. COM11."
}
$root=Split-Path -Parent $PSScriptRoot
$mp=Get-Command mpremote -ErrorAction SilentlyContinue
if (-not $mp) { throw "Install mpremote separately: python -m pip install mpremote" }
if ($Action -eq "upload" -and -not $ConfirmUpload) {
  throw "Device writes require -ConfirmUpload and an exact serial port."
}
Push-Location $root
try {
  if ($Action -eq "list") {
    & $mp.Source connect $Port fs ls
  } elseif ($Action -eq "repl") {
    & $mp.Source connect $Port repl
  } else {
    # Never remove files or erase flash. Only selected project files are copied.
    & $mp.Source connect $Port fs cp src/config.py :config.py
    if ($LASTEXITCODE -ne 0) { throw "config.py transfer failed." }
    & $mp.Source connect $Port fs cp src/logic.py :logic.py
    if ($LASTEXITCODE -ne 0) { throw "logic.py transfer failed." }
    & $mp.Source connect $Port fs cp src/main.py :main.py
    if ($LASTEXITCODE -ne 0) { throw "main.py transfer failed." }
    Write-Host "Copied firmware files. Reset/run on the board explicitly." -ForegroundColor Yellow
  }
} finally { Pop-Location }
