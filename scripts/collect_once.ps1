param(
  [string]$Config,
  [string]$Snapshot
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { 'py' } elseif (Get-Command python -ErrorAction SilentlyContinue) { 'python' } else { throw 'Python not found' }
$argsList = @('-3', '-m', 'collector', 'collect-once')
if ($py -eq 'python') { $argsList = @('-m','collector','collect-once') }
if ($Config) { $argsList += @('--config', $Config) }
if ($Snapshot) { $argsList += @('--snapshot', $Snapshot) }
Push-Location $root
try {
    & $py @argsList
    $exitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $exitCode
