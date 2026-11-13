$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
  if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 -m collector init-config
  } else {
    python -m collector init-config
  }
  $exitCode = $LASTEXITCODE
} finally {
  Pop-Location
}
exit $exitCode
